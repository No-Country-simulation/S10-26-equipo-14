from contextlib import contextmanager
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

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


@pytest.fixture
def public_context():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app(
        cors_origins=[],
        app_settings=Settings(
            _env_file=None,
            database_url="sqlite://",
            app_env="production",
        ),
    )

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db

    @contextmanager
    def session_scope():
        with factory() as session:
            yield session

    try:
        with TestClient(app) as client:
            yield client, session_scope
    finally:
        app.dependency_overrides.clear()
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


def test_production_reads_and_management_access_are_public(public_context, monkeypatch):
    client, session_scope = public_context
    store_id, _listing_id = seed_public_rows(session_scope)
    monkeypatch.setattr("app.api.v1.router.MonedApiProvider.fetch", lambda _self: ())

    assert client.get("/api/v1/management/access").json() == {"can_manage": True}
    paths = [
        "/api/v1/stores",
        "/api/v1/categories",
        "/api/v1/products",
        "/api/v1/products/paginated?limit=10&offset=0",
        "/api/v1/products/paginated-with-prices?limit=10&offset=0",
        "/api/v1/price-observations",
        "/api/v1/exchange-rates?rate_type=official",
        "/api/v1/management/stores",
        f"/api/v1/management/stores/{store_id}/extractions",
    ]
    for path in paths:
        response = client.get(path)
        assert response.status_code == 200, (path, response.text)

    private_response = client.get("/api/v1/store-products")
    assert private_response.status_code == 404


def test_public_writes_do_not_require_admin_token(public_context):
    client, session_scope = public_context
    _store_id, listing_id = seed_public_rows(session_scope)

    created = client.post("/api/v1/management/stores", json={
        "name": "Tienda nueva",
        "base_url": "https://new-store.example",
        "country": "AR",
        "currency": "ARS",
    })
    assert created.status_code == 201
    assert created.json()["name"] == "Tienda nueva"

    observation = client.post("/api/v1/price-observations", json={
        "store_product_id": listing_id,
        "amount": "130.00",
        "currency": "ARS",
        "observed_at": "2026-01-02T12:00:00Z",
    })
    assert observation.status_code == 201

    with session_scope() as session:
        assert session.scalar(select(Store).where(Store.name == "Tienda nueva")) is not None
        assert len(session.scalars(select(PriceObservation)).all()) == 2


def test_public_management_reads_redact_internal_diagnostics(public_context):
    client, session_scope = public_context
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


def test_unhandled_get_errors_do_not_return_exception_details(public_context):
    client, _session_scope = public_context
    app = client.app

    def failing_db_dependency():
        raise RuntimeError("INTERNAL_DIAGNOSTIC_MARKER")
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = failing_db_dependency
    response = TestClient(app, raise_server_exceptions=False).get("/api/v1/categories")

    assert response.status_code == 500
    assert "INTERNAL_DIAGNOSTIC_MARKER" not in response.text
    assert response.text == "Internal Server Error"
