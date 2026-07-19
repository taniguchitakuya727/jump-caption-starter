from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app
from app.services.subtitles import SubtitleResult, SubtitleSegment
from app.services.video_processing import JumpCutResult, SilenceInterval


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_homepage_contains_file_picker() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert "Jump Caption" in response.text
    assert 'type="file"' in response.text
    assert "/static/app.js?v=sprint-a-subtitle-quality" in response.text
    assert "/static/style.css?v=sprint-a-subtitle-quality" in response.text
    assert "字幕エディタ" in response.text
    assert "caption-overlay" in response.text
    assert "続きから" in response.text
    assert "字幕を読みやすく整形" in response.text


def test_jump_cut_endpoint_returns_output_links(monkeypatch, tmp_path) -> None:
    output_path = tmp_path / "sample_cut.mp4"
    json_path = tmp_path / "sample_silences.json"
    output_path.write_bytes(b"mp4")
    json_path.write_text("{}", encoding="utf-8")

    def fake_run_jump_cut(input_path, output_dir, settings):
        assert Path(input_path).name == "sample.mp4"
        assert settings.silence_threshold_db == -32
        assert settings.min_silence_duration == 0.7
        assert settings.retained_margin == 0.2
        return JumpCutResult(
            output_path=output_path,
            silence_json_path=json_path,
            duration=3.0,
            silences=[SilenceInterval(start=1.0, end=1.8, duration=0.8)],
            logs=["ok"],
        )

    monkeypatch.setattr(main, "run_jump_cut", fake_run_jump_cut)

    response = client.post(
        "/api/jump-cut",
        files={"file": ("sample.mp4", b"fake-video", "video/mp4")},
        data={
            "silence_threshold_db": "-32",
            "min_silence_duration": "0.7",
            "retained_margin": "0.2",
        },
    )

    assert response.status_code == 200
    assert response.json()["output_url"] == "/outputs/sample_cut.mp4"
    assert response.json()["silence_json_url"] == "/outputs/sample_silences.json"


def test_whisper_status_endpoint(monkeypatch) -> None:
    monkeypatch.setattr(main, "faster_whisper_available", lambda: True)

    response = client.get("/api/whisper")

    assert response.status_code == 200
    assert response.json()["available"] is True
    assert response.json()["default_model"] == "small"
    assert response.json()["default_language"] == "ja"


def test_outputs_endpoint_lists_existing_files(monkeypatch, tmp_path) -> None:
    video_path = tmp_path / "sample_cut.mp4"
    video_path.write_bytes(b"mp4")
    metadata_path = tmp_path / "sample_cut_subtitles.json"
    metadata_path.write_text(
        '{"source":"sample_cut.mp4","segments":[{"text":"a"}],"logs":[]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)

    response = client.get("/api/outputs")

    assert response.status_code == 200
    assert response.json()["videos"][0]["file"] == "sample_cut.mp4"
    assert response.json()["subtitle_projects"][0]["file"] == "sample_cut_subtitles.json"
    assert response.json()["subtitle_projects"][0]["segments"] == 1


def test_subtitles_endpoint_returns_output_links(monkeypatch, tmp_path) -> None:
    media_path = tmp_path / "sample_cut.mp4"
    media_path.write_bytes(b"mp4")
    srt_path = tmp_path / "sample_cut.srt"
    txt_path = tmp_path / "sample_cut.txt"
    metadata_path = tmp_path / "sample_cut_subtitles.json"

    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)

    def fake_generate_subtitles(media_path, output_dir, settings):
        assert media_path.name == "sample_cut.mp4"
        assert settings.model_size == "small"
        assert settings.language == "ja"
        return SubtitleResult(
            srt_path=srt_path,
            txt_path=txt_path,
            metadata_path=metadata_path,
            segments=[
                SubtitleSegment(
                    index=1,
                    start=0.0,
                    end=1.0,
                    text="こんにちは",
                    avg_logprob=-0.2,
                    no_speech_prob=0.1,
                    suspicious=False,
                )
            ],
            logs=["ok"],
        )

    monkeypatch.setattr(main, "generate_subtitles", fake_generate_subtitles)

    response = client.post(
        "/api/subtitles",
        data={"filename": "sample_cut.mp4", "model_size": "small", "language": "ja"},
    )

    assert response.status_code == 200
    assert response.json()["srt_url"] == "/outputs/sample_cut.srt"
    assert response.json()["txt_url"] == "/outputs/sample_cut.txt"
    assert response.json()["metadata_url"] == "/outputs/sample_cut_subtitles.json"


def test_get_subtitle_metadata(monkeypatch, tmp_path) -> None:
    metadata_path = tmp_path / "sample_cut_subtitles.json"
    metadata_path.write_text(
        '{"source":"sample_cut.mp4","segments":[],"logs":[]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)

    response = client.get("/api/subtitles/sample_cut_subtitles.json")

    assert response.status_code == 200
    assert response.json()["video_url"] == "/outputs/sample_cut.mp4"
    assert response.json()["metadata_file"] == "sample_cut_subtitles.json"


def test_save_subtitles_endpoint_rewrites_srt(monkeypatch, tmp_path) -> None:
    metadata_path = tmp_path / "sample_cut_subtitles.json"
    metadata_path.write_text(
        '{"source":"sample_cut.mp4","segments":[],"logs":["generated"]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)

    response = client.post(
        "/api/subtitles/sample_cut_subtitles.json/save",
        json={
            "segments": [
                {
                    "start": 0,
                    "end": 1,
                    "text": "保存テスト",
                    "avg_logprob": None,
                    "no_speech_prob": None,
                    "suspicious": False,
                }
            ]
        },
    )

    assert response.status_code == 200
    assert response.json()["srt_url"] == "/outputs/sample_cut.srt"
    assert (tmp_path / "sample_cut.srt").read_text(encoding="utf-8") == (
        "1\n00:00:00,000 --> 00:00:01,000\n保存テスト\n"
    )


def test_format_subtitles_endpoint(monkeypatch, tmp_path) -> None:
    metadata_path = tmp_path / "sample_cut_subtitles.json"
    metadata_path.write_text(
        """
        {
          "source": "sample_cut.mp4",
          "segments": [
            {
              "start": 0,
              "end": 6,
              "text": "今日はジャンプカットと字幕編集の基本的な流れを確認します。",
              "avg_logprob": null,
              "no_speech_prob": null,
              "suspicious": false
            }
          ],
          "logs": []
        }
        """,
        encoding="utf-8",
    )
    monkeypatch.setattr(main, "OUTPUT_DIR", tmp_path)

    response = client.post(
        "/api/subtitles/sample_cut_subtitles.json/format",
        json={"max_chars_per_line": 10, "max_lines": 2, "max_duration": 3},
    )

    assert response.status_code == 200
    assert len(response.json()["segments"]) > 1
    assert response.json()["metadata_url"] == "/outputs/sample_cut_subtitles.json"
