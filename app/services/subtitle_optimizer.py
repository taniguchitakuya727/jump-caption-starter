from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable

from app.services.subtitles import SubtitleEditError, SubtitleSegment


STRONG_PUNCTUATION = "。！？.!?"
MEDIUM_PUNCTUATION = "、，,"
PARTICLES = (
    "という",
    "ことで",
    "けれど",
    "から",
    "まで",
    "より",
    "ので",
    "のに",
    "けど",
    "って",
    "は",
    "が",
    "を",
    "に",
    "で",
    "と",
    "も",
    "へ",
    "の",
)
CONNECTORS = (
    "そして",
    "それで",
    "ただ",
    "また",
    "でも",
    "なので",
    "だから",
    "次に",
    "一方",
)
FUNCTION_WORDS_ALLOWED_AT_START = ("で、", "で,", "でも", "では", "それで")


@dataclass(frozen=True)
class SubtitleOptimizerSettings:
    minimum_duration: float = 0.8
    maximum_duration: float = 7.0
    minimum_gap: float = 0.05
    preferred_chars_per_second: float = 10.0
    maximum_chars_per_second: float = 15.0
    max_chars_per_caption: int = 36
    preferred_chars_per_line: int = 18
    max_lines: int = 2
    merge_gap_threshold: float = 0.35
    hard_gap_threshold: float = 0.7

    def validate(self) -> None:
        if self.minimum_duration <= 0:
            raise SubtitleEditError("最短表示時間は 0 より大きくしてください。")
        if self.maximum_duration < self.minimum_duration:
            raise SubtitleEditError("最長表示時間は最短表示時間以上にしてください。")
        if self.minimum_gap < 0:
            raise SubtitleEditError("字幕間隔は 0 以上にしてください。")
        if self.preferred_chars_per_second <= 0 or self.maximum_chars_per_second <= 0:
            raise SubtitleEditError("文字/秒は 0 より大きくしてください。")
        if self.max_chars_per_caption <= 0:
            raise SubtitleEditError("1画面の最大文字数は 1 以上にしてください。")
        if self.preferred_chars_per_line <= 0:
            raise SubtitleEditError("1行の推奨文字数は 1 以上にしてください。")
        if self.max_lines <= 0:
            raise SubtitleEditError("最大行数は 1 以上にしてください。")


@dataclass(frozen=True)
class SubtitleValidationResult:
    ok: bool
    errors: list[str]
    warnings: list[str]


def optimize_subtitles(
    segments: list[SubtitleSegment],
    settings: SubtitleOptimizerSettings | None = None,
) -> list[SubtitleSegment]:
    settings = settings or SubtitleOptimizerSettings()
    settings.validate()
    if not segments:
        return []

    original_text = comparable_text(segment.text for segment in segments)
    candidates = build_caption_candidates(segments)
    split_segments = split_by_semantic_boundaries(candidates, settings)
    merged_segments = merge_short_captions(split_segments, settings)
    timed_segments = adjust_caption_timings(merged_segments, settings)
    wrapped_segments = wrap_caption_lines(timed_segments, settings)

    validation = validate_captions(
        before=segments,
        after=wrapped_segments,
        settings=settings,
        require_exact_text=True,
    )
    if not validation.ok:
        raise SubtitleEditError("字幕整形の検証に失敗しました: " + " / ".join(validation.errors))

    if comparable_text(segment.text for segment in wrapped_segments) != original_text:
        raise SubtitleEditError("字幕整形後の本文が元本文と一致しません。")

    return [
        SubtitleSegment(
            index=index,
            start=segment.start,
            end=segment.end,
            text=segment.text,
            avg_logprob=segment.avg_logprob,
            no_speech_prob=segment.no_speech_prob,
            suspicious=segment.suspicious,
            words=segment.words,
        )
        for index, segment in enumerate(wrapped_segments, start=1)
    ]


