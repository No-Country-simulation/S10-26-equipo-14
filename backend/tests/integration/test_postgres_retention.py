from datetime import datetime, timezone

import pytest
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from app.models import PriceObservation, Product, Store, StoreProduct

pytestmark = pytest.mark.integration


def add_price_history(session):
    store = Store(name="Local PostgreSQL test store", base_url="https://local-test.invalid")
    product = Product(name="Local PostgreSQL test product")
    session.add_all([store, product])
    session.flush()
    listing = StoreProduct(
        store_id=store.id,
        product_id=product.id,
        external_id="test-source-id",
        product_url="https://local-test.invalid/product",
        product_name="Local PostgreSQL test product listing",
    )
    session.add(listing)
    session.flush()
    observation = PriceObservation(
        store_product_id=listing.id,
        amount="10.25",
        observed_at=datetime(2026, 11, 2, tzinfo=timezone.utc),
    )
    session.add(observation)
    session.commit()
    return store.id, product.id, listing.id, observation.id


def test_postgres_schema_contains_all_tables_and_restrict_fks(postgres_engine):
    inspector = inspect(postgres_engine)
    assert {
        "alembic_version",
        "stores",
        "categories",
        "products",
        "store_products",
        "price_observations",
        "exchange_rates",
        "extraction_runs",
    } <= set(inspector.get_table_names())

    expected = {
        ("store_products", "store_id"): "RESTRICT",
        ("store_products", "product_id"): "RESTRICT",
        ("price_observations", "store_product_id"): "RESTRICT",
    }
    for (table, column), ondelete in expected.items():
        fk = next(fk for fk in inspector.get_foreign_keys(table) if fk["constrained_columns"] == [column])
        assert fk["options"]["ondelete"].upper() == ondelete


def test_postgres_restrict_and_soft_deactivation_preserve_observations(postgres_session):
    store_id, product_id, listing_id, observation_id = add_price_history(postgres_session)

    store = postgres_session.get(Store, store_id)
    assert store.products
    original = (store.name, store.base_url, store.country, store.created_at)
    store.deactivate()
    postgres_session.flush()
    assert store.is_active is False
    assert (store.name, store.base_url, store.country, store.created_at) == original
    assert postgres_session.get(PriceObservation, observation_id) is not None

    postgres_session.delete(store)
    with pytest.raises(IntegrityError):
        postgres_session.flush()
    postgres_session.rollback()
    assert postgres_session.get(PriceObservation, observation_id) is not None

    listing = postgres_session.get(StoreProduct, listing_id)
    assert listing.observations
    postgres_session.delete(listing)
    with pytest.raises(IntegrityError):
        postgres_session.flush()
    postgres_session.rollback()
    assert postgres_session.get(PriceObservation, observation_id) is not None

    product = postgres_session.get(Product, product_id)
    assert product.store_products
    postgres_session.delete(product)
    with pytest.raises(IntegrityError):
        postgres_session.flush()
    postgres_session.rollback()
    assert postgres_session.get(PriceObservation, observation_id) is not None


def test_postgres_orm_blocks_direct_observation_delete(postgres_session):
    _, _, _, observation_id = add_price_history(postgres_session)
    observation = postgres_session.get(PriceObservation, observation_id)
    postgres_session.delete(observation)
    with pytest.raises(InvalidRequestError, match="approved retention procedure"):
        postgres_session.flush()
    postgres_session.rollback()
    assert postgres_session.scalar(select(PriceObservation.id)) == observation_id
