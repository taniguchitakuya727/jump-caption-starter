from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path

from app.services.ffmpeg import detect_ffmpeg


class VideoProcessingError(RuntimeError):
    pass


@dataclass(frozen=True)
class SilenceInterval:
    start: float
    end: float
    duration: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class KeepSegment:
    start: float
    end: float


@dataclass(frozen=True)
class JumpCutSettings:
    silence_threshold_db: float = -35.0
    min_silence_duration: float = 0.5
    retained_margin: float = 0.15

    def validate(self) -> None:
        if self.silence_threshold_db >= 0:
            raise VideoProcessingError("無音判定音量は 0 dB 未満にしてください。")
        if self.min_silence_duration <= 0:
            raise VideoProcessingError("最短無音時間は 0 より大きくしてください。")
        if self.retained_margin < 0:
            raise VideoProcessingError("余白は 0 以上にしてください。")


@dataclass(frozen=True)
class JumpCutResult:
    output_path: Path
    silence_json_path: Path
    duration: float
    silences: list[SilenceInterval]
    logs: list[str]


SILENCE_START_RE = re.compile(r"silence_start:\s*(?P<start>[0-9.]+)")
SILENCE_END_RE = re.compile(
    r"silence_end:\s*(?P<end>[0-9.]+)\s*\|\s*silence_duration:\s*(?P<duration>[0-9.]+)"
)


def parse_silence_log(log_text: str) -> list[SilenceInterval]:
    silences: list[SilenceInterval] = []
    pending_start: float | None = None

    for line in log_text.splitlines():
        start_match = SILENCE_START_RE.search(line)
        if start_match:
            pending_start = float(start_match.group("start"))
            continue

        end_match = SILENCE_END_RE.search(line)
        if not end_match:
            continue

        end = float(end_match.group("end"))
        duration = float(end_match.group("duration"))
        start = pending_start if pending_start is not None else max(0.0, end - duration)
        silences.append(SilenceInterval(start=start, end=end, duration=duration))
        pending_start = None

    return silences


def build_keep_segments(
    duration: float,
    silences: list[SilenceInterval],
    retained_margin: float,
) -> list[KeepSegment]:
    if duration <= 0:
        raise VideoProcessingError("動画の長さを取得できませんでした。")

    cut_ranges: list[KeepSegment] = []
    for silence in silences:
        cut_start = max(0.0, silence.start + retained_margin)
        cut_end = min(duration, silence.end - retained_margin)
        if cut_end > cut_start:
            cut_ranges.append(KeepSegment(start=cut_start, end=cut_end))

    if not cut_ranges:
        return [KeepSegment(start=0.0, end=duration)]

    keep_segments: list[KeepSegment] = []
    cursor = 0.0
    for cut_range in sorted(cut_ranges, key=lambda segment: segment.start):
        if cut_range.start > cursor:
            keep_segments.append(KeepSegment(start=cursor, end=cut_range.start))
        cursor = max(cursor, cut_range.end)

    if cursor < duration:
        keep_segments.append(KeepSegment(start=cursor, end=duration))

    return [segment for segment in keep_segments if segment.end - segment.start > 0.01]


