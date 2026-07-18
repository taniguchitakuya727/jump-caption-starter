from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


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