def build_caption_candidates(segments: list[SubtitleSegment]) -> list[SubtitleSegment]:
    return [
        SubtitleSegment(
            index=index,
            start=segment.start,
            end=segment.end,
            text=segment.text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "").strip(),
            avg_logprob=segment.avg_logprob,
            no_speech_prob=segment.no_speech_prob,
            suspicious=segment.suspicious,
            words=segment.words,
        )
        for index, segment in enumerate(segments, start=1)
        if segment.text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "").strip()
    ]


def split_by_semantic_boundaries(
    segments: list[SubtitleSegment],
    settings: SubtitleOptimizerSettings,
) -> list[SubtitleSegment]:
    result: list[SubtitleSegment] = []
    for segment in segments:
        text = compact_line_text(segment.text)
        chunks = split_text_into_chunks(text, settings.max_chars_per_caption)
        if len(chunks) == 1:
            result.append(segment)
            continue

        cursor = segment.start
        total_chars = sum(max(1, len(chunk)) for chunk in chunks)
        for chunk_index, chunk in enumerate(chunks):
            end = segment.end
            if chunk_index < len(chunks) - 1:
                end = cursor + (segment.end - segment.start) * (len(chunk) / total_chars)
                end = min(max(end, cursor + 0.05), segment.end)
            result.append(
                SubtitleSegment(
                    index=len(result) + 1,
                    start=cursor,
                    end=end,
                    text=chunk,
                    avg_logprob=segment.avg_logprob,
                    no_speech_prob=segment.no_speech_prob,
                    suspicious=True,
                    words=split_words_for_text(segment.words, chunk),
                )
            )
            cursor = end

    return result


def merge_short_captions(
    segments: list[SubtitleSegment],
    settings: SubtitleOptimizerSettings,
) -> list[SubtitleSegment]:
    merged: list[SubtitleSegment] = []
    index = 0
    while index < len(segments):
        current = segments[index]
        if index + 1 >= len(segments):
            merged.append(current)
            break

        next_segment = segments[index + 1]
        merged_text = join_text(current.text, next_segment.text)
        gap = next_segment.start - current.end
        current_duration = current.end - current.start
        should_merge = (
            gap <= settings.merge_gap_threshold
            and gap < settings.hard_gap_threshold
            and len(compact_line_text(merged_text)) <= settings.max_chars_per_caption
            and (
                current_duration < settings.minimum_duration
                or starts_with_orphan_particle(next_segment.text)
                or chars_per_second(current) > settings.maximum_chars_per_second
            )
        )

        if should_merge:
            merged.append(
                SubtitleSegment(
                    index=len(merged) + 1,
                    start=current.start,
                    end=next_segment.end,
                    text=merged_text,
                    avg_logprob=current.avg_logprob,
                    no_speech_prob=max_optional(current.no_speech_prob, next_segment.no_speech_prob),
                    suspicious=(
                        current.suspicious
                        or next_segment.suspicious
                        or current_duration < settings.minimum_duration
                        or starts_with_orphan_particle(next_segment.text)
                    ),
                    words=combine_words(current.words, next_segment.words),
                )
            )
            index += 2
            continue

        merged.append(current)
        index += 1

    if len(merged) != len(segments):
        return merge_short_captions(merged, settings)
    return merged


