from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.core.config import Settings
from app.main import create_app


def test_cors_origins_default_is_empty(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = Settings(_env_file=None, database_url="sqlite://")

    assert settings.cors_origins == []


def test_cors_origins_are_read_as_json(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173"]')

    settings = Settings(_env_file=None, database_url="sqlite://")

    assert settings.cors_origins == ["http://localhost:5173"]


def test_cors_rejects_wildcard_origin():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite://", cors_origins=["*"])


def test_health_returns_ok():
    response = TestClient(create_app()).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_configured_origins():
    client = TestClient(create_app(cors_origins=["https://pricescope.example.com"]))
    response = client.get(
        "/health",
        headers={"Origin": "https://pricescope.example.com"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://pricescope.example.com"


def test_cors_rejects_unauthorized_origins():
    client = TestClient(create_app(cors_origins=["https://pricescope.example.com"]))
    response = client.get(
        "/health",
        headers={"Origin": "https://evil-site.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_ready_returns_ready_when_db_available():
    with patch("app.db.session.engine.connect") as mock_connect:
        client = TestClient(create_app())
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    execute = mock_connect.return_value.__enter__.return_value.execute
    execute.assert_called_once()
    assert str(execute.call_args.args[0]) == "SELECT 1"


def test_ready_returns_503_when_db_fails():
    with patch("app.db.session.engine.connect", side_effect=Exception("Connection failed")):
        response = TestClient(create_app()).get("/ready")

    assert response.status_code == 503
    assert response.json() == {"status": "not ready"}
