from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.commands.seed_demo import populate
from app.db.base import Base
import app.models  # noqa: F401 - register all mapped tables
from app.models import Category, ExchangeRate, ExtractionRun, PriceObservation, Product, Store, StoreProduct


def test_demo_fixture_is_synthetic_complete_and_idempotent():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        with Session(engine) as session:
            first = populate(session)
            session.commit()
            second = populate(session)
            session.commit()

            assert first == {
                "categories": 3,
                "stores": 2,
                "products": 21,
                "listings": 42,
                "observations": 126,
                "rates": 3,
            }
            assert all(value == 0 for value in second.values())
            assert session.scalar(select(func.count()).select_from(ExtractionRun)) == 0
            assert session.scalar(select(func.count()).select_from(Category)) == 3
            assert session.scalar(select(func.count()).select_from(Store)) == 2
            assert session.scalar(select(func.count()).select_from(Product)) == 21
            assert session.scalar(select(func.count()).select_from(StoreProduct)) == 42
            assert session.scalar(select(func.count()).select_from(PriceObservation)) == 126
            assert session.scalar(select(func.count()).select_from(ExchangeRate)) == 3
            assert all(url.endswith(".invalid") for (url,) in session.query(Store.base_url).all())
            assert all(".invalid/" in url for (url,) in session.query(PriceObservation.source_url).all())
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