def adjust_caption_timings(
    segments: list[SubtitleSegment],
    settings: SubtitleOptimizerSettings,
) -> list[SubtitleSegment]:
    adjusted: list[SubtitleSegment] = []
    for index, segment in enumerate(segments):
        start = max(0.0, segment.start)
        end = max(start + 0.05, segment.end)
        text_length = max(1, len(compact_line_text(segment.text)))
        preferred_duration = min(
            settings.maximum_duration,
            max(settings.minimum_duration, text_length / settings.preferred_chars_per_second),
        )
        if end - start < preferred_duration:
            end = min(start + preferred_duration, start + settings.maximum_duration)
        if end - start > settings.maximum_duration:
            end = start + settings.maximum_duration

        if index + 1 < len(segments):
            next_start = max(start, segments[index + 1].start)
            latest_end = max(start + 0.05, next_start - settings.minimum_gap)
            if end > latest_end:
                end = latest_end

        if adjusted and start < adjusted[-1].end + settings.minimum_gap:
            start = adjusted[-1].end + settings.minimum_gap
            end = max(end, start + settings.minimum_duration)

        adjusted.append(
            SubtitleSegment(
                index=index + 1,
                start=round(start, 3),
                end=round(max(end, start + 0.05), 3),
                text=segment.text,
                avg_logprob=segment.avg_logprob,
                no_speech_prob=segment.no_speech_prob,
                suspicious=segment.suspicious or chars_per_second(segment) > settings.maximum_chars_per_second,
                words=segment.words,
            )
        )

    return adjusted


def wrap_caption_lines(
    segments: list[SubtitleSegment],
    settings: SubtitleOptimizerSettings,
) -> list[SubtitleSegment]:
    return [
        SubtitleSegment(
            index=index,
            start=segment.start,
            end=segment.end,
            text=wrap_text(segment.text, settings.preferred_chars_per_line, settings.max_lines),
            avg_logprob=segment.avg_logprob,
            no_speech_prob=segment.no_speech_prob,
            suspicious=segment.suspicious,
            words=segment.words,
        )
        for index, segment in enumerate(segments, start=1)
    ]


def validate_captions(
    before: list[SubtitleSegment],
    after: list[SubtitleSegment],
    settings: SubtitleOptimizerSettings | None = None,
    require_exact_text: bool = True,
) -> SubtitleValidationResult:
    settings = settings or SubtitleOptimizerSettings()
    errors: list[str] = []
    warnings: list[str] = []

    if require_exact_text and comparable_text(segment.text for segment in before) != comparable_text(
        segment.text for segment in after
    ):
        errors.append("本文の欠落または重複があります。")

    previous_end = -1.0
    for index, segment in enumerate(after):
        text = compact_line_text(segment.text)
        if not text:
            errors.append(f"{index + 1}: 本文が空です。")
        if segment.start >= segment.end:
            errors.append(f"{index + 1}: 開始時刻が終了時刻以上です。")
        if segment.start < previous_end:
            errors.append(f"{index + 1}: 字幕時刻が重複しています。")
        if len(segment.text.splitlines()) > settings.max_lines:
            errors.append(f"{index + 1}: 最大行数を超えています。")
        if len(text) > settings.max_chars_per_caption + 4:
            warnings.append(f"{index + 1}: 1画面の文字数が多めです。")
        if segment.end - segment.start < settings.minimum_duration * 0.5:
            warnings.append(f"{index + 1}: 表示時間が短すぎます。")
        previous_end = segment.end

    return SubtitleValidationResult(ok=not errors, errors=errors, warnings=warnings)


def split_text_into_chunks(text: str, max_chars: int) -> list[str]:
    text = compact_line_text(text)
    if len(text) <= max_chars:
        return [text]

    chunks: list[str] = []
    remaining = text
    while len(remaining) > max_chars:
        split_at = find_split_position(remaining, max_chars)
        chunks.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def find_split_position(text: str, max_chars: int) -> int:
    if len(text) <= 1:
        return len(text)

    target = min(max_chars, len(text) - 1)
    min_position = max(1, int(target * 0.45))
    max_position = min(len(text) - 1, max(target + 6, int(target * 1.35)))
    return max(
        range(min_position, max_position + 1),
        key=lambda index: split_position_score(text, index, target),
    )


