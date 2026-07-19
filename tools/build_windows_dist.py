from __future__ import annotations

import shutil
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]
DIST_DIR = PROJECT_DIR / "dist_windows" / "jump-caption-mvp"

FILES = [
    "pyproject.toml",
    "README.md",
    "README_WINDOWS.md",
    "start_windows.bat",
    "install_ffmpeg_windows.bat",
    "tools/check_windows_readiness.py",
]

DIRS = [
    "app",
]


def copy_file(relative_path: str) -> None:
    source = PROJECT_DIR / relative_path
    target = DIST_DIR / relative_path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)


def copy_dir(relative_path: str) -> None:
    source = PROJECT_DIR / relative_path
    target = DIST_DIR / relative_path
    if target.exists():
        shutil.rmtree(target)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store")
    shutil.copytree(source, target, ignore=ignore)


def main() -> int:
    if DIST_DIR.exists():
        shutil.rmtree(DIST_DIR)
    DIST_DIR.mkdir(parents=True)

    for relative_path in FILES:
        copy_file(relative_path)
    for relative_path in DIRS:
        copy_dir(relative_path)

    (DIST_DIR / "outputs").mkdir()
    (DIST_DIR / "uploads").mkdir()
    (DIST_DIR / "WINDOWS_PACKAGE.txt").write_text(
        "\n".join(
            [
                "Jump Caption MVP Windows test package",
                "",
                "Double-click start_windows.bat to launch.",
                "If FFmpeg is missing, double-click install_ffmpeg_windows.bat.",
                "Read README_WINDOWS.md before sending this folder to a tester.",
                "",
                "This package does not include Python, FFmpeg, a virtual environment,",
                "uploaded videos, generated outputs, or Whisper model files.",
                "",
            ]
        ),
        encoding="utf-8",
    )

    print(f"created: {DIST_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
