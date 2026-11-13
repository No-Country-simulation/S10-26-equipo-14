from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
import json

from sqlalchemy import func, select

from app.db.session import get_db
from app.main import app
from app.models import Category, ExtractionRun, PriceObservation, Product, Store, StoreProduct
from app.extractors.base import ProductSnapshot
from app.extractors.verified_stores import CredicoopExtractor
from app.extractors.strategies import parse_html_product
from app.extractors import extractor_for_store
from app.services.extraction import run_store_extraction


class FakeExtractor:
    name = "Extractor sintético de pruebas"

    def __init__(self, *, fail_on: set[int] | None = None, blocked_on: set[int] | None = None, barcode: str | None = "4006381333931", amount: Decimal = Decimal("1250.50")):
        self.fail_on = fail_on or set()
        self.blocked_on = blocked_on or set()
        self.calls: list[int] = []
        self.barcode = barcode
        self.amount = amount

    def supports(self, store):
        return True

    def prepare(self):
        return None

    def extract(self, listing):
        self.calls.append(listing.id)
        if listing.id in self.blocked_on:
            raise ValueError("BLOCKED: HTTP 403")
        if listing.id in self.fail_on:
            raise ValueError("fallo de fixture sintética")
        return ProductSnapshot(
            name=f"Producto ficticio {listing.id}",
            amount=self.amount,
            currency="ARS",
            source_url=listing.product_url,
            external_id=f"fixture-{listing.id}",
            barcode=self.barcode,
            brand="Marca ficticia",
            category_name="Hogar",
            is_available=True,
        )


def _session():
    return next(app.dependency_overrides[get_db]())


def _make_store(session, listing_count=1):
    category = Category(name="Hogar", slug="hogar")
    store = Store(name="Tienda de prueba", base_url="https://www.fravega.com")
    session.add_all([category, store])
    session.flush()
    listings = [
        StoreProduct(
            store_id=store.id,
            product_url=f"https://www.fravega.com/p/producto-ficticio-{i}/",
            product_name=f"Producto ficticio {i}",
        )
        for i in range(1, listing_count + 1)
    ]
    session.add_all(listings)
    session.commit()
    return store, listings


def test_run_persists_canonical_product_listing_price_and_run(client):
    session = _session()
    store, listings = _make_store(session)
    started_at = datetime(2026, 1, 1, tzinfo=timezone.utc)

    result = run_store_extraction(
        session,
        store.id,
        FakeExtractor(),
        started_at=started_at,
    )

    assert result.status == "SUCCESS"
    assert result.records_seen == 1
    assert result.observations_created == 1
    assert result.products_created == 1
    assert result.prices_changed == 0
    listing = session.get(StoreProduct, listings[0].id)
    product = session.get(Product, listing.product_id)
    observation = session.scalar(select(PriceObservation))
    run = session.get(ExtractionRun, result.run_id)
    assert product.name == "Producto ficticio 1"
    assert product.barcode == "4006381333931"
    assert product.category_id is None
    assert listing.category_id is not None
    assert listing.external_id == "fixture-1"
    assert observation.amount == Decimal("1250.50")
    assert observation.observed_at.replace(tzinfo=timezone.utc) == started_at
    assert run.status == "SUCCESS"
    session.close()


def test_same_run_timestamp_does_not_duplicate_price_history(client):
    session = _session()
    store, _ = _make_store(session)
    timestamp = datetime(2026, 1, 1, tzinfo=timezone.utc)

    first = run_store_extraction(session, store.id, FakeExtractor(), started_at=timestamp)
    retry = run_store_extraction(session, store.id, FakeExtractor(), started_at=timestamp)

    count = session.scalar(select(func.count()).select_from(PriceObservation))
    assert first.observations_created == 1
    assert retry.observations_created == 0
    assert count == 1
    session.close()


