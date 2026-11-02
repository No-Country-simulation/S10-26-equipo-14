from datetime import datetime, timezone


def test_catalog_endpoints(client):
    from app.db.session import get_db
    from app.main import app

    session = next(app.dependency_overrides[get_db]())
    from app.models import Category, Product, Store, StoreProduct
    store = Store(name="Tienda de prueba", base_url="https://example.test", country="Argentina")
    category = Category(name="Tecnología", slug="tecnologia")
    session.add_all([store, category])
    session.flush()
    product = Product(name="Equipo de prueba", category_id=category.id)
    session.add(product)
    session.flush()
    session.add(StoreProduct(store_id=store.id, product_id=product.id, product_url="https://example.test/item", product_name="Equipo de prueba"))
    session.commit()
    session.close()

    assert client.get("/api/v1/stores").json()[0]["name"] == "Tienda de prueba"
    assert client.get("/api/v1/categories").json()[0]["slug"] == "tecnologia"
    assert client.get("/api/v1/products").json()[0]["name"] == "Equipo de prueba"


def test_price_observation_preserves_history_and_rejects_duplicate(client):
    from app.db.session import get_db
    from app.main import app
    from app.models import Store, StoreProduct
    session = next(app.dependency_overrides[get_db]())
    store = Store(name="Tienda", base_url="https://example.test")
    session.add(store)
    session.flush()
    item = StoreProduct(store_id=store.id, product_url="https://example.test/p", product_name="Producto")
    session.add(item)
    session.commit()
    item_id = item.id
    session.close()

    for day, amount in (("2026-01-01T10:00:00-03:00", "100.00"), ("2026-01-02T10:00:00-03:00", "110.00")):
        response = client.post("/api/v1/price-observations", json={"store_product_id": item_id, "amount": amount, "observed_at": day})
        assert response.status_code == 201
    duplicate = client.post("/api/v1/price-observations", json={"store_product_id": item_id, "amount": "120.00", "observed_at": "2026-01-01T10:00:00-03:00"})
    assert duplicate.status_code == 409
    history = client.get("/api/v1/price-observations", params={"store_product_id": item_id})
    assert len(history.json()) == 2
    assert history.json()[0]["amount"] == "110.00"


def test_exchange_rates_can_be_filtered_by_type_and_date(client):
    from app.db.session import get_db
    from app.main import app
    from app.models import ExchangeRate
    session = next(app.dependency_overrides[get_db]())
    session.add_all([
        ExchangeRate(source="BCRA", rate_type="official", rate="1000.000000", observed_at=datetime(2026, 1, 1, tzinfo=timezone.utc)),
        ExchangeRate(source="BCRA", rate_type="official", rate="1100.000000", observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
        ExchangeRate(source="Ámbito", rate_type="blue", rate="1200.000000", observed_at=datetime(2026, 1, 2, tzinfo=timezone.utc)),
    ])
    session.commit()
    session.close()

    response = client.get("/api/v1/exchange-rates", params={"rate_type": "official", "on_date": "2026-01-01T23:00:00Z"})
    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["rate"] == "1000.000000"


def test_price_requires_timezone(client):
    response = client.post("/api/v1/price-observations", json={"store_product_id": 1, "amount": "1", "observed_at": "2026-01-01T12:00:00"})
    assert response.status_code == 422
