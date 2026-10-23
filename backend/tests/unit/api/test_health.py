from fastapi.testclient import TestClient
from pytest import MonkeyPatch

from benchguard import __version__
from benchguard.api.app import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_models_without_key(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    response = client.get("/api/models")
    assert response.status_code == 200
    assert response.json() == {"sam": False, "spark": False}
