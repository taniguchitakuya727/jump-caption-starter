from __future__ import annotations

import shutil
import subprocess
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FFmpegDetection:
    available: bool
    path: str | None
    version: str | None
    error: str | None = None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def detect_ffmpeg() -> FFmpegDetection:
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path is None:
        return FFmpegDetection(
            available=False,
            path=None,
            version=None,
            error=(
                "FFmpeg が見つかりません。ジャンプカットには ffmpeg と ffprobe が必要です。"
                "Windowsでは README_WINDOWS.md の手順で FFmpeg をインストールし、"
                "PATH から実行できる状態にしてください。"
            ),
        )

    try:
        result = subprocess.run(
            [ffmpeg_path, "-version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=5,
        )
    except OSError as exc:
        return FFmpegDetection(
            available=False,
            path=ffmpeg_path,
            version=None,
            error=str(exc),
        )
    except subprocess.TimeoutExpired:
        return FFmpegDetection(
            available=False,
            path=ffmpeg_path,
            version=None,
            error="ffmpeg -version timed out.",
        )

    if result.returncode != 0:
        stderr = result.stderr.strip() or "ffmpeg -version failed."
        return FFmpegDetection(
            available=False,
            path=ffmpeg_path,
            version=None,
            error=stderr,
        )

    first_line = result.stdout.splitlines()[0] if result.stdout else None
    return FFmpegDetection(
        available=True,
        path=ffmpeg_path,
        version=first_line,
        error=None,
    )
