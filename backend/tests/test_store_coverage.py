from datetime import datetime, timedelta, timezone
from decimal import Decimal

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
    ExtractionRun,
    PriceObservation,
    Product,
    Store,
    StoreProduct,
)
from app.services.indicators import compare_latest_prices, price_alerts


class VerifiedFixtureExtractor:
    name = "Fixture provider adapter"

    def supports(self, _store):
        return True

    def prepare(self):
        return None

    def extract(self, listing):
        from app.extractors.base import ProductSnapshot

        return ProductSnapshot(name=listing.product_name, amount=Decimal("100"), currency="ARS",
                               source_url=listing.product_url)


@pytest.fixture
def coverage_context(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app(cors_origins=[], app_settings=Settings(
        _env_file=None,
        database_url="sqlite://",
        app_env="production",
        public_read_only=True,
        admin_api_token="coverage-test-token",
    ))

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    monkeypatch.setattr("app.api.v1.stores.extractor_for_store", lambda _store: VerifiedFixtureExtractor())
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def _store(session, *, name="Frávega", active=True):
    store = Store(name=name, base_url="https://www.fravega.com", country="Argentina", is_active=active)
    session.add(store)
    session.flush()
    return store


def _listing(session, store, product=None, *, name="Producto", url="https://www.fravega.com/p/producto/"):
    listing = StoreProduct(store_id=store.id, product_id=product.id if product else None,
                           product_url=url, product_name=name, currency="ARS")
    session.add(listing)
    session.flush()
    return listing


def _run(session, store, status, started):
    run = ExtractionRun(store_id=store.id, source="fixture-adapter", status=status,
                        started_at=started, finished_at=started + timedelta(minutes=1), records_seen=1)
    session.add(run)
    session.flush()
    return run


def _coverage(client, store_id):
    response = client.get("/api/v1/management/stores")
    assert response.status_code == 200
    return next(row for row in response.json() if row["id"] == store_id)


@pytest.mark.parametrize(
    ("run_status", "persist_observation", "expected"),
    [
        ("SUCCESS", True, "operational"),
        ("PARTIAL_SUCCESS", True, "partial"),
        ("NETWORK_ERROR", False, "failed"),
        ("SUCCESS", False, "no_data"),
    ],
)
def test_coverage_distinguishes_success_partial_failure_and_empty(
    coverage_context, run_status, persist_observation, expected
):
    client, factory = coverage_context
    started = datetime(2026, 11, 1, tzinfo=timezone.utc)
    with factory() as session:
        store = _store(session)
        listing = _listing(session, store)
        _run(session, store, run_status, started)
        if persist_observation:
            session.add(PriceObservation(store_product_id=listing.id, amount=100, currency="ARS",
                                         observed_at=started, is_available=True))
        session.commit()

    result = _coverage(client, store.id)
    assert result["coverage_status"] == expected
    assert result["is_operational"] is (expected == "operational")


def test_latest_failed_run_does_not_reuse_previous_success(coverage_context):
    client, factory = coverage_context
    started = datetime(2026, 11, 1, tzinfo=timezone.utc)
    with factory() as session:
        store = _store(session)
        listing = _listing(session, store)
        _run(session, store, "SUCCESS", started)
        session.add(PriceObservation(store_product_id=listing.id, amount=100, currency="ARS",
                                     observed_at=started, is_available=True))
        _run(session, store, "BLOCKED", started + timedelta(days=1))
        session.commit()
    result = _coverage(client, store.id)
    assert result["coverage_status"] == "failed"
    assert result["is_operational"] is False


def test_unverified_generic_adapter_is_not_configured_or_operational(coverage_context, monkeypatch):
    from app.extractors.public_store import PublicStoreExtractor

    client, factory = coverage_context
    with factory() as session:
        store = _store(session, name="Tienda HTML genérica")
        store.base_url = "https://shop.example"
        listing = _listing(session, store, url="https://shop.example/product/item")
        started = datetime(2026, 11, 1, tzinfo=timezone.utc)
        _run(session, store, "SUCCESS", started)
        session.add(PriceObservation(store_product_id=listing.id, amount=100, currency="ARS",
                                     observed_at=started, is_available=True))
        session.commit()
        store_id = store.id
    monkeypatch.setattr("app.api.v1.stores.extractor_for_store", lambda _store: PublicStoreExtractor())
    result = _coverage(client, store_id)
    assert result["coverage_status"] == "connector_unverified"
    assert result["connector_configured"] is False
    assert result["is_operational"] is False
    response = client.post(f"/api/v1/management/stores/{store_id}/extract", headers={
        "X-Admin-API-Token": "coverage-test-token",
    })
    assert response.status_code == 422


@pytest.mark.parametrize(
    ("active", "has_listing", "expected_status"),
    [(False, True, "inactive"), (True, False, "no_listings")],
)
def test_coverage_reports_inactive_and_missing_listing_reason(
    coverage_context, active, has_listing, expected_status
):
    client, factory = coverage_context
    with factory() as session:
        store = _store(session, active=active)
        if has_listing:
            _listing(session, store)
        session.commit()
        store_id = store.id
    assert _coverage(client, store_id)["coverage_status"] == expected_status


@pytest.mark.parametrize(
    ("active", "listing", "compatible", "expected_status"),
    [
        (False, True, True, 409),
        (True, False, True, 409),
        (True, True, False, 422),
    ],
)
def test_extraction_endpoint_checks_server_preconditions(
    coverage_context, monkeypatch, active, listing, compatible, expected_status
):
    client, factory = coverage_context
    with factory() as session:
        store = _store(session, active=active)
        if listing:
            _listing(session, store)
        session.commit()
        store_id = store.id

    if not compatible:
        from app.extractors import ExtractionError

        def unsupported(_store):
            raise ExtractionError("No existe un conector registrado")

        monkeypatch.setattr("app.api.v1.stores.extractor_for_store", unsupported)
    response = client.post(f"/api/v1/management/stores/{store_id}/extract", headers={
        "X-Admin-API-Token": "coverage-test-token",
    })
    assert response.status_code == expected_status
    with factory() as session:
        assert session.scalar(select(ExtractionRun).where(ExtractionRun.store_id == store_id)) is None


def test_extraction_endpoint_still_requires_admin_token(coverage_context):
    client, factory = coverage_context
    with factory() as session:
        store = _store(session)
        _listing(session, store)
        session.commit()
        store_id = store.id
    assert client.post(f"/api/v1/management/stores/{store_id}/extract").status_code == 401


def test_fravega_extraction_rejects_invalid_listing_url(coverage_context, monkeypatch):
    from app.extractors.fravega import FravegaExtractor

    client, factory = coverage_context
    with factory() as session:
        store = _store(session)
        _listing(session, store, url="https://www.fravega.com/category/search/")
        session.commit()
        store_id = store.id
    monkeypatch.setattr("app.api.v1.stores.extractor_for_store", lambda _store: FravegaExtractor())
    response = client.post(f"/api/v1/management/stores/{store_id}/extract", headers={
        "X-Admin-API-Token": "coverage-test-token",
    })
    assert response.status_code == 422
    assert response.json()["detail"] == "La tienda tiene una publicación inválida o fuera del dominio permitido."


def test_comparison_alerts_and_store_candidates_exclude_unavailable_and_demo(coverage_context):
    client, factory = coverage_context
    now = datetime(2026, 11, 12, tzinfo=timezone.utc)
    with factory() as session:
        category = Category(name="Alimentos", slug="alimentos")
        demo_category = Category(name="DEMO PriceScope category", slug="demo-category")
        session.add_all([category, demo_category])
        session.flush()
        product = Product(name="Aceite real", category_id=category.id)
        demo = Product(name="DEMO PriceScope Aceite", category_id=demo_category.id)
        session.add_all([product, demo])
        session.flush()
        stores = [_store(session, name=f"Tienda {index}") for index in range(3)]
        real_a = _listing(session, stores[0], product)
        real_b = _listing(session, stores[1], product)
        demo_listing = _listing(session, stores[2], demo, name=demo.name)
        session.add_all([
            PriceObservation(store_product_id=real_a.id, amount=100, currency="ARS", observed_at=now,
                             is_available=True),
            PriceObservation(store_product_id=real_b.id, amount=200, currency="ARS", observed_at=now,
                             is_available=False),
            PriceObservation(store_product_id=demo_listing.id, amount=100, currency="ARS",
                             observed_at=now - timedelta(days=1), is_available=True),
            PriceObservation(store_product_id=demo_listing.id, amount=200, currency="ARS",
                             observed_at=now, is_available=True),
        ])
        session.commit()

        comparisons = compare_latest_prices(session, start=now - timedelta(days=2), end=now)
        alerts = price_alerts(session, start=now - timedelta(days=2), end=now)

    assert comparisons == []
    assert alerts == []
    for eligible_for in ("comparisons", "alerts"):
        response = client.get("/api/v1/stores", params={
            "with_observations": "true", "eligible_for": eligible_for,
            "start": (now - timedelta(days=2)).isoformat(), "end": now.isoformat(),
        })
        assert response.status_code == 200
        assert response.json() == []


def test_store_candidates_only_include_actual_comparison_and_alert_history(coverage_context):
    client, factory = coverage_context
    now = datetime(2026, 11, 12, tzinfo=timezone.utc)
    with factory() as session:
        category = Category(name="Bebidas", slug="bebidas")
        session.add(category)
        session.flush()
        product = Product(name="Producto comparable", category_id=category.id)
        session.add(product)
        session.flush()
        stores = [_store(session, name=f"Tienda válida {index}") for index in range(2)]
        listings = [_listing(session, store, product) for store in stores]
        session.add_all([
            PriceObservation(store_product_id=listings[0].id, amount=100, currency="ARS",
                             observed_at=now - timedelta(days=1), is_available=True),
            PriceObservation(store_product_id=listings[1].id, amount=120, currency="ARS",
                             observed_at=now, is_available=True),
            PriceObservation(store_product_id=listings[0].id, amount=100, currency="ARS",
                             observed_at=now, is_available=True),
        ])
        session.commit()

    period = {
        "with_observations": "true",
        "start": (now - timedelta(days=2)).isoformat(),
        "end": now.isoformat(),
    }
    comparison_stores = client.get("/api/v1/stores", params={**period, "eligible_for": "comparisons"})
    alert_stores = client.get("/api/v1/stores", params={**period, "eligible_for": "alerts"})
    assert {row["name"] for row in comparison_stores.json()} == {"Tienda válida 0", "Tienda válida 1"}
    assert {row["name"] for row in alert_stores.json()} == {"Tienda válida 0"}
