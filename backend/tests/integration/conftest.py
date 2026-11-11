import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session


MARKET_TABLES = {
    "alembic_version",
    "stores",
    "categories",
    "products",
    "store_products",
    "price_observations",
    "exchange_rates",
    "extraction_runs",
}
EXPECTED_TABLES = MARKET_TABLES | {
    "store_integrations",
    "store_monitoring_preferences",
    "store_monitoring_categories",
}
CURRENT_HEAD = "a6f20488d7b1"


def _validated_test_url():
    raw_url = os.environ.get("PRICESCOPE_TEST_DATABASE_URL")
    if not raw_url:
        pytest.skip("Set PRICESCOPE_TEST_DATABASE_URL to run PostgreSQL integration tests")

    url = make_url(raw_url)
    if url.get_backend_name() != "postgresql":
        pytest.fail("Integration tests require PostgreSQL")
    if url.host not in {"localhost", "127.0.0.1", "::1"}:
        pytest.fail("Refusing integration target outside local loopback")
    if url.database != "pricescope_test":
        pytest.fail("Refusing integration target other than pricescope_test")
    return url.set(drivername="postgresql+psycopg")


@pytest.fixture(scope="session")
def postgres_engine():
    url = _validated_test_url()
    engine = create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 5})

    try:
        with engine.connect() as connection:
            if connection.execute(text("select current_database()")).scalar_one() != "pricescope_test":
                pytest.fail("Connected database does not match the isolated test target")
            tables = set(inspect(connection).get_table_names())
            versions = []
            if "alembic_version" in tables:
                versions = list(connection.execute(text("select version_num from alembic_version")).scalars())

        allowed_states = (
            not tables
            or (tables == {"alembic_version", "stores"} and versions == ["cb0deba93496"])
            or (tables == MARKET_TABLES and versions == ["4db267e3b121"])
            or (tables == MARKET_TABLES and versions == ["d8f31a9c0e42"])
            or (tables == EXPECTED_TABLES and versions == [CURRENT_HEAD])
        )
        if not allowed_states:
            pytest.fail("Test database contains an unexpected schema; refusing to migrate it")

        env = os.environ.copy()
        env["DATABASE_URL"] = url.render_as_string(hide_password=False)
        env["PRICESCOPE_TEST_DATABASE_URL"] = url.render_as_string(hide_password=False)
        backend_dir = Path(__file__).resolve().parents[2]
        migration = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        if migration.returncode:
            pytest.fail("Alembic migration failed against the validated local test database")

        check = subprocess.run(
            [sys.executable, "-m", "alembic", "-c", "alembic.ini", "check"],
            cwd=backend_dir,
            env=env,
            capture_output=True,
            text=True,
        )
        if check.returncode:
            pytest.fail("Alembic metadata check found differences between models and PostgreSQL")

        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def postgres_session(postgres_engine):
    connection = postgres_engine.connect()
    outer_transaction = connection.begin()
    session = Session(connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        outer_transaction.rollback()
        connection.close()
