from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class SubtitleGenerationError(RuntimeError):
    pass


@dataclass(frozen=True)
class SubtitleSegment:
    index: int
    start: float
    end: float
    text: str
    avg_logprob: float | None
    no_speech_prob: float | None
    suspicious: bool

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True)
class SubtitleSettings:
    model_size: str = "small"
    language: str | None = "ja"
    device: str = "cpu"
    compute_type: str = "int8"

    def validate(self) -> None:
        if not self.model_size:
            raise SubtitleGenerationError("Whisperモデルを指定してください。")


@dataclass(frozen=True)
class SubtitleResult:
    srt_path: Path
    txt_path: Path
    metadata_path: Path
    segments: list[SubtitleSegment]
    logs: list[str]


def faster_whisper_available() -> bool:
    try:
        import faster_whisper  # noqa: F401
    except ImportError:
        return False
    return True


def generate_subtitles(
    media_path: Path,
    output_dir: Path,
    settings: SubtitleSettings,
) -> SubtitleResult:
    settings.validate()

    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:
        raise SubtitleGenerationError(
            "faster-whisper がインストールされていません。READMEの手順で依存関係を更新してください。"
        ) from exc

    output_dir.mkdir(parents=True, exist_ok=True)
    srt_path = output_dir / f"{media_path.stem}.srt"
    txt_path = output_dir / f"{media_path.stem}.txt"
    metadata_path = output_dir / f"{media_path.stem}_subtitles.json"
    logs = [
        f"model: {settings.model_size}",
        f"language: {settings.language or 'auto'}",
        f"device: {settings.device}",
        f"compute_type: {settings.compute_type}",
    ]

    try:
        model = WhisperModel(
            settings.model_size,
            device=settings.device,
            compute_type=settings.compute_type,
        )
        raw_segments, info = model.transcribe(
            str(media_path),
            language=settings.language,
            vad_filter=True,
        )
        segments = [
            _convert_segment(index=index, raw_segment=segment)
            for index, segment in enumerate(raw_segments, start=1)
        ]
    except Exception as exc:
        raise SubtitleGenerationError(
            "字幕生成に失敗しました。初回はWhisperモデルのダウンロードが必要です。"
            "インターネット接続を確認してから再実行してください。"
            f" 詳細: {exc}"
        ) from exc

    logs.append(f"detected language: {getattr(info, 'language', settings.language)}")
    logs.append(f"language probability: {getattr(info, 'language_probability', None)}")
    logs.append(f"segments: {len(segments)}")

    srt_path.write_text(to_srt(segments), encoding="utf-8")
    txt_path.write_text(to_txt(segments), encoding="utf-8")
    write_metadata(metadata_path, media_path, settings, segments, logs)

    return SubtitleResult(
        srt_path=srt_path,
        txt_path=txt_path,
        metadata_path=metadata_path,
        segments=segments,
        logs=logs,
    )


def _convert_segment(index: int, raw_segment: Any) -> SubtitleSegment:
    text = str(getattr(raw_segment, "text", "")).strip()
    avg_logprob = getattr(raw_segment, "avg_logprob", None)
    no_speech_prob = getattr(raw_segment, "no_speech_prob", None)
    suspicious = (
        not text
        or (avg_logprob is not None and avg_logprob < -1.0)
        or (no_speech_prob is not None and no_speech_prob > 0.6)
    )
    return SubtitleSegment(
        index=index,
        start=float(getattr(raw_segment, "start")),
        end=float(getattr(raw_segment, "end")),
        text=text,
        avg_logprob=avg_logprob,
        no_speech_prob=no_speech_prob,
        suspicious=suspicious,
    )


def format_srt_time(seconds: float) -> str:
    milliseconds = round(seconds * 1000)
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02}:{minutes:02}:{secs:02},{millis:03}"


def to_srt(segments: list[SubtitleSegment]) -> str:
    blocks = []
    for segment in segments:
        blocks.append(
            "\n".join(
                [
                    str(segment.index),
                    f"{format_srt_time(segment.start)} --> {format_srt_time(segment.end)}",
                    segment.text,
                ]
            )
        )
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def to_txt(segments: list[SubtitleSegment]) -> str:
    return "\n".join(segment.text for segment in segments if segment.text) + (
        "\n" if segments else ""
    )


def write_metadata(
    metadata_path: Path,
    media_path: Path,
    settings: SubtitleSettings,
    segments: list[SubtitleSegment],
    logs: list[str],
) -> None:
    payload = {
        "source": media_path.name,
        "settings": asdict(settings),
        "segments": [segment.to_dict() for segment in segments],
        "logs": logs,
    }
    metadata_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
