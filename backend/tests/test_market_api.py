from contextlib import contextmanager
from datetime import datetime, timezone

import pytest


@contextmanager
def _manual_db_session():
    from app.db.session import get_db
    from app.main import app

    dependency_generator = app.dependency_overrides[get_db]()
    try:
        yield next(dependency_generator)
    finally:
        dependency_generator.close()


def test_manual_db_session_finalizes_dependency_when_test_raises(client, monkeypatch):
    from app.db.session import get_db
    from app.main import app

    finalized = False

    def dependency():
        nonlocal finalized
        try:
            yield object()
        finally:
            finalized = True

    monkeypatch.setitem(app.dependency_overrides, get_db, dependency)
    with pytest.raises(RuntimeError, match="test failure"):
        with _manual_db_session():
            raise RuntimeError("test failure")
    assert finalized


def test_catalog_endpoints(client):
    from app.models import Category, Product, Store, StoreProduct

    with _manual_db_session() as session:
        store = Store(name="Tienda de prueba", base_url="https://example.test", country="Argentina")
        category = Category(name="Tecnología", slug="tecnologia")
        session.add_all([store, category])
        session.flush()
        product = Product(name="Equipo de prueba", category_id=category.id)
        session.add(product)
        session.flush()
        session.add(StoreProduct(
            store_id=store.id,
            product_id=product.id,
            product_url="https://example.test/item",
            product_name="Equipo de prueba",
        ))
        session.commit()

    assert client.get("/api/v1/stores").json()[0]["name"] == "Tienda de prueba"
    assert client.get("/api/v1/categories").json()[0]["slug"] == "tecnologia"
    products = client.get("/api/v1/products").json()
    assert isinstance(products, list)
    assert len(products) == 1
    expected_fields = {
        "id", "name", "brand", "model", "description", "barcode", "category_id",
        "package_quantity", "package_unit", "package_count", "normalized_quantity",
        "normalized_unit", "normalization_unavailable_reason",
    }
    for product_payload in products:
        assert set(product_payload) == expected_fields
        assert type(product_payload["id"]) is int
        assert isinstance(product_payload["name"], str)
        for field in ("brand", "model", "description", "barcode"):
            assert product_payload[field] is None or isinstance(product_payload[field], str)
        assert product_payload["category_id"] is None or type(product_payload["category_id"]) is int
    assert products[0]["name"] == "Equipo de prueba"
    assert products[0]["package_quantity"] is None
    assert products[0]["normalization_unavailable_reason"] == "missing_package_quantity"


def test_products_paginated_defaults_and_total(client):
    from app.models import Category, Product

    with _manual_db_session() as session:
        category = Category(name="Hogar", slug="hogar")
        session.add(category)
        session.flush()
        session.add_all([Product(name=name, category_id=category.id) for name in ("C", "A", "B")])
        session.commit()

    response = client.get("/api/v1/products/paginated")
    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload["items"]] == ["A", "B", "C"]
    assert payload["total"] == 3
    assert payload["limit"] == 20
    assert payload["offset"] == 0


def test_products_paginated_limit_offset_and_category_filter(client):
    from app.models import Category, Product

    with _manual_db_session() as session:
        first = Category(name="Hogar", slug="hogar")
        second = Category(name="Tecnología", slug="tecnologia")
        session.add_all([first, second])
        session.flush()
        session.add_all([
            Product(name="A", category_id=first.id),
            Product(name="B", category_id=first.id),
            Product(name="C", category_id=first.id),
            Product(name="Otro", category_id=second.id),
        ])
        session.commit()
        category_id = first.id

    response = client.get(
        "/api/v1/products/paginated",
        params={"category_id": category_id, "limit": 1, "offset": 1},
    )
    assert response.status_code == 200
    payload = response.json()
    assert [item["name"] for item in payload["items"]] == ["B"]
    assert payload["total"] == 3
    assert payload["limit"] == 1
    assert payload["offset"] == 1


def test_products_paginated_search_applies_before_offset_and_total(client):
    from app.models import Product

    with _manual_db_session() as session:
        session.add_all([
            Product(name="DEMO Café molido"),
            Product(name="DEMO Café en grano"),
            Product(name="DEMO Té negro"),
        ])
        session.commit()

    response = client.get("/api/v1/products/paginated", params={"search": "café", "limit": 1, "offset": 1})
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 2
    assert payload["items"][0]["name"] == "DEMO Café molido"


