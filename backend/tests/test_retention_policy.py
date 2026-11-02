from datetime import datetime, timezone

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from app.models import PriceObservation, Product, Store, StoreProduct


def create_price_history(session):
    store = Store(name="Comercio", base_url="https://example.test")
    product = Product(name="Producto canónico")
    session.add_all([store, product])
    session.flush()
    listing = StoreProduct(
        store_id=store.id,
        product_id=product.id,
        external_id="sku-1",
        product_url="https://example.test/producto",
        product_name="Producto publicado",
    )
    session.add(listing)
    session.flush()
    observation = PriceObservation(
        store_product_id=listing.id,
        amount="1250.50",
        currency="ARS",
        observed_at=datetime(2026, 10, 1, tzinfo=timezone.utc),
    )
    session.add(observation)
    session.commit()
    return store.id, product.id, listing.id


def observation_count(session):
    return session.scalar(select(func.count()).select_from(PriceObservation))


def test_store_is_soft_deactivated_and_hard_delete_is_restricted(client):
    from app.db.session import get_db
    from app.main import app

    session = next(app.dependency_overrides[get_db]())
    store_id, _, _ = create_price_history(session)
    store = session.get(Store, store_id)
    assert store.products  # Exercise the loaded-collection ORM delete path.

    session.delete(store)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()

    store = session.get(Store, store_id)
    store.deactivate()
    session.commit()
    assert session.get(Store, store_id).is_active is False
    assert observation_count(session) == 1
    session.close()


def test_store_product_and_canonical_product_deletes_preserve_history(client):
    from app.db.session import get_db
    from app.main import app

    session = next(app.dependency_overrides[get_db]())
    _, product_id, listing_id = create_price_history(session)

    listing = session.get(StoreProduct, listing_id)
    assert listing.observations  # Exercise the loaded-collection ORM delete path.
    session.delete(listing)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    assert observation_count(session) == 1

    product = session.get(Product, product_id)
    assert product.store_products
    session.delete(product)
    with pytest.raises(IntegrityError):
        session.commit()
    session.rollback()
    assert session.get(Product, product_id) is not None
    assert observation_count(session) == 1
    session.close()


def test_price_observation_cannot_be_deleted_through_orm(client):
    from app.db.session import get_db
    from app.main import app

    session = next(app.dependency_overrides[get_db]())
    create_price_history(session)
    observation = session.scalar(select(PriceObservation))
    session.delete(observation)
    with pytest.raises(InvalidRequestError, match="approved retention procedure"):
        session.flush()
    session.rollback()
    assert observation_count(session) == 1
    session.close()