def split_position_score(text: str, index: int, target: int) -> float:
    before = text[:index]
    after = text[index:]
    last_char = before[-1:]
    next_char = after[:1]
    score = 100 - abs(index - target) * 2.8

    if last_char in STRONG_PUNCTUATION:
        score += 120
    elif last_char in MEDIUM_PUNCTUATION:
        score += 90

    if starts_with_any(after, CONNECTORS):
        score += 36
    if ends_with_any(before, CONNECTORS):
        score += 28
    if ends_with_any(before, ("ので", "から", "ため", "けど", "けれど", "ことで", "という")):
        score += 42
    if last_char in "はがをにへでともやのねよ":
        score += 32
    if starts_with_orphan_particle(after):
        score -= 95
    if ends_with_any(before, ("という", "こと")) and starts_with_any(after, ("で", "は", "を", "に")):
        score -= 120
    if len(after) <= 2:
        score -= 50
    if next_char in "、。！？,.!?":
        score -= 100
    return score


def wrap_text(text: str, preferred_chars_per_line: int, max_lines: int) -> str:
    plain_text = compact_line_text(text)
    if len(plain_text) <= preferred_chars_per_line or max_lines <= 1:
        return plain_text

    split_at = find_line_break_position(plain_text, preferred_chars_per_line)
    first = plain_text[:split_at].strip()
    second = plain_text[split_at:].strip()
    if not first or not second:
        return plain_text
    return f"{first}\n{second}"


def find_line_break_position(text: str, preferred_chars_per_line: int) -> int:
    target = min(preferred_chars_per_line, max(1, len(text) // 2))
    min_position = max(1, int(len(text) * 0.35))
    max_position = min(len(text) - 1, int(len(text) * 0.65) + 1)
    return max(
        range(min_position, max_position + 1),
        key=lambda index: line_break_score(text, index, target),
    )


def line_break_score(text: str, index: int, target: int) -> float:
    before = text[:index]
    after = text[index:]
    score = 100 - abs(len(before) - len(after)) * 4 - abs(index - target)
    if before[-1:] in MEDIUM_PUNCTUATION:
        score += 90
    if before[-1:] in "はがをにへでともやのねよ":
        score += 42
    if ends_with_any(before, ("という", "ことで", "なので", "から", "まで")):
        score += 36
    if starts_with_orphan_particle(after):
        score -= 100
    if before[-1:] in "、。！？,.!?" and len(after) <= 3:
        score -= 60
    return score


def starts_with_orphan_particle(text: str) -> bool:
    stripped = compact_line_text(text)
    if starts_with_any(stripped, FUNCTION_WORDS_ALLOWED_AT_START):
        return False
    return starts_with_any(stripped, PARTICLES)


def chars_per_second(segment: SubtitleSegment) -> float:
    duration = max(0.05, segment.end - segment.start)
    return len(compact_line_text(segment.text)) / duration


def comparable_text(parts: Iterable[str]) -> str:
    return re.sub(r"\s+", "", "".join(parts))


def compact_line_text(text: str) -> str:
    return re.sub(r"\s+", "", text.replace("\r\n", "\n").replace("\r", "\n"))


def join_text(left: str, right: str) -> str:
    return f"{compact_line_text(left)}{compact_line_text(right)}"


def starts_with_any(text: str, prefixes: tuple[str, ...]) -> bool:
    return any(text.startswith(prefix) for prefix in prefixes)


def ends_with_any(text: str, suffixes: tuple[str, ...]) -> bool:
    return any(text.endswith(suffix) for suffix in suffixes)


def max_optional(left: float | None, right: float | None) -> float | None:
    values = [value for value in [left, right] if value is not None]
    return max(values) if values else None


def combine_words(
    left: list[dict[str, object]] | None,
    right: list[dict[str, object]] | None,
) -> list[dict[str, object]] | None:
    words = [*(left or []), *(right or [])]
    return words or None


def split_words_for_text(
    words: list[dict[str, object]] | None,
    text: str,
) -> list[dict[str, object]] | None:
    if not words:
        return None
    target = compact_line_text(text)
    collected: list[dict[str, object]] = []
    cursor = ""
    for word in words:
        collected.append(word)
        cursor += compact_line_text(str(word.get("word", "")))
        if len(cursor) >= len(target):
            break
    return collected or None
