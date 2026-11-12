from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import Category, ExtractionRun, PriceObservation, Store, StoreIntegration, StoreMonitoringPreference, StoreProduct
from app.analyzers.base import CategoryCandidate, StoreAnalysisResult
from app.extractors.base import ProductSnapshot


@pytest.fixture
def management_context(monkeypatch):
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app(
        cors_origins=["http://localhost:5173"],
        app_settings=Settings(
            _env_file=None,
            database_url="sqlite://",
            app_env="development",
            public_read_only=False,
        ),
    )

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    with factory() as session:
        session.add(Category(id=7, name="Computación", slug="computacion"))
        session.commit()
    with TestClient(app) as client:
        yield client, factory
    app.dependency_overrides.clear()
    Base.metadata.drop_all(engine)
    engine.dispose()


def test_production_store_management_writes_are_blocked_even_when_read_only_flag_is_false():
    app = create_app(
        cors_origins=["http://localhost:5173"],
        app_settings=Settings(
            _env_file=None,
            database_url="sqlite://",
            app_env="production",
            public_read_only=False,
        ),
    )
    with TestClient(app) as client:
        response = client.post("/api/v1/management/stores", json={
            "name": "Example", "base_url": "https://example.com", "country": "AR", "currency": "ARS",
        })
    assert response.status_code == 403
    assert response.json()["detail"] == "Operación bloqueada: esta API está en modo público de solo lectura."


def test_create_store_is_pending_and_duplicates_are_rejected(management_context):
    client, factory = management_context
    payload = {"name": "Example Store", "base_url": "https://example.com", "country": "AR", "currency": "ars"}

    created = client.post("/api/v1/management/stores", json=payload)
    assert created.status_code == 201
    assert created.json()["integration_status"] == "pending"
    assert created.json()["monitoring_enabled"] is False
    assert client.post("/api/v1/management/stores", json=payload).status_code == 201

    with factory() as session:
        assert len(session.scalars(select(Store)).all()) == 1
        assert session.scalar(select(StoreIntegration)).status == "pending"
        assert session.scalar(select(StoreMonitoringPreference)).is_enabled is False


def test_analysis_proposals_require_review_before_monitoring_activation(management_context, monkeypatch):
    client, factory = management_context

    class FakeAnalyzer:
        key = "test-fixture-analyzer"

        def analyze(self, store, categories):
            return StoreAnalysisResult(
                analyzer_key=self.key,
                message="Enlace de prueba observado; revisión necesaria.",
                categories=(CategoryCandidate("Computación", "https://example.com/categorias/computacion", 7),),
            )

    monkeypatch.setattr("app.services.store_analysis.analyzer_for_store", lambda _store: FakeAnalyzer())
    created = client.post("/api/v1/management/stores", json={
        "name": "Example Store", "base_url": "https://example.com", "country": "AR", "currency": "ARS",
    })
    store_id = created.json()["id"]

    analysis = client.post(f"/api/v1/management/stores/{store_id}/analyze")
    assert analysis.status_code == 200
    assert analysis.json()["integration_status"] == "configuration_required"
    assert analysis.json()["analysis_candidates"][0]["category_id"] == 7
    assert analysis.json()["monitoring_enabled"] is False

    invalid = client.put(f"/api/v1/management/stores/{store_id}/monitoring", json={
        "category_ids": [8], "currency": "ARS", "interval_hours": 24, "enabled": True,
    })
    assert invalid.status_code == 422

    activated = client.put(f"/api/v1/management/stores/{store_id}/monitoring", json={
        "category_ids": [7], "currency": "ARS", "interval_hours": 48, "enabled": True,
    })
    assert activated.status_code == 200
    assert activated.json()["integration_status"] == "active"
    assert activated.json()["monitoring_enabled"] is True
    assert "todavía no está disponible" in activated.json()["analysis_message"]

    with factory() as session:
        run = session.scalar(select(ExtractionRun))
        assert run.store_id == store_id
        assert run.source.startswith("analysis:")


def test_unsupported_store_analysis_never_fetches_user_host(management_context):
    client, _factory = management_context
    created = client.post("/api/v1/management/stores", json={
        "name": "Other Shop", "base_url": "https://shop.example", "country": "AR", "currency": "ARS",
    })
    store_id = created.json()["id"]
    result = client.post(f"/api/v1/management/stores/{store_id}/analyze")
    assert result.status_code == 200
    assert result.json()["integration_status"] == "configuration_required"
    assert result.json()["analyzer_key"] is None
    assert result.json()["analysis_candidates"] == []


def test_extract_endpoint_persists_run_and_history_without_network(management_context, monkeypatch):
    client, factory = management_context

    class FixtureExtractor:
        name = "Fixture extractor"

        def supports(self, _store): return True
        def prepare(self): return None
        def extract(self, listing):
            return ProductSnapshot(
                name="Producto de fixture",
                amount=Decimal("123.45"),
                currency="ARS",
                source_url=listing.product_url,
            )

    created = client.post("/api/v1/management/stores", json={
        "name": "Fixture Store", "base_url": "https://fixture.test", "country": "AR", "currency": "ARS",
    })
    store_id = created.json()["id"]
    with factory() as session:
        session.add(StoreProduct(
            store_id=store_id,
            product_url="https://fixture.test/product",
            product_name="Producto de fixture",
            currency="ARS",
        ))
        session.commit()

    monkeypatch.setattr("app.api.v1.stores.extractor_for_store", lambda _store: FixtureExtractor())
    result = client.post(f"/api/v1/management/stores/{store_id}/extract")
    assert result.status_code == 200
    payload = result.json()
    assert payload["status"] == "SUCCESS"
    assert payload["records_seen"] == 1
    assert payload["observations_created"] == 1
    assert payload["store_name"] == "Fixture Store"

    history = client.get(f"/api/v1/management/stores/{store_id}/extractions?limit=5")
    assert history.status_code == 200
    assert len(history.json()) == 1
    assert history.json()[0]["run_id"] == payload["run_id"]
    assert history.json()[0]["observations_created"] == 1
    assert len(client.get("/api/v1/price-observations", params={"store_id": store_id}).json()) == 1
    with factory() as session:
        run = session.get(ExtractionRun, payload["run_id"])
        observation = session.scalar(select(PriceObservation))
        assert run.store_id == store_id and run.status == "SUCCESS"
        assert observation.amount == Decimal("123.45")
