from __future__ import annotations

import subprocess

from app.services import ffmpeg


def test_detect_ffmpeg_missing(monkeypatch) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda name: None)

    result = ffmpeg.detect_ffmpeg()

    assert result.available is False
    assert result.path is None
    assert result.version is None
    assert result.error is not None
    assert "FFmpeg が見つかりません" in result.error
    assert "README_WINDOWS.md" in result.error


def test_detect_ffmpeg_available(monkeypatch) -> None:
    monkeypatch.setattr(ffmpeg.shutil, "which", lambda name: "/usr/local/bin/ffmpeg")

    def fake_run(*args, **kwargs):
        return subprocess.CompletedProcess(
            args=args[0],
            returncode=0,
            stdout="ffmpeg version 6.1 Copyright\nconfiguration: test\n",
            stderr="",
        )

    monkeypatch.setattr(ffmpeg.subprocess, "run", fake_run)

    result = ffmpeg.detect_ffmpeg()

    assert result.available is True
    assert result.path == "/usr/local/bin/ffmpeg"
    assert result.version == "ffmpeg version 6.1 Copyright"
    assert result.error is None
