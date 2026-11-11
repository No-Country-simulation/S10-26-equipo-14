from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.v1.management_security import READ_ONLY_DETAIL, WRITE_METHODS
from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import (
    Category,
    ExchangeRate,
    ExtractionRun,
    PriceObservation,
    Store,
    StoreIntegration,
    StoreProduct,
)


EXPECTED_MUTATIONS = {
    ("POST", "/api/v1/store-products"),
    ("POST", "/api/v1/price-observations"),
    ("POST", "/api/v1/management/stores"),
    ("POST", "/api/v1/management/stores/{store_id}/analyze"),
    ("POST", "/api/v1/management/stores/{store_id}/extract"),
    ("PUT", "/api/v1/management/stores/{store_id}/monitoring"),
}


@pytest.fixture
def write_policy_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def make_client(app_env: str, public_read_only: bool):
        config = Settings(
            _env_file=None,
            database_url="sqlite://",
            cors_origins=[],
            app_env=app_env,
            public_read_only=public_read_only,
        )
        api = create_app(cors_origins=[], app_settings=config)

        def override_db():
            with factory() as session:
                yield session

        api.dependency_overrides[get_db] = override_db
        return api, TestClient(api)

    @contextmanager
    def session_scope():
        with factory() as session:
            yield session

    try:
        yield make_client, session_scope
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def seed_public_rows(session_scope):
    with session_scope() as session:
        store = Store(name="Tienda pública", base_url="https://store.example", country="AR")
        category = Category(name="Hogar", slug="hogar")
        session.add_all([store, category])
        session.flush()
        listing = StoreProduct(
            store_id=store.id,
            category_id=category.id,
            product_url="https://store.example/item",
            product_name="Producto público",
            currency="ARS",
        )
        session.add(listing)
        session.flush()
        session.add_all([
            PriceObservation(
                store_product_id=listing.id,
                amount=125.50,
                currency="ARS",
                observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
            ExchangeRate(
                source="fixture",
                rate_type="official",
                rate_side="reference",
                base_currency="USD",
                quote_currency="ARS",
                rate=1200,
                observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc),
            ),
        ])
        session.commit()
        return store.id, listing.id


def test_production_get_endpoints_remain_public(write_policy_context):
    make_client, session_scope = write_policy_context
    store_id, _listing_id = seed_public_rows(session_scope)
    _api, client = make_client("production", True)
    with client:
        paths = [
            "/api/v1/stores",
            "/api/v1/categories",
            "/api/v1/products",
            "/api/v1/products/paginated?limit=10&offset=0",
            "/api/v1/products/paginated-with-prices?limit=10&offset=0",
            "/api/v1/price-observations",
            "/api/v1/exchange-rates",
            "/api/v1/management/stores",
            f"/api/v1/management/stores/{store_id}/extractions",
        ]
        for path in paths:
            response = client.get(path)
            assert response.status_code == 200, (path, response.text)
            if "/paginated" in path:
                assert set(response.json()) == {"items", "total", "limit", "offset"}

        private_response = client.get("/api/v1/store-products")
        assert private_response.status_code == 404
        assert private_response.json() == {"detail": "Recurso no disponible en el modo público."}


def test_public_management_reads_redact_internal_diagnostics(write_policy_context):
    make_client, session_scope = write_policy_context
    store_id, _listing_id = seed_public_rows(session_scope)
    with session_scope() as session:
        session.add(StoreIntegration(
            store_id=store_id,
            status="error",
            analyzer_key="internal-analyzer-v1",
            analysis_message="RuntimeError: internal diagnostic marker C:\\private\\file.py",
            analysis_candidates=[{
                "name": "Hogar",
                "source_url": "https://store.example/category/home",
                "category_id": 1,
            }],
        ))
        session.add(ExtractionRun(
            store_id=store_id,
            source="internal-extractor-v1",
            status="failed",
            started_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
            finished_at=datetime(2026, 1, 2, 0, 1, tzinfo=timezone.utc),
            records_seen=1,
            error_summary="RuntimeError: internal diagnostic marker C:\\private\\file.py https://store.example/private-token",
        ))
        session.commit()

    _api, client = make_client("production", True)
    with client:
        stores_response = client.get("/api/v1/management/stores")
        history_response = client.get(f"/api/v1/management/stores/{store_id}/extractions")

    assert stores_response.status_code == 200
    store_payload = stores_response.json()[0]
    assert store_payload["analyzer_key"] is None
    assert "internal diagnostic marker" not in str(store_payload)
    assert "C:\\private" not in str(store_payload)
    assert store_payload["analysis_candidates"][0]["source_url"] == "https://store.example/category/home"

    assert history_response.status_code == 200
    run_payload = history_response.json()[0]
    assert run_payload["source"] == "Extracción"
    assert run_payload["error_summary"] is None
    assert "internal diagnostic marker" not in history_response.text
    assert "private-token" not in history_response.text

    _api, local_client = make_client("development", False)
    with local_client:
        local_store = local_client.get("/api/v1/management/stores").json()[0]
        local_history = local_client.get(f"/api/v1/management/stores/{store_id}/extractions").json()[0]
    assert local_store["analyzer_key"] == "internal-analyzer-v1"
    assert "internal diagnostic marker" in local_store["analysis_message"]
    assert local_history["source"] == "internal-extractor-v1"
    assert "internal diagnostic marker" in local_history["error_summary"]