def test_repeated_unchanged_run_same_day_keeps_one_daily_observation(client):
    session = _session()
    store, _ = _make_store(session)
    first_time = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
    second_time = datetime(2026, 1, 1, 18, tzinfo=timezone.utc)

    first = run_store_extraction(session, store.id, FakeExtractor(), started_at=first_time)
    retry = run_store_extraction(session, store.id, FakeExtractor(), started_at=second_time)

    count = session.scalar(select(func.count()).select_from(PriceObservation))
    assert first.products_created == 1
    assert first.observations_created == 1
    assert retry.records_seen == 1
    assert retry.products_created == 0
    assert retry.prices_changed == 0
    assert retry.observations_created == 0
    assert count == 1
    session.close()


def test_price_change_same_day_appends_a_real_observation(client):
    session = _session()
    store, _ = _make_store(session)
    first_time = datetime(2026, 1, 1, 8, tzinfo=timezone.utc)
    changed_time = datetime(2026, 1, 1, 18, tzinfo=timezone.utc)

    run_store_extraction(session, store.id, FakeExtractor(), started_at=first_time)
    changed = run_store_extraction(
        session,
        store.id,
        FakeExtractor(amount=Decimal("1300.00")),
        started_at=changed_time,
    )

    observations = session.scalars(
        select(PriceObservation).order_by(PriceObservation.observed_at)
    ).all()
    assert len(observations) == 2
    assert observations[-1].amount == Decimal("1300.00")
    assert changed.prices_changed == 1
    assert changed.observations_created == 1
    session.close()


def test_new_extractions_append_historical_observations(client):
    session = _session()
    store, _ = _make_store(session)
    first_time = datetime(2026, 1, 1, tzinfo=timezone.utc)

    run_store_extraction(session, store.id, FakeExtractor(), started_at=first_time)
    run_store_extraction(
        session,
        store.id,
        FakeExtractor(),
        started_at=datetime(2026, 1, 2, tzinfo=timezone.utc),
    )

    timestamps = session.scalars(
        select(PriceObservation.observed_at).order_by(PriceObservation.observed_at)
    ).all()
    assert [value.replace(tzinfo=timezone.utc) for value in timestamps] == [
        first_time,
        datetime(2026, 1, 2, tzinfo=timezone.utc),
    ]
    session.close()


def test_links_existing_canonical_product_by_barcode_without_overwriting_it(client):
    session = _session()
    store, listings = _make_store(session)
    canonical = Product(
        name="Nombre canónico curado",
        brand="Marca curada",
        barcode="4006381333931",
    )
    session.add(canonical)
    session.commit()

    result = run_store_extraction(session, store.id, FakeExtractor())

    listing = session.get(StoreProduct, listings[0].id)
    linked = session.get(Product, listing.product_id)
    product_count = session.scalar(select(func.count()).select_from(Product))
    assert result.status == "SUCCESS"
    assert linked.id == canonical.id
    assert linked.name == "Nombre canónico curado"
    assert linked.brand == "Marca curada"
    assert listing.product_name == "Producto ficticio 1"
    assert product_count == 1
    session.close()


def test_conflicting_snapshot_gtin_does_not_relink_curated_product(client):
    session = _session()
    store, listings = _make_store(session)
    curated = Product(name="Producto curado", barcode="036000291452")
    session.add(curated)
    session.flush()
    listings[0].product_id = curated.id
    session.commit()
    curated_id = curated.id

    result = run_store_extraction(session, store.id, FakeExtractor())

    session.refresh(listings[0])
    assert result.observations_created == 0
    assert len(result.errors) == 1
    assert "Conflicto de GTIN" in result.errors[0]
    assert listings[0].product_id == curated_id
    assert session.get(Product, curated_id).barcode == "036000291452"
    assert session.scalar(select(func.count()).select_from(PriceObservation)) == 0
    session.close()


def test_extraction_rejects_bad_gtin_before_association_or_price_write(client):
    session = _session()
    store, listings = _make_store(session)

    result = run_store_extraction(session, store.id, FakeExtractor(barcode="4006381333932"))

    session.refresh(listings[0])
    assert result.observations_created == 0
    assert "GTIN inválido" in result.errors[0]
    assert listings[0].product_id is None
    assert session.scalar(select(func.count()).select_from(Product)) == 0
    assert session.scalar(select(func.count()).select_from(PriceObservation)) == 0
    session.close()


