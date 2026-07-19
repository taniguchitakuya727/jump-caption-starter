from __future__ import annotations

from types import SimpleNamespace

from app.services.subtitles import (
    SubtitleFormatSettings,
    SubtitleSegment,
    _convert_segment,
    find_split_position,
    format_subtitle_segments,
    format_srt_time,
    save_subtitle_edit,
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


def test_convert_segment_keeps_word_timestamps() -> None:
    raw_segment = SimpleNamespace(
        start=0,
        end=1,
        text="テスト",
        avg_logprob=-0.2,
        no_speech_prob=0.1,
        words=[
            SimpleNamespace(word="テ", start=0.0, end=0.2, probability=0.9),
            SimpleNamespace(word="スト", start=0.2, end=0.8, probability=0.8),
        ],
    )

    segment = _convert_segment(1, raw_segment)

    assert segment.words == [
        {"word": "テ", "start": 0.0, "end": 0.2, "probability": 0.9},
        {"word": "スト", "start": 0.2, "end": 0.8, "probability": 0.8},
    ]


def test_save_subtitle_edit_rewrites_outputs(tmp_path) -> None:
    metadata_path = tmp_path / "sample_cut_subtitles.json"
    metadata_path.write_text(
        """
        {
          "source": "sample_cut.mp4",
          "settings": {"model_size": "tiny"},
          "segments": [],
          "logs": ["generated"]
        }
        """,
        encoding="utf-8",
    )

    result = save_subtitle_edit(
        metadata_path=metadata_path,
        output_dir=tmp_path,
        payload_segments=[
            {
                "start": 0,
                "end": 1.5,
                "text": "編集済み",
                "avg_logprob": -0.2,
                "no_speech_prob": 0.1,
                "suspicious": False,
            }
        ],
    )

    assert result.srt_path.read_text(encoding="utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,500\n編集済み\n"
    )
    assert result.txt_path.read_text(encoding="utf-8") == "編集済み\n"
    assert result.segments[0].index == 1


def test_format_subtitle_segments_wraps_and_splits_long_text() -> None:
    segments = [
        SubtitleSegment(
            index=1,
            start=0,
            end=6,
            text="今日はジャンプカットと字幕編集の基本的な流れを確認します。",
            avg_logprob=None,
            no_speech_prob=None,
            suspicious=False,
        )
    ]

    formatted = format_subtitle_segments(
        segments,
        SubtitleFormatSettings(max_chars_per_line=10, max_lines=2, max_duration=3),
    )

    assert len(formatted) > 1
    assert all(len(line) <= 20 for segment in formatted for line in segment.text.splitlines())
    assert formatted[0].suspicious is True


def test_format_subtitle_segments_merges_short_text() -> None:
    segments = [
        SubtitleSegment(1, 0, 0.4, "今日は", None, None, False),
        SubtitleSegment(2, 0.4, 1.4, "よろしくお願いします", None, None, False),
    ]

    formatted = format_subtitle_segments(
        segments,
        SubtitleFormatSettings(max_chars_per_line=18, max_lines=2, min_duration=0.8),
    )

    assert len(formatted) == 1
    assert formatted[0].text == "今日はよろしくお願いします"


def test_find_split_position_prefers_punctuation_near_target() -> None:
    text = "今日はジャンプカットをします。そして字幕を整えます。"

    split_at = find_split_position(text, 16)

    assert text[:split_at].endswith("。")


def test_find_split_position_avoids_leaving_particle_at_next_start() -> None:
    text = "今日は字幕の分割位置を自然に調整します"

    split_at = find_split_position(text, 10)

    assert text[split_at : split_at + 1] not in "はがをにへでともやの、。！？,.!?"
