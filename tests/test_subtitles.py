from __future__ import annotations

from types import SimpleNamespace

from app.services.subtitles import (
    SubtitleSegment,
    _convert_segment,
    format_srt_time,
    to_srt,
    to_txt,
)


def test_format_srt_time() -> None:
    assert format_srt_time(3723.4567) == "01:02:03,457"


def test_to_srt() -> None:
    segments = [
        SubtitleSegment(
            index=1,
            start=0.0,
            end=1.25,
            text="こんにちは",
            avg_logprob=-0.2,
            no_speech_prob=0.1,
            suspicious=False,
        )
    ]

    assert to_srt(segments) == "1\n00:00:00,000 --> 00:00:01,250\nこんにちは\n"


def test_to_txt() -> None:
    segments = [
        SubtitleSegment(1, 0.0, 1.0, "一行目", -0.2, 0.1, False),
        SubtitleSegment(2, 1.0, 2.0, "二行目", -0.3, 0.2, False),
    ]

    assert to_txt(segments) == "一行目\n二行目\n"


def test_convert_segment_marks_suspicious() -> None:
    raw_segment = SimpleNamespace(
        start=1,
        end=2,
        text="  不確か  ",
        avg_logprob=-1.2,
        no_speech_prob=0.1,
    )

    segment = _convert_segment(1, raw_segment)

    assert segment.text == "不確か"
    assert segment.suspicious is True

