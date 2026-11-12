from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
import pytest

from app.db.base import Base
from app.db.session import get_db
from app.core.config import Settings
from app.main import app as application
import app.models  # noqa: F401 - register all mapped tables
from app.models import Category, ExchangeRate, PriceObservation, Product, Store, StoreProduct
from app.services.indicators import accumulated_inflation, compare_latest_prices, price_alerts, shrinkflation_signals


@pytest.fixture
def indicator_api():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = lambda: Session(engine, expire_on_commit=False)

    def override_db():
        with factory() as session:
            yield session

    previous = application.state.settings
    application.state.settings = Settings(_env_file=None, database_url="sqlite://", app_env="development", public_read_only=False)
    application.dependency_overrides[get_db] = override_db
    try:
        with TestClient(application) as test_client:
            yield test_client, factory
    finally:
        application.dependency_overrides.clear()
        application.state.settings = previous
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_comparisons_use_latest_observations_and_promotion_price():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session, session.begin():
            category = Category(name="Tecnologia", slug="tecnologia")
            product = Product(name="Telefono", category=category)
            first_store = Store(name="Tienda A", base_url="https://a.example.test")
            second_store = Store(name="Tienda B", base_url="https://b.example.test")
            session.add_all([product, first_store, second_store])
            session.flush()
            first = StoreProduct(store_id=first_store.id, product_id=product.id,
                                 product_url="https://a.example.test/p/1", product_name="Telefono")
            second = StoreProduct(store_id=second_store.id, product_id=product.id,
                                  product_url="https://b.example.test/p/1", product_name="Telefono")
            session.add_all([first, second])
            session.flush()
            session.add_all([
                PriceObservation(store_product_id=first.id, amount=Decimal("100"), currency="ARS",
                                 observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=first.id, amount=Decimal("130"), currency="ARS",
                                 observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=second.id, amount=Decimal("125"),
                                 promotional_price=Decimal("110"), currency="ARS",
                                 observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
            ])
            session.flush()
            comparisons = compare_latest_prices(session, category_id=category.id)
            assert len(comparisons) == 1
            result = comparisons[0]
            assert result["product_name"] == "Telefono"
            assert result["spread_amount"] == "20.00"
            assert Decimal(result["spread_percent"]) == Decimal(20) / Decimal(110) * 100
            assert {price["effective_price"] for price in result["prices"]} == {"130.00", "110.00"}
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_alerts_compare_same_listing_to_aligned_exchange_rate_and_find_spikes():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session, session.begin():
            product = Product(name="Cafe")
            store = Store(name="Tienda", base_url="https://shop.example.test")
            session.add_all([product, store])
            session.flush()
            listing = StoreProduct(store_id=store.id, product_id=product.id,
                                   product_url="https://shop.example.test/p/cafe", product_name="Cafe")
            session.add(listing)
            session.flush()
            older = datetime(2026, 11, 1, tzinfo=timezone.utc)
            newer = datetime(2026, 11, 2, tzinfo=timezone.utc)
            session.add_all([
                PriceObservation(store_product_id=listing.id, amount=Decimal("100"), currency="ARS", observed_at=older),
                PriceObservation(store_product_id=listing.id, amount=Decimal("130"), currency="ARS", observed_at=newer),
                ExchangeRate(source="official-fixture", rate_type="official", rate_side="reference",
                             rate=Decimal("100"), observed_at=older),
                ExchangeRate(source="official-fixture", rate_type="official", rate_side="reference",
                             rate=Decimal("110"), observed_at=newer),
            ])
            session.flush()
            alerts = price_alerts(session, rate_type="official", spike_percent=Decimal("20"))
            assert {alert["alert_type"] for alert in alerts} == {
                "price_spike", "price_increase_over_currency"
            }
            for alert in alerts:
                assert Decimal(alert["price_change_percent"]) == Decimal("30")
                assert Decimal(alert["exchange_rate_change_percent"]) == Decimal("10")
                assert alert["source_url"] is None
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_indicator_endpoints_serve_comparisons_and_alerts_from_sqlite(indicator_api):
    client, factory = indicator_api
    with factory() as session, session.begin():
        product = Product(name="Arroz")
        store_a = Store(name="Mercado A", base_url="https://a.example.test")
        store_b = Store(name="Mercado B", base_url="https://b.example.test")
        session.add_all([product, store_a, store_b])
        session.flush()
        listing_a = StoreProduct(store_id=store_a.id, product_id=product.id,
                                 product_url="https://a.example.test/p/1", product_name="Arroz")
        listing_b = StoreProduct(store_id=store_b.id, product_id=product.id,
                                 product_url="https://b.example.test/p/1", product_name="Arroz")
        session.add_all([listing_a, listing_b])
        session.flush()
        first = datetime(2026, 11, 1, tzinfo=timezone.utc)
        second = datetime(2026, 11, 2, tzinfo=timezone.utc)
        session.add_all([
            PriceObservation(store_product_id=listing_a.id, amount=Decimal("100"), currency="ARS", observed_at=first),
            PriceObservation(store_product_id=listing_a.id, amount=Decimal("130"), currency="ARS", observed_at=second),
            PriceObservation(store_product_id=listing_b.id, amount=Decimal("120"), currency="ARS", observed_at=second),
            ExchangeRate(source="test-official", rate_type="official", rate_side="reference", rate=Decimal("100"), observed_at=first),
            ExchangeRate(source="test-official", rate_type="official", rate_side="reference", rate=Decimal("110"), observed_at=second),
        ])

    comparisons = client.get("/api/v1/comparisons")
    alerts = client.get("/api/v1/alerts")
    assert comparisons.status_code == 200
    assert comparisons.json()[0]["spread_amount"] == "10.00"
    assert alerts.status_code == 200
    assert {item["alert_type"] for item in alerts.json()} == {
        "price_spike", "price_increase_over_currency"
    }


def test_shrinkflation_uses_explicit_same_listing_measurements_and_unit_conversion():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session, session.begin():
            product = Product(name="Leche", package_quantity=Decimal("800"), package_unit="g", package_count=1)
            store = Store(name="Market", base_url="https://market.test")
            session.add_all([product, store]); session.flush()
            listing = StoreProduct(store_id=store.id, product_id=product.id,
                                   product_url="https://market.test/leche", product_name=product.name)
            session.add(listing); session.flush()
            session.add_all([
                PriceObservation(store_product_id=listing.id, amount="1000", currency="ARS",
                    observed_package_quantity="1", observed_package_unit="kg", observed_package_count=1,
                    observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=listing.id, amount="1000", currency="ARS",
                    observed_package_quantity="800", observed_package_unit="g", observed_package_count=1,
                    observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
            ])
        result = shrinkflation_signals(session)
        assert len(result) == 1
        assert result[0]["status"] == "confirmed"
        assert Decimal(result[0]["previous_quantity"]) == Decimal("1000")
        assert Decimal(result[0]["latest_quantity"]) == Decimal("800")
        assert result[0]["unit"] == "g"
        assert Decimal(result[0]["unit_price_change_percent"]) == Decimal("25")
    finally:
        Base.metadata.drop_all(engine); engine.dispose()


def test_shrinkflation_ignores_unknown_measurements_currency_changes_and_unrelated_products():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session, session.begin():
            store = Store(name="Market", base_url="https://market.test")
            one, two = Product(name="A"), Product(name="B")
            session.add_all([store, one, two]); session.flush()
            listing = StoreProduct(store_id=store.id, product_id=one.id,
                product_url="https://market.test/a", product_name="A")
            unknown = StoreProduct(store_id=store.id, product_id=two.id,
                product_url="https://market.test/b", product_name="B")
            session.add_all([listing, unknown]); session.flush()
            session.add_all([
                PriceObservation(store_product_id=listing.id, amount="100", currency="ARS", observed_package_quantity="1", observed_package_unit="L", observed_package_count=1, observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=listing.id, amount="100", currency="USD", observed_package_quantity="900", observed_package_unit="ml", observed_package_count=1, observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=unknown.id, amount="100", currency="ARS", observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=unknown.id, amount="100", currency="ARS", observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
            ])
        assert shrinkflation_signals(session) == []
    finally:
        Base.metadata.drop_all(engine); engine.dispose()


def test_accumulated_inflation_uses_period_endpoints_and_separates_fx():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    start, end = datetime(2026, 11, 1, tzinfo=timezone.utc), datetime(2026, 11, 10, tzinfo=timezone.utc)
    try:
        with Session(engine) as session, session.begin():
            category = Category(name="Alimentos", slug="alimentos")
            product = Product(name="Arroz", category=category)
            store = Store(name="Market", base_url="https://market.test")
            session.add_all([product, store]); session.flush()
            category_id = category.id
            listing = StoreProduct(store_id=store.id, product_id=product.id,
                product_url="https://market.test/arroz", product_name=product.name)
            session.add(listing); session.flush()
            session.add_all([
                PriceObservation(store_product_id=listing.id, amount="100", currency="ARS", observed_at=start),
                PriceObservation(store_product_id=listing.id, amount="110", currency="ARS", observed_at=datetime(2026, 11, 5, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=listing.id, amount="120", promotional_price="115", currency="ARS", observed_at=end),
                ExchangeRate(source="fixture", rate_type="official", rate_side="reference", rate="100", observed_at=start),
                ExchangeRate(source="fixture", rate_type="official", rate_side="reference", rate="110", observed_at=end),
            ])
        result = accumulated_inflation(session, start=start, end=end)
        assert result["status"] == "available"
        currency = result["currencies"][0]
        assert Decimal(currency["inflation_percent"]) == Decimal("15")
        assert Decimal(currency["fx_variation_percent"]) == Decimal("10")
        assert Decimal(currency["price_minus_fx_percentage_points"]) == Decimal("5")
        assert result["products"][0]["listings"][0]["initial_price"] == "100.00"
        assert result["products"][0]["listings"][0]["final_price"] == "115.00"
        assert result["categories"][0]["category_id"] == category_id
    finally:
        Base.metadata.drop_all(engine); engine.dispose()


def test_accumulated_inflation_reports_insufficient_period_and_excludes_mixed_currency():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    start, end = datetime(2026, 11, 1, tzinfo=timezone.utc), datetime(2026, 11, 10, tzinfo=timezone.utc)
    try:
        with Session(engine) as session, session.begin():
            product = Product(name="Item")
            store = Store(name="Market", base_url="https://market.test")
            session.add_all([product, store]); session.flush()
            listing = StoreProduct(store_id=store.id, product_id=product.id,
                product_url="https://market.test/item", product_name=product.name)
            session.add(listing); session.flush()
            session.add_all([
                PriceObservation(store_product_id=listing.id, amount="100", currency="ARS", observed_at=start),
                PriceObservation(store_product_id=listing.id, amount="100", currency="USD", observed_at=end),
            ])
        assert accumulated_inflation(session, start=start, end=end)["status"] == "insufficient_data"
        assert accumulated_inflation(session, start=end, end=end)["status"] == "insufficient_data"
    finally:
        Base.metadata.drop_all(engine); engine.dispose()


def test_shrinkflation_identifies_possible_volume_and_count_reductions():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session, session.begin():
            store = Store(name="Market", base_url="https://market.test")
            volume = Product(name="Jugo")
            count = Product(name="Huevos")
            session.add_all([store, volume, count]); session.flush()
            listings = [StoreProduct(store_id=store.id, product_id=item.id,
                product_url=f"https://market.test/{item.name}", product_name=item.name) for item in (volume, count)]
            session.add_all(listings); session.flush()
            session.add_all([
                PriceObservation(store_product_id=listings[0].id, amount="1000", currency="ARS", observed_package_quantity="1", observed_package_unit="L", observed_package_count=1, observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=listings[0].id, amount="950", currency="ARS", observed_package_quantity="900", observed_package_unit="ml", observed_package_count=1, observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=listings[1].id, amount="600", currency="ARS", observed_package_quantity="6", observed_package_unit="ud", observed_package_count=1, observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
                PriceObservation(store_product_id=listings[1].id, amount="590", currency="ARS", observed_package_quantity="5", observed_package_unit="unidades", observed_package_count=1, observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
            ])
        signals = shrinkflation_signals(session)
        assert len(signals) == 2
        assert {signal["status"] for signal in signals} == {"possible"}
        assert {signal["unit"] for signal in signals} == {"ml", "unidad"}
    finally:
        Base.metadata.drop_all(engine); engine.dispose()


def test_indicator_api_exposes_period_inflation_and_shrinkflation(indicator_api):
    client, _factory = indicator_api
    base = {"start": "2026-11-01T00:00:00Z", "end": "2026-11-10T00:00:00Z"}
    inflation = client.get("/api/v1/indicators/inflation", params=base)
    shrinkflation = client.get("/api/v1/indicators/shrinkflation", params=base)
    assert inflation.status_code == 200
    assert inflation.json()["status"] == "insufficient_data"
    assert inflation.json()["currencies"] == []
    assert shrinkflation.status_code == 200
    assert shrinkflation.json() == []


def test_indicator_api_returns_persisted_inflation_and_shrinkflation(indicator_api):
    client, factory = indicator_api
    with factory() as session, session.begin():
        category = Category(name="Bebidas", slug="bebidas")
        product = Product(name="Jugo", category=category)
        store = Store(name="Mercado", base_url="https://market.test")
        session.add_all([product, store]); session.flush()
        listing = StoreProduct(store_id=store.id, product_id=product.id, category_id=category.id,
            product_url="https://market.test/jugo", product_name=product.name)
        session.add(listing); session.flush()
        session.add_all([
            PriceObservation(store_product_id=listing.id, amount="1000", currency="ARS",
                observed_package_quantity="1", observed_package_unit="L", observed_package_count=1,
                observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
            PriceObservation(store_product_id=listing.id, amount="1100", currency="ARS",
                observed_package_quantity="900", observed_package_unit="ml", observed_package_count=1,
                observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
        ])
    params = {"start": "2026-11-01T00:00:00Z", "end": "2026-11-02T23:59:59Z", "category_id": category.id}
    inflation = client.get("/api/v1/indicators/inflation", params=params)
    signals = client.get("/api/v1/indicators/shrinkflation", params=params)
    assert inflation.status_code == 200
    assert Decimal(inflation.json()["products"][0]["inflation_percent"]) == Decimal("10")
    assert inflation.json()["categories"][0]["category_id"] == category.id
    assert signals.status_code == 200
    assert signals.json()[0]["status"] == "confirmed"
    assert signals.json()[0]["unit"] == "ml"


def test_seeded_demo_records_are_not_mixed_into_real_catalog_or_indicators(indicator_api):
    client, factory = indicator_api
    with factory() as session, session.begin():
        category = Category(name="DEMO PriceScope Alimentos", slug="demo-pricescope-alimentos")
        product = Product(name="DEMO PriceScope Producto 01", category=category)
        store = Store(name="DEMO PriceScope Tienda A", base_url="https://pricescope-demo-a.example.invalid")
        session.add_all([product, store]); session.flush()
        listing = StoreProduct(store_id=store.id, product_id=product.id, category_id=category.id,
            product_url="https://pricescope-demo-a.example.invalid/items/01", product_name=product.name)
        session.add(listing); session.flush()
        session.add_all([
            PriceObservation(store_product_id=listing.id, amount="100", currency="ARS", observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc)),
            PriceObservation(store_product_id=listing.id, amount="200", currency="ARS", observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc)),
        ])
    assert all(not item["name"].startswith("DEMO PriceScope") for item in client.get("/api/v1/products").json())
    assert all(not item["name"].startswith("DEMO PriceScope") for item in client.get("/api/v1/stores").json())
    assert all(not item["name"].startswith("DEMO PriceScope") for item in client.get("/api/v1/categories").json())
    assert client.get("/api/v1/price-observations").json() == []
    window = {"start": "2026-11-01T00:00:00Z", "end": "2026-11-03T00:00:00Z"}
    assert client.get("/api/v1/indicators/inflation", params=window).json()["status"] == "insufficient_data"
    assert client.get("/api/v1/indicators/shrinkflation", params=window).json() == []
    assert client.get("/api/v1/comparisons").json() == []
    assert client.get("/api/v1/alerts").json() == []