def test_priced_product_search_and_date_range_select_matching_observation(client):
    from app.models import Category, PriceObservation, Product, Store, StoreProduct

    with _manual_db_session() as session:
        category = Category(name="DEMO Café", slug="demo-cafe")
        store = Store(name="DEMO Shop", base_url="https://shop.demo.invalid")
        session.add_all([category, store])
        session.flush()
        in_range = Product(name="DEMO Café molido", category_id=category.id)
        out_of_range = Product(name="DEMO Café viejo", category_id=category.id)
        session.add_all([in_range, out_of_range])
        session.flush()
        listings = [
            StoreProduct(store_id=store.id, product_id=product.id, category_id=category.id,
                         product_url=f"https://shop.demo.invalid/{index}", product_name=product.name)
            for index, product in enumerate((in_range, out_of_range), start=1)
        ]
        session.add_all(listings)
        session.flush()
        session.add_all([
            PriceObservation(store_product_id=listings[0].id, amount="101.00", currency="ARS",
                             observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            PriceObservation(store_product_id=listings[1].id, amount="90.00", currency="ARS",
                             observed_at=datetime(2025, 12, 31, tzinfo=timezone.utc)),
        ])
        session.commit()

    response = client.get("/api/v1/products/paginated-with-prices", params={
        "search": "café", "category_id": category.id,
        "start": "2026-01-01T00:00:00Z", "end": "2026-01-03T00:00:00Z",
    })
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "DEMO Café molido"
    assert payload["items"][0]["latest_price"]["amount"] == "101.00"


def test_price_observations_can_search_canonical_or_listing_name(client):
    from app.models import Category, PriceObservation, Product, Store, StoreProduct

    with _manual_db_session() as session:
        category = Category(name="DEMO Cocina", slug="demo-cocina")
        store = Store(name="DEMO Shop", base_url="https://shop.demo.invalid")
        session.add_all([category, store])
        session.flush()
        product = Product(name="DEMO Producto canónico", category_id=category.id)
        session.add(product)
        session.flush()
        listing = StoreProduct(store_id=store.id, product_id=product.id, category_id=category.id,
                               product_url="https://shop.demo.invalid/item", product_name="DEMO Café paquete")
        session.add(listing)
        session.flush()
        session.add(PriceObservation(store_product_id=listing.id, amount="25.00", currency="ARS",
                                     observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)))
        session.commit()
        store_id, category_id = store.id, category.id

    response = client.get("/api/v1/price-observations", params={
        "store_id": store_id, "category_id": category_id, "search": "café",
    })
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_products_with_latest_prices_keeps_products_without_observations(client):
    from app.models import PriceObservation, Product, Store, StoreProduct

    with _manual_db_session() as session:
        store = Store(name="Tienda real fixture", base_url="https://shop.test")
        priced = Product(name="Producto con observación")
        empty = Product(name="Producto sin observación")
        session.add_all([store, priced, empty])
        session.flush()
        listing = StoreProduct(
            store_id=store.id,
            product_id=priced.id,
            product_url="https://shop.test/item",
            product_name=priced.name,
        )
        session.add(listing)
        session.flush()
        session.add_all([
            PriceObservation(
                store_product_id=listing.id,
                amount="999999.00",
                currency="ARS",
                source_url=listing.product_url,
                observed_at=datetime(2026, 10, 10, 20, tzinfo=timezone.utc),
            ),
            PriceObservation(
                store_product_id=listing.id,
                amount="1086665.88",
                currency="ARS",
                source_url=listing.product_url,
                observed_at=datetime(2026, 11, 10, 20, tzinfo=timezone.utc),
            ),
        ])
        session.commit()

    response = client.get("/api/v1/products/paginated-with-prices", params={"limit": 10})
    assert response.status_code == 200
    payload = response.json()
    by_name = {item["name"]: item for item in payload["items"]}
    assert by_name["Producto con observación"]["latest_price"]["amount"] == "1086665.88"
    assert by_name["Producto con observación"]["latest_price"]["currency"] == "ARS"
    assert by_name["Producto con observación"]["latest_price"]["store_name"] == "Tienda real fixture"
    assert by_name["Producto sin observación"]["latest_price"] is None


def test_product_by_id_returns_product_and_404_for_missing(client):
    from app.models import Product

    with _manual_db_session() as session:
        product = Product(name="Producto")
        session.add(product)
        session.commit()
        product_id = product.id

    found = client.get(f"/api/v1/products/{product_id}")
    assert found.status_code == 200
    assert found.json()["name"] == "Producto"
    assert client.get("/api/v1/products/999").status_code == 404


def test_product_routes_validate_pagination_and_positive_id(client):
    assert client.get("/api/v1/products/paginated", params={"limit": 101}).status_code == 422
    assert client.get("/api/v1/products/paginated", params={"offset": -1}).status_code == 422
    assert client.get("/api/v1/products/paginated", params={"category_id": 0}).status_code == 422
    assert client.get("/api/v1/products/paginated", params={"category_id": -1}).status_code == 422
    assert client.get("/api/v1/products/0").status_code == 422


