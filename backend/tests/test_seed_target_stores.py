from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.commands.seed_target_stores import TARGET_STORE_NAMES, populate
from app.db.base import Base
import app.models  # noqa: F401 - register all mapped tables
from app.models import Store, StoreIntegration


def _engine():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    return engine


def test_target_store_seed_first_execution_registers_all_stores():
    engine = _engine()
    try:
        with Session(engine) as session, session.begin():
            assert populate(session) == {"stores": 15, "integrations": 15}

        with Session(engine) as session:
            stores = session.scalars(select(Store).order_by(Store.id)).all()
            integrations = session.scalars(select(StoreIntegration)).all()
            assert [store.name for store in stores] == list(TARGET_STORE_NAMES)
            assert all(store.base_url == "" for store in stores)
            assert all(store.country == "AR" and store.is_active for store in stores)
            assert len(integrations) == 15
            assert {item.status for item in integrations} == {"configuration_required"}
            assert all(item.analyzer_key is None for item in integrations)
            assert all("no se configur\u00f3 ni verific\u00f3" in item.analysis_message for item in integrations)
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_target_store_seed_second_execution_is_idempotent():
    engine = _engine()
    try:
        with Session(engine) as session, session.begin():
            assert populate(session) == {"stores": 15, "integrations": 15}
        with Session(engine) as session, session.begin():
            assert populate(session) == {"stores": 0, "integrations": 0}
            assert session.scalar(select(func.count()).select_from(Store)) == 15
            assert session.scalar(select(func.count()).select_from(StoreIntegration)) == 15
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_target_store_seed_preserves_existing_store_and_integration():
    engine = _engine()
    try:
        with Session(engine) as session, session.begin():
            store = Store(name="Carrefour", base_url="https://local.example.test", country="AR", is_active=False)
            session.add(store)
            session.flush()
            session.add(StoreIntegration(
                store_id=store.id,
                status="active",
                analyzer_key="existing-analyzer",
                analysis_message="Existing operator configuration",
                analysis_candidates=[{"preserved": True}],
            ))
        with Session(engine) as session, session.begin():
            counts = populate(session)
            assert counts == {"stores": 14, "integrations": 14}
        with Session(engine) as session:
            store = session.scalar(select(Store).where(Store.name == "Carrefour"))
            integration = session.scalar(
                select(StoreIntegration).where(StoreIntegration.store_id == store.id)
            )
            assert store.base_url == "https://local.example.test"
            assert store.is_active is False
            assert integration.status == "active"
            assert integration.analyzer_key == "existing-analyzer"
            assert integration.analysis_message == "Existing operator configuration"
            assert integration.analysis_candidates == [{"preserved": True}]
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


def test_target_store_seed_recognizes_existing_credicoop_name():
    engine = _engine()
    try:
        with Session(engine) as session, session.begin():
            original = Store(
                name="Tienda Credicoop ficha real",
                base_url="https://existing.example.test",
                country="AR",
            )
            session.add(original)
            session.flush()
            original_id = original.id
        with Session(engine) as session, session.begin():
            assert populate(session) == {"stores": 14, "integrations": 15}
        with Session(engine) as session:
            assert session.scalar(select(func.count()).select_from(Store)) == 15
            preserved = session.get(Store, original_id)
            assert preserved.name == "Tienda Credicoop ficha real"
            assert preserved.base_url == "https://existing.example.test"
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
