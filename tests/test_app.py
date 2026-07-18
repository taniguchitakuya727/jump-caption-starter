from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app import main
from app.main import app
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
