from datetime import datetime, timezone
from decimal import Decimal

def test_frontend_contract_fields_and_decimal_json_are_explicit(client):
    from app.db.session import get_db
    from app.main import app
    from app.models import Category, ExchangeRate, Product, Store, StoreProduct

    session = next(app.dependency_overrides[get_db]())
    category = Category(name="Hogar", slug="hogar")
    store = Store(name="Comercio de prueba", base_url="https://example.test")
    session.add_all([category, store])
    session.flush()
    product = Product(name="Producto canónico", barcode="00012345678905", category_id=category.id)
    session.add(product)
    session.flush()
    listing = StoreProduct(
        store_id=store.id,
        product_id=product.id,
        category_id=category.id,
        external_id=None,
        product_url="https://example.test/item",
        product_name="Nombre publicado",
    )
    session.add(listing)
    session.add_all([
        ExchangeRate(
            source="Proveedor de prueba", rate_type="blue", rate_side=side,
            base_currency="USD", quote_currency="ARS", rate=Decimal(value),
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )
        for side, value in (("buy", "1400.123456"), ("sell", "1450.654321"))
    ])
    session.commit()
    session.close()

    store_response = client.get("/api/v1/stores")
    assert store_response.status_code == 200
    assert store_response.json()[0]["created_at"]

    product_payload = client.get("/api/v1/products").json()[0]
    assert product_payload["barcode"] == "00012345678905"
    assert product_payload["description"] is None

    listing_payload = client.get("/api/v1/store-products").json()[0]
    assert listing_payload["product_id"] == product_payload["id"]
    assert listing_payload["category_id"] is not None
    assert "store_id" in listing_payload

    rates = client.get("/api/v1/exchange-rates", params={"rate_type": "blue"}).json()
    assert {rate["rate_side"] for rate in rates} == {"buy", "sell"}
    assert all(isinstance(rate["rate"], str) for rate in rates)


def test_price_observation_contract_preserves_decimal_and_source_fields(client):
    from app.db.session import get_db
    from app.main import app
    from app.models import Store, StoreProduct

    session = next(app.dependency_overrides[get_db]())
    store = Store(name="Comercio", base_url="https://example.test")
    session.add(store)
    session.flush()
    listing = StoreProduct(
        store_id=store.id,
        product_url="https://example.test/item",
        product_name="Artículo",
    )
    session.add(listing)
    session.commit()
    listing_id = listing.id
    session.close()

    response = client.post("/api/v1/price-observations", json={
        "store_product_id": listing_id,
        "amount": "1234567890.12",
        "promotional_price": "1199999999.99",
        "currency": "ARS",
        "source_url": "https://example.test/item",
        "is_available": False,
        "observed_at": "2026-11-01T10:00:00-03:00",
    })
    assert response.status_code == 201
    body = response.json()
    assert body["amount"] == "1234567890.12"
    assert body["promotional_price"] == "1199999999.99"
    assert body["source_url"] == "https://example.test/item"
    assert body["is_available"] is False
    assert body["store_product_id"] == listing_id
