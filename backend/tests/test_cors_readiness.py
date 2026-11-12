from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import ValidationError
import pytest

from app.core.config import DEFAULT_CORS_ORIGINS, Settings
from app.main import create_app


def test_cors_origins_default_include_local_and_deployed_frontends(monkeypatch):
    monkeypatch.delenv("CORS_ORIGINS", raising=False)

    settings = Settings(_env_file=None, database_url="sqlite://")

    assert settings.cors_origins == list(DEFAULT_CORS_ORIGINS)
    assert "https://pricescope-14.vercel.app" in settings.cors_origins


def test_runtime_defaults_are_production_and_management_is_public(monkeypatch):
    monkeypatch.delenv("APP_ENV", raising=False)

    settings = Settings(_env_file=None, database_url="sqlite://")
    response = TestClient(create_app(app_settings=settings)).get("/api/v1/management/access")

    assert settings.app_env == "production"
    assert response.status_code == 200
    assert response.json() == {"can_manage": True}


def test_runtime_environment_rejects_unknown_values():
    with pytest.raises(ValidationError):
        Settings(_env_file=None, database_url="sqlite://", app_env="staging")


def test_cors_origins_are_read_as_json(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["http://localhost:5173"]')

    settings = Settings(_env_file=None, database_url="sqlite://")

    assert settings.cors_origins == list(DEFAULT_CORS_ORIGINS)


def test_cors_origins_keep_additional_explicit_environment_origins(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", '["https://admin.pricescope.example"]')

    settings = Settings(_env_file=None, database_url="sqlite://")

    assert settings.cors_origins == [*DEFAULT_CORS_ORIGINS, "https://admin.pricescope.example"]


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


def test_vercel_origin_can_read_store_catalog(client):
    origin = "https://pricescope-14.vercel.app"

    response = client.get("/api/v1/stores", headers={"Origin": origin})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_preflight_allows_management_methods_from_supported_frontends():
    client = TestClient(create_app(cors_origins=list(DEFAULT_CORS_ORIGINS)))

    for origin in DEFAULT_CORS_ORIGINS:
        response = client.options(
            "/api/v1/management/stores",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "content-type",
            },
        )

        assert response.status_code == 200
        assert response.headers["access-control-allow-origin"] == origin
        assert "POST" in response.headers["access-control-allow-methods"]
        assert "PUT" in response.headers["access-control-allow-methods"]



def test_cors_allows_only_this_projects_vercel_preview_hostnames():
    client = TestClient(create_app(cors_origins=[]))
    allowed_origin = "https://s10-26-equipo-14-iwu6zn7qm-juan-perez-s-projects.vercel.app"
    response = client.options(
        "/api/v1/categories",
        headers={
            "Origin": allowed_origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == allowed_origin

    rejected = client.options(
        "/api/v1/categories",
        headers={
            "Origin": "https://another-project-123.vercel.app",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert rejected.status_code == 400


def test_management_endpoints_are_registered_in_local_openapi():
    paths = create_app(cors_origins=[]).openapi()["paths"]

    assert "/api/v1/management/stores" in paths
    assert {"get", "post"}.issubset(paths["/api/v1/management/stores"])
    assert "post" in paths["/api/v1/management/stores/{store_id}/analyze"]
    assert "put" in paths["/api/v1/management/stores/{store_id}/monitoring"]


def test_cors_rejects_unauthorized_origins():
    client = TestClient(create_app(cors_origins=["https://pricescope.example.com"]))
    response = client.get(
        "/health",
        headers={"Origin": "https://evil-site.com"},
    )

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_public_management_access_does_not_require_an_admin_token():
    settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        app_env="production",
        cors_origins=["https://pricescope.example.com"],
    )
    client = TestClient(create_app(app_settings=settings))

    response = client.get(
        "/api/v1/management/access",
        headers={"Origin": "https://pricescope.example.com"},
    )

    assert response.status_code == 200
    assert response.json() == {"can_manage": True}
    assert response.headers["access-control-allow-origin"] == "https://pricescope.example.com"


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