def test_partial_failure_is_recorded_without_losing_successful_listing(client):
    session = _session()
    store, listings = _make_store(session, listing_count=2)

    result = run_store_extraction(
        session,
        store.id,
        FakeExtractor(fail_on={listings[1].id}),
    )

    assert result.status == "PARTIAL_SUCCESS"
    assert result.records_seen == 1
    assert result.observations_created == 1
    assert len(result.errors) == 1
    assert session.get(ExtractionRun, result.run_id).error_summary
    assert session.scalar(select(func.count()).select_from(PriceObservation)) == 1
    session.close()


def test_blocked_portal_stops_the_remaining_batch(client):
    session = _session()
    store, listings = _make_store(session, listing_count=3)
    extractor = FakeExtractor(blocked_on={listings[0].id})

    result = run_store_extraction(session, store.id, extractor)

    assert result.status == "BLOCKED"
    assert extractor.calls == [listings[0].id]
    assert result.observations_created == 0
    assert session.scalar(select(func.count()).select_from(PriceObservation)) == 0
    session.close()


def test_credicoop_fixture_flows_through_general_parser_service_and_observation_endpoint(client):
    session = _session()
    fixture = Path(__file__).parent / "fixtures" / "extraction" / "credicoop_product_metadata.html"
    html = fixture.read_text(encoding="utf-8")
    product_url = (
        "https://tiendacredicoop.coop/televisores-y-accesorios/"
        "43925-smart-tv-samsung-qled-4-k-uhd-55-qn-55-q-6-faag-7798180339319.html"
    )

    parsed = parse_html_product(html, product_url, configured_currency="ARS")
    assert parsed.name == "Smart TV Samsung QLED 4K UHD 55 QN55Q6FAAG"
    assert parsed.amount == Decimal("1086665.88")
    assert parsed.currency == "ARS"
    assert parsed.extraction_format == "open_graph_product_metadata"

    store = Store(name="Tienda Credicoop fixture", base_url="https://tiendacredicoop.coop", country="Argentina")
    session.add(store)
    session.flush()
    assert isinstance(extractor_for_store(store), CredicoopExtractor)
    listing = StoreProduct(
        store=store,
        store_id=store.id,
        product_url=product_url,
        product_name=parsed.name,
        currency="ARS",
    )
    session.add(listing)
    session.commit()

    def fixture_fetch(url):
        if url.endswith("/robots.txt"):
            return "User-agent: *\nAllow: /\n"
        assert url == product_url
        return html

    extractor = CredicoopExtractor(get_text=fixture_fetch, minimum_interval_seconds=0)
    result = run_store_extraction(session, store.id, extractor)
    session.refresh(listing)
    product = session.get(Product, listing.product_id)
    observation = session.scalar(select(PriceObservation))
    run = session.get(ExtractionRun, result.run_id)

    assert result.status == "SUCCESS"
    assert listing.store_id == store.id
    assert listing.product_id == product.id
    assert listing.product_name == parsed.name
    assert observation.store_product_id == listing.id
    assert observation.amount == Decimal("1086665.88")
    assert observation.source_url == product_url
    assert run.status == "SUCCESS" and run.records_seen == 1
    assert run.store_id == store.id
    diagnostics = json.loads(run.error_summary)
    assert diagnostics["url"] == product_url
    assert diagnostics["http_status"] == 200
    assert diagnostics["content_type"] == "text/html"
    assert diagnostics["format"] == "open_graph_product_metadata"

    response = client.get(f"/api/v1/price-observations?store_id={store.id}")
    assert response.status_code == 200
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["store_product_id"] == listing.id
    assert rows[0]["amount"] == "1086665.88"
    assert rows[0]["currency"] == "ARS"
    assert rows[0]["source_url"] == product_url
    session.close()
