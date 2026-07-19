from __future__ import annotations

from app.services.subtitle_optimizer import (
    SubtitleOptimizerSettings,
    comparable_text,
    optimize_subtitles,
    validate_captions,
    wrap_text,
)
from app.services.subtitles import SubtitleFormatSettings, SubtitleSegment, format_subtitle_segments, to_srt


def segment(index: int, start: float, end: float, text: str) -> SubtitleSegment:
    return SubtitleSegment(
        index=index,
        start=start,
        end=end,
        text=text,
        avg_logprob=None,
        no_speech_prob=None,
        suspicious=False,
    )


def test_optimizer_reduces_orphan_particle_at_caption_start() -> None:
    optimized = optimize_subtitles(
        [
            segment(1, 0.0, 0.5, "この方法を使うこと"),
            segment(2, 0.55, 1.7, "で改善できます"),
        ],
        SubtitleOptimizerSettings(preferred_chars_per_line=12),
    )

    assert len(optimized) == 1
    assert optimized[0].text == "この方法を使うことで\n改善できます"


def test_optimizer_avoids_splitting_toiu_and_kotode() -> None:
    optimized = optimize_subtitles(
        [segment(1, 0.0, 5.0, "これは字幕を自然にするということで改善できます")],
        SubtitleOptimizerSettings(max_chars_per_caption=18, preferred_chars_per_line=12),
    )

    joined = "|".join(item.text.replace("\n", "") for item in optimized)
    assert "という|ことで" not in joined
    assert "こと|で" not in joined


def test_optimizer_splits_near_comma() -> None:
    optimized = optimize_subtitles(
        [segment(1, 0.0, 6.0, "今日はジャンプカットを確認して、字幕を読みやすく整えます")],
        SubtitleOptimizerSettings(max_chars_per_caption=20, preferred_chars_per_line=18),
    )

    assert optimized[0].text.replace("\n", "").endswith("、")


def test_wrap_caption_lines_uses_natural_boundary() -> None:
    assert wrap_text("この方法を使うことで改善できます", 12, 2) == "この方法を使うことで\n改善できます"


def test_optimizer_merges_extremely_short_caption() -> None:
    optimized = optimize_subtitles(
        [
            segment(1, 0.0, 0.25, "はい"),
            segment(2, 0.3, 1.2, "そうですね"),
            segment(3, 1.25, 2.4, "これは大事です"),
        ]
    )

    assert optimized[0].text.replace("\n", "") == "はいそうですね"
    assert len(optimized) == 2


def test_optimizer_splits_long_caption() -> None:
    optimized = optimize_subtitles(
        [segment(1, 0.0, 8.0, "今日はジャンプカットと字幕編集の基本的な流れを確認して読みやすい字幕に整えます。")],
        SubtitleOptimizerSettings(max_chars_per_caption=18, preferred_chars_per_line=12),
    )

    assert len(optimized) > 1
    assert all(len(item.text.replace("\n", "")) <= 22 for item in optimized)


def test_optimizer_does_not_merge_across_silence_gap() -> None:
    optimized = optimize_subtitles(
        [
            segment(1, 0.0, 0.4, "はい"),
            segment(2, 1.5, 2.4, "次に進みます"),
        ]
    )

    assert len(optimized) == 2


def test_optimizer_does_not_create_overlapping_timestamps() -> None:
    optimized = optimize_subtitles(
        [
            segment(1, 0.0, 0.6, "今日は"),
            segment(2, 0.65, 1.1, "字幕を整えます"),
            segment(3, 1.15, 1.8, "よろしくお願いします"),
        ]
    )

    for current, following in zip(optimized, optimized[1:]):
        assert current.end <= following.start


def test_optimizer_keeps_all_text() -> None:
    source = [
        segment(1, 0.0, 0.5, "この方法を使うこと"),
        segment(2, 0.55, 2.0, "で改善できます"),
    ]
    optimized = optimize_subtitles(source)

    assert comparable_text(item.text for item in optimized) == comparable_text(item.text for item in source)


def test_optimizer_handles_mixed_japanese_alnum_symbols() -> None:
    source = [segment(1, 0.0, 4.0, "API v2で、Windows 11の動画をチェックします。")]
    optimized = optimize_subtitles(source, SubtitleOptimizerSettings(preferred_chars_per_line=14))

    assert comparable_text(item.text for item in optimized) == "APIv2で、Windows11の動画をチェックします。"
    assert "\n" in optimized[0].text


def test_optimizer_accepts_windows_newlines() -> None:
    source = [segment(1, 0.0, 2.5, "今日は\r\n字幕を\r\n整えます")]
    optimized = optimize_subtitles(source)

    assert comparable_text(item.text for item in optimized) == "今日は字幕を整えます"


def test_optimizer_keeps_existing_srt_output_shape() -> None:
    optimized = format_subtitle_segments(
        [segment(1, 0.0, 1.5, "保存テスト")],
        SubtitleFormatSettings(),
    )

    assert to_srt(optimized) == "1\n00:00:00,000 --> 00:00:01,500\n保存テスト\n"


def test_validate_captions_detects_text_loss() -> None:
    result = validate_captions(
        before=[segment(1, 0.0, 1.0, "欠落しない")],
        after=[segment(1, 0.0, 1.0, "欠落")],
        require_exact_text=True,
    )

    assert result.ok is False
    assert result.errors
