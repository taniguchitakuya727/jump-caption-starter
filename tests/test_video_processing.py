from __future__ import annotations

from app.services.video_processing import (
    SilenceInterval,
    build_keep_segments,
    parse_silence_log,
)


def test_parse_silence_log() -> None:
    log_text = """
    [silencedetect @ 0x123] silence_start: 1.25
    [silencedetect @ 0x123] silence_end: 2.75 | silence_duration: 1.5
    [silencedetect @ 0x123] silence_start: 4
    [silencedetect @ 0x123] silence_end: 5.25 | silence_duration: 1.25
    """

    silences = parse_silence_log(log_text)

    assert silences == [
        SilenceInterval(start=1.25, end=2.75, duration=1.5),
        SilenceInterval(start=4.0, end=5.25, duration=1.25),
    ]


def test_build_keep_segments_keeps_margin_around_speech() -> None:
    segments = build_keep_segments(
        duration=8.0,
        silences=[SilenceInterval(start=2.0, end=4.0, duration=2.0)],
        retained_margin=0.25,
    )

    assert [(segment.start, segment.end) for segment in segments] == [
        (0.0, 2.25),
        (3.75, 8.0),
    ]


def test_build_keep_segments_ignores_silence_shorter_than_margins() -> None:
    segments = build_keep_segments(
        duration=3.0,
        silences=[SilenceInterval(start=1.0, end=1.2, duration=0.2)],
        retained_margin=0.15,
    )

    assert [(segment.start, segment.end) for segment in segments] == [(0.0, 3.0)]