def make_output_paths(input_path: Path, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{input_path.stem}_cut.mp4"
    silence_json_path = output_dir / f"{input_path.stem}_silences.json"
    return output_path, silence_json_path


def run_jump_cut(
    input_path: Path,
    output_dir: Path,
    settings: JumpCutSettings,
) -> JumpCutResult:
    settings.validate()
    ffmpeg_detection = detect_ffmpeg()
    if not ffmpeg_detection.available or ffmpeg_detection.path is None:
        raise VideoProcessingError(ffmpeg_detection.error or "FFmpeg が見つかりません。")

    ffprobe_path = shutil.which("ffprobe")
    if ffprobe_path is None:
        raise VideoProcessingError(
            "ffprobe が見つかりません。通常は FFmpeg と一緒にインストールされます。"
            "Windowsでは README_WINDOWS.md の手順を確認してください。"
        )

    output_path, silence_json_path = make_output_paths(input_path, output_dir)
    logs: list[str] = []

    duration = probe_duration(ffprobe_path, input_path)
    logs.append(f"duration: {duration:.3f} sec")

    silences, detect_log = detect_silences(ffmpeg_detection.path, input_path, settings)
    logs.append(detect_log)
    logs.append(f"silences detected: {len(silences)}")

    keep_segments = build_keep_segments(duration, silences, settings.retained_margin)
    logs.append(f"keep segments: {len(keep_segments)}")

    cut_log = write_jump_cut(ffmpeg_detection.path, input_path, output_path, keep_segments)
    logs.append(cut_log)

    write_silence_json(
        silence_json_path=silence_json_path,
        source_path=input_path,
        output_path=output_path,
        duration=duration,
        settings=settings,
        silences=silences,
        keep_segments=keep_segments,
    )
    logs.append(f"silence json: {silence_json_path.name}")

    return JumpCutResult(
        output_path=output_path,
        silence_json_path=silence_json_path,
        duration=duration,
        silences=silences,
        logs=logs,
    )


def probe_duration(ffprobe_path: str, input_path: Path) -> float:
    command = [
        ffprobe_path,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(input_path),
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise VideoProcessingError(result.stderr.strip() or "ffprobe failed.")

    try:
        return float(result.stdout.strip())
    except ValueError as exc:
        raise VideoProcessingError("ffprobe の duration を読み取れませんでした。") from exc


def detect_silences(
    ffmpeg_path: str,
    input_path: Path,
    settings: JumpCutSettings,
) -> tuple[list[SilenceInterval], str]:
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-i",
        str(input_path),
        "-af",
        f"silencedetect=noise={settings.silence_threshold_db}dB:d={settings.min_silence_duration}",
        "-f",
        "null",
        "-",
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_text = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if result.returncode != 0:
        raise VideoProcessingError(log_text.strip() or "FFmpeg の無音検出に失敗しました。")

    return parse_silence_log(log_text), log_text


def write_jump_cut(
    ffmpeg_path: str,
    input_path: Path,
    output_path: Path,
    keep_segments: list[KeepSegment],
) -> str:
    if not keep_segments:
        raise VideoProcessingError("出力する動画区間がありません。")

    filter_complex_parts: list[str] = []
    concat_inputs: list[str] = []
    for index, segment in enumerate(keep_segments):
        filter_complex_parts.append(
            f"[0:v]trim=start={segment.start:.6f}:end={segment.end:.6f},"
            f"setpts=PTS-STARTPTS[v{index}]"
        )
        filter_complex_parts.append(
            f"[0:a]atrim=start={segment.start:.6f}:end={segment.end:.6f},"
            f"asetpts=PTS-STARTPTS[a{index}]"
        )
        concat_inputs.append(f"[v{index}][a{index}]")

    filter_complex = (
        ";".join(filter_complex_parts)
        + ";"
        + "".join(concat_inputs)
        + f"concat=n={len(keep_segments)}:v=1:a=1[outv][outa]"
    )
    command = [
        ffmpeg_path,
        "-hide_banner",
        "-y",
        "-i",
        str(input_path),
        "-filter_complex",
        filter_complex,
        "-map",
        "[outv]",
        "-map",
        "[outa]",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "20",
        "-c:a",
        "aac",
        "-movflags",
        "+faststart",
        str(output_path),
    ]
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    log_text = "\n".join(part for part in [result.stdout, result.stderr] if part)
    if result.returncode != 0:
        raise VideoProcessingError(log_text.strip() or "FFmpeg のジャンプカットに失敗しました。")

    return log_text


def write_silence_json(
    silence_json_path: Path,
    source_path: Path,
    output_path: Path,
    duration: float,
    settings: JumpCutSettings,
    silences: list[SilenceInterval],
    keep_segments: list[KeepSegment],
) -> None:
    payload = {
        "source": source_path.name,
        "output": output_path.name,
        "duration": duration,
        "settings": asdict(settings),
        "silences": [silence.to_dict() for silence in silences],
        "keep_segments": [asdict(segment) for segment in keep_segments],
    }
    silence_json_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
