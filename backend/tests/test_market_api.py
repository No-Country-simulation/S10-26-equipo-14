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
    expected_fields = {"id", "name", "brand", "model", "description", "barcode", "category_id"}
    for product_payload in products:
        assert set(product_payload) == expected_fields
        assert type(product_payload["id"]) is int
        assert isinstance(product_payload["name"], str)
        for field in ("brand", "model", "description", "barcode"):
            assert product_payload[field] is None or isinstance(product_payload[field], str)
        assert product_payload["category_id"] is None or type(product_payload["category_id"]) is int
    assert products[0]["name"] == "Equipo de prueba"


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


def test_exchange_rates_can_be_filtered_by_type_and_date(client):
    from app.models import ExchangeRate

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


def test_price_requires_timezone(client):
    response = client.post("/api/v1/price-observations", json={"store_product_id": 1, "amount": "1", "observed_at": "2026-01-01T12:00:00"})
    assert response.status_code == 422
