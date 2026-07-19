from __future__ import annotations

import os
import platform
import shutil
import sys
from pathlib import Path


def main() -> int:
    project_dir = Path(__file__).resolve().parents[1]
    checks = [
        ("Python", sys.version.split()[0]),
        ("Platform", platform.platform()),
        ("Project path", str(project_dir)),
        ("Path has spaces", "yes" if " " in str(project_dir) else "no"),
        ("Path length", str(len(str(project_dir)))),
        ("FFmpeg", shutil.which("ffmpeg") or "not found"),
        ("ffprobe", shutil.which("ffprobe") or "not found"),
        ("HF_HOME", os.environ.get("HF_HOME", "(default)")),
    ]

    print("Jump Caption readiness check")
    print("=" * 32)
    for label, value in checks:
        print(f"{label}: {value}")

    outputs = project_dir / "outputs"
    uploads = project_dir / "uploads"
    outputs.mkdir(exist_ok=True)
    uploads.mkdir(exist_ok=True)
    print(f"outputs writable: {os.access(outputs, os.W_OK)}")
    print(f"uploads writable: {os.access(uploads, os.W_OK)}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