def test_unhandled_get_errors_do_not_return_exception_details(write_policy_context):
    make_client, _session_scope = write_policy_context
    api, _client = make_client("production", True)

    def failing_db_dependency():
        raise RuntimeError("INTERNAL_DIAGNOSTIC_MARKER")
        yield  # pragma: no cover - the exception is raised before yielding

    api.dependency_overrides[get_db] = failing_db_dependency
    client = TestClient(api, raise_server_exceptions=False)
    response = client.get("/api/v1/categories")

    assert response.status_code == 500
    assert "INTERNAL_DIAGNOSTIC_MARKER" not in response.text
    assert response.text == "Internal Server Error"


def test_production_blocks_every_registered_mutation_without_database_changes(write_policy_context):
    make_client, session_scope = write_policy_context
    seed_public_rows(session_scope)
    api, client = make_client("production", False)
    registered_mutations = {
        (method, route.path)
        for route in api.routes
        if getattr(route, "path", "").startswith("/api/")
        for method in (getattr(route, "methods", set()) or set())
        if method in WRITE_METHODS
    }
    assert registered_mutations == EXPECTED_MUTATIONS

    with client:
        for method, route_path in sorted(registered_mutations):
            concrete_path = route_path.replace("{store_id}", "1")
            response = client.request(method, concrete_path, json={})
            assert response.status_code == 403, (method, route_path, response.text)
            assert response.json()["detail"] == READ_ONLY_DETAIL

    with session_scope() as session:
        assert session.scalar(select(func.count()).select_from(Store)) == 1
        assert session.scalar(select(func.count()).select_from(StoreProduct)) == 1
        assert session.scalar(select(func.count()).select_from(PriceObservation)) == 1


def test_blocked_extraction_and_analysis_never_call_external_services(write_policy_context, monkeypatch):
    make_client, session_scope = write_policy_context
    seed_public_rows(session_scope)
    _api, client = make_client("production", False)

    def fail_if_called(*_args, **_kwargs):
        raise AssertionError("external operation must not run in read-only mode")

    monkeypatch.setattr("app.api.v1.stores.extractor_for_store", fail_if_called)
    monkeypatch.setattr("app.api.v1.stores.analyze_store", fail_if_called)
    with client:
        extract_response = client.post("/api/v1/management/stores/1/extract")
        analyze_response = client.post("/api/v1/management/stores/1/analyze")
    assert extract_response.status_code == 403
    assert analyze_response.status_code == 403


def test_explicit_development_mode_allows_expected_api_writes(write_policy_context):
    make_client, session_scope = write_policy_context
    _store_id, listing_id = seed_public_rows(session_scope)
    _api, client = make_client("development", False)
    with client:
        listing_response = client.post("/api/v1/store-products", json={
            "store_id": 1,
            "product_url": "https://store.example/second-item",
            "product_name": "Segundo producto",
            "currency": "ARS",
        })
        observation_response = client.post("/api/v1/price-observations", json={
            "store_product_id": listing_id,
            "amount": "130.00",
            "currency": "ARS",
            "observed_at": "2026-01-02T12:00:00Z",
        })
    assert listing_response.status_code == 201
    assert observation_response.status_code == 201


def test_test_environment_is_fail_closed_even_if_read_only_flag_is_false(write_policy_context):
    make_client, _session_scope = write_policy_context
    _api, client = make_client("test", False)
    with client:
        response = client.post("/api/v1/price-observations", json={})
    assert response.status_code == 403
