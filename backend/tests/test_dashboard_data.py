from datetime import datetime, timezone

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.db.base import Base
from app.db.session import get_db
from app.main import create_app
from app.models import PriceObservation, Product, Store, StoreProduct


def test_public_product_history_is_filterable_and_excludes_demo_listings():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    app = create_app(cors_origins=[], app_settings=Settings(
        _env_file=None, database_url="sqlite://", app_env="production", public_read_only=True,
    ))

    def override_db():
        with factory() as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        with factory() as session:
            real_store = Store(name="Comercio real", base_url="https://shop.test", country="AR")
            demo_store = Store(name="DEMO PriceScope Store", base_url="https://demo.invalid", country="AR")
            real_product = Product(name="Producto real")
            demo_product = Product(name="DEMO PriceScope Product")
            session.add_all([real_store, demo_store, real_product, demo_product])
            session.flush()
            real_listing = StoreProduct(store_id=real_store.id, product_id=real_product.id,
                product_url="https://shop.test/real", product_name="Producto real")
            demo_listing = StoreProduct(store_id=demo_store.id, product_id=demo_product.id,
                product_url="https://demo.invalid/item", product_name="DEMO PriceScope Product")
            session.add_all([real_listing, demo_listing])
            session.flush()
            timestamp = datetime(2026, 11, 12, tzinfo=timezone.utc)
            session.add_all([
                PriceObservation(store_product_id=real_listing.id, amount=100, currency="ARS", observed_at=timestamp),
                PriceObservation(store_product_id=demo_listing.id, amount=999, currency="ARS", observed_at=timestamp),
            ])
            session.commit()
            product_id = real_product.id

        with TestClient(app) as client:
            response = client.get("/api/v1/price-observations", params={"product_id": product_id})
        assert response.status_code == 200
        assert len(response.json()) == 1
        assert response.json()[0]["amount"] == "100.00"
    finally:
        app.dependency_overrides.clear()
        Base.metadata.drop_all(engine)
        engine.dispose()
