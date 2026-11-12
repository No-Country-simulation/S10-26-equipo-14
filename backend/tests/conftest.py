import os

# Unit tests must never inherit the application's Neon DATABASE_URL.
os.environ["DATABASE_URL"] = "sqlite://"

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.core.config import Settings
from app.main import app
from app.models import Category, ExchangeRate, ExtractionRun, PriceObservation, Product, Store, StoreProduct


@pytest.fixture
def client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_sqlite_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    def override_db():
        with session_factory() as session:
            yield session

    previous_settings = app.state.settings
    app.state.settings = Settings(
        _env_file=None,
        database_url="sqlite://",
        app_env="development",
    )
    app.dependency_overrides[get_db] = override_db
    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        app.state.settings = previous_settings
        Base.metadata.drop_all(engine)
        engine.dispose()