def test_price_observation_preserves_history_and_rejects_duplicate(client):
    from app.models import Store, StoreProduct

    with _manual_db_session() as session:
        store = Store(name="Tienda", base_url="https://example.test")
        session.add(store)
        session.flush()
        item = StoreProduct(store_id=store.id, product_url="https://example.test/p", product_name="Producto")
        session.add(item)
        session.commit()
        item_id = item.id

    for day, amount in (("2026-01-01T10:00:00-03:00", "100.00"), ("2026-01-02T10:00:00-03:00", "110.00")):
        response = client.post("/api/v1/price-observations", json={"store_product_id": item_id, "amount": amount, "observed_at": day})
        assert response.status_code == 201
    duplicate = client.post("/api/v1/price-observations", json={"store_product_id": item_id, "amount": "120.00", "observed_at": "2026-01-01T10:00:00-03:00"})
    assert duplicate.status_code == 409
    history = client.get("/api/v1/price-observations", params={"store_product_id": item_id})
    assert len(history.json()) == 2
    assert history.json()[0]["amount"] == "110.00"


def test_exchange_rates_can_be_filtered_by_type_and_date(client, monkeypatch):
    from app.models import ExchangeRate

    monkeypatch.setattr("app.api.v1.router.MonedApiProvider.fetch", lambda _self: ())
    with _manual_db_session() as session:
        session.add_all([
            ExchangeRate(source="BCRA", rate_type="official", rate="1000.000000", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
            ExchangeRate(source="BCRA", rate_type="official", rate="1100.000000", observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
            ExchangeRate(source="Ámbito", rate_type="blue", rate="1200.000000", observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        ])
        session.commit()

    response = client.get("/api/v1/exchange-rates", params={"rate_type": "official", "on_date": "2026-01-01T23:00:00Z"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["rate"] == "1000.000000"

    blue = client.get("/api/v1/exchange-rates", params={"rate_type": "blue"})
    assert blue.status_code == 200
    assert [item["rate_type"] for item in blue.json()] == ["blue"]


def test_exchange_rates_require_a_nonblank_type(client):
    assert client.get("/api/v1/exchange-rates").status_code == 422
    assert client.get("/api/v1/exchange-rates", params={"rate_type": ""}).status_code == 422


def test_price_requires_timezone(client):
    response = client.post("/api/v1/price-observations", json={"store_product_id": 1, "amount": "1", "observed_at": "2026-01-01T12:00:00"})
    assert response.status_code == 422


def test_catalog_exposes_original_and_normalized_package_prices(client):
    from decimal import Decimal
    from app.models import PriceObservation, Product, Store, StoreProduct

    with _manual_db_session() as session:
        store = Store(name="Pack shop", base_url="https://pack.test")
        product = Product(
            name="Pack beverage", package_quantity=Decimal("500"),
            package_unit="ml", package_count=6,
        )
        session.add_all([store, product])
        session.flush()
        listing = StoreProduct(
            store_id=store.id, product_id=product.id,
            product_url="https://pack.test/item", product_name=product.name,
            currency="ARS",
        )
        session.add(listing)
        session.flush()
        session.add(PriceObservation(
            store_product_id=listing.id, amount=Decimal("1500.00"),
            promotional_price=Decimal("1200.00"), currency="ARS",
            source_url=listing.product_url,
            observed_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
        ))
        session.commit()
        listing_id = listing.id

    response = client.get("/api/v1/products/paginated-with-prices")
    assert response.status_code == 200
    product_payload = response.json()["items"][0]
    assert product_payload["package_quantity"] == "500.000000"
    assert product_payload["package_unit"] == "ml"
    assert product_payload["package_count"] == 6
    assert product_payload["normalized_quantity"] == "3000.000000"
    assert product_payload["normalized_unit"] == "ml"
    price_payload = product_payload["latest_price"]
    assert price_payload["amount"] == "1500.00"
    assert price_payload["promotional_price"] == "1200.00"
    assert price_payload["currency"] == "ARS"
    assert price_payload["normalized_price"] == "0.5"
    assert price_payload["normalized_promotional_price"] == "0.4"
    assert price_payload["normalized_unit"] == "ml"
    assert price_payload["normalization_unavailable_reason"] is None

    listing_payload = client.get("/api/v1/store-products").json()[0]
    assert listing_payload["id"] == listing_id
    assert listing_payload["normalized_quantity"] == "3000.000000"


def test_catalog_does_not_normalize_unknown_product_units(client):
    from app.models import PriceObservation, Product, Store, StoreProduct

    with _manual_db_session() as session:
        store = Store(name="Unit shop", base_url="https://unit.test")
        product = Product(
            name="Unknown unit product", package_quantity="500",
            package_unit="oz", package_count=1,
        )
        session.add_all([store, product])
        session.flush()
        listing = StoreProduct(
            store_id=store.id, product_id=product.id,
            product_url="https://unit.test/item", product_name=product.name,
        )
        session.add(listing)
        session.flush()
        session.add(PriceObservation(
            store_product_id=listing.id, amount="10.00", currency="ARS",
            observed_at=datetime(2026, 11, 10, tzinfo=timezone.utc),
        ))
        session.commit()

    payload = client.get("/api/v1/products/paginated-with-prices").json()["items"][0]
    assert payload["normalized_quantity"] is None
    assert payload["normalization_unavailable_reason"] == "unsupported_package_unit"
    assert payload["latest_price"]["normalized_price"] is None
    assert payload["latest_price"]["normalization_unavailable_reason"] == "unsupported_package_unit"
