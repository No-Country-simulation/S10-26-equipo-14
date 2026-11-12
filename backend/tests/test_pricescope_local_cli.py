from decimal import Decimal
import os
import subprocess
import sys

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from sqlalchemy.engine import URL

from app.commands import pricescope_local as cli
from app.extractors.fravega import FravegaExtractor
from app.models import ExtractionRun, PriceObservation, Product, Store, StoreProduct


SYNTHETIC_URL = "https://www.fravega.com/p/fixture-only-not-a-real-listing/"
SYNTHETIC_HTML = '''<html><script type="application/ld+json">
{"@type":"Product","name":"Fixture de prueba (no producto real)","offers":{"@type":"Offer","price":"123.45","priceCurrency":"ARS","availability":"https://schema.org/InStock"}}
</script></html>'''


def test_db_init_runs_migrations_and_verifies_local_schema(tmp_path):
    db_path = tmp_path / "catalog.sqlite3"

    result = cli.main(["--db", str(db_path), "db", "init"])

    assert result == 0
    tables, revision = cli._read_sqlite_state(db_path)
    assert tables == cli.EXPECTED_TABLES
    assert revision == cli.ALEMBIC_HEAD
    environment = {**os.environ, "DATABASE_URL": URL.create("sqlite", database=str(db_path)).render_as_string()}
    check = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "check"],
        cwd=cli.BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_package_measurement_migration_downgrades_on_temporary_sqlite(tmp_path):
    db_path = cli.init_db(tmp_path / "downgrade.sqlite3")
    environment = {
        **os.environ,
        "DATABASE_URL": URL.create("sqlite", database=str(db_path)).render_as_string(),
    }
    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "downgrade", "a6f20488d7b1"],
        cwd=cli.BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr

    import sqlite3

    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("INSERT INTO stores (name, base_url) VALUES (?, ?)", ("Historical store", "https://example.test"))
        connection.execute("INSERT INTO products (name, barcode) VALUES (?, ?)", ("Historical product", "0123456789012"))
        connection.execute(
            "INSERT INTO store_products (store_id, product_id, product_url, product_name, currency) VALUES (1, 1, ?, ?, 'ARS')",
            ("https://example.test/item", "Historical listing"),
        )
        connection.execute(
            "INSERT INTO price_observations (store_product_id, amount, currency, observed_at) VALUES (1, 123.45, 'ARS', '2026-01-01 00:00:00')"
        )
        connection.commit()

    upgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=cli.BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert upgrade.returncode == 0, upgrade.stdout + upgrade.stderr
    with sqlite3.connect(db_path) as connection:
        assert connection.execute("SELECT count(*) FROM stores").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM store_products").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM price_observations").fetchone() == (1,)
        assert connection.execute(
            "SELECT package_quantity, package_unit, package_count FROM products WHERE id=1"
        ).fetchone() == (None, None, None)
        connection.execute(
            "UPDATE products SET package_quantity=500, package_unit='ml', package_count=6 WHERE id=1"
        )
        connection.commit()

    downgrade = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "downgrade", "a6f20488d7b1"],
        cwd=cli.BACKEND_DIR,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert downgrade.returncode == 0, downgrade.stdout + downgrade.stderr
    with sqlite3.connect(db_path) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(products)")}
        assert not {"package_quantity", "package_unit", "package_count"} & columns
        assert connection.execute("SELECT name FROM products").fetchone() == ("Historical product",)
        assert connection.execute("SELECT count(*) FROM store_products").fetchone() == (1,)
        assert connection.execute("SELECT count(*) FROM price_observations").fetchone() == (1,)
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == ("a6f20488d7b1",)


def test_db_init_adds_observation_measurements_without_replacing_existing_rows(tmp_path):
    db_path = (tmp_path / "preserve.sqlite3").resolve()
    environment = {
        **os.environ,
        "DATABASE_URL": URL.create("sqlite", database=str(db_path)).render_as_string(),
    }
    predecessor = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "f41d0c2a9b73"],
        cwd=cli.BACKEND_DIR, env=environment, capture_output=True, text=True, check=False,
    )
    assert predecessor.returncode == 0, predecessor.stdout + predecessor.stderr
    import sqlite3
    with sqlite3.connect(db_path) as connection:
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("INSERT INTO stores (id, name, base_url) VALUES (41, 'Existing', 'https://existing.test')")
        connection.execute("INSERT INTO products (id, name, barcode) VALUES (51, 'Existing product', '0123456789012')")
        connection.execute("INSERT INTO store_products (id, store_id, product_id, product_url, product_name, currency) VALUES (61, 41, 51, 'https://existing.test/p', 'Existing listing', 'ARS')")
        connection.execute("INSERT INTO price_observations (id, store_product_id, amount, currency, observed_at) VALUES (71, 61, 123.45, 'ARS', '2026-11-01 00:00:00')")
        connection.commit()
        before = {
            table: connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            for table in ("stores", "products", "store_products", "price_observations")
        }

    assert cli.main(["--db", str(db_path), "db", "init"]) == 0
    with sqlite3.connect(db_path) as connection:
        for table, rows in before.items():
            after = connection.execute(f"SELECT * FROM {table} ORDER BY 1").fetchall()
            assert [row[:len(rows[0])] for row in after] == rows
        columns = {row[1] for row in connection.execute("PRAGMA table_info(price_observations)")}
        assert {"observed_package_quantity", "observed_package_unit", "observed_package_count"} <= columns
        assert connection.execute("SELECT version_num FROM alembic_version").fetchone() == (cli.ALEMBIC_HEAD,)


def test_db_init_refuses_an_unrecognized_existing_database(tmp_path):
    db_path = tmp_path / "existing.sqlite3"
    import sqlite3

    with sqlite3.connect(db_path) as connection:
        connection.execute("CREATE TABLE user_data (id INTEGER PRIMARY KEY)")

    assert cli.main(["--db", str(db_path), "db", "init"]) == 2
    with sqlite3.connect(db_path) as connection:
        assert connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='user_data'"
        ).fetchone()


def test_store_and_listing_registration_are_idempotent(tmp_path):
    path = cli.init_db(tmp_path / "catalog.sqlite3")
    engine = cli._make_engine(path)
    try:
        with Session(engine) as session:
            store, created = cli.add_store(session, "Frávega", "https://www.fravega.com", "AR")
            assert created
            duplicate, created = cli.add_store(session, "Frávega", "https://www.fravega.com/", "AR")
            assert not created
            assert duplicate.id == store.id

            listing, created = cli.add_listing(
                session, store.id, "Fixture de prueba", SYNTHETIC_URL, "ars", "0123456789012"
            )
            assert created
            duplicate, created = cli.add_listing(
                session, store.id, "Fixture de prueba", SYNTHETIC_URL, "ARS", "0123456789012"
            )
            assert not created
            assert duplicate.id == listing.id
            assert session.scalar(select(Product).where(Product.barcode == "0123456789012"))
            assert len(session.scalars(select(StoreProduct)).all()) == 1

            second_listing, created = cli.add_listing(
                session, store.id, "Fixture de prueba", "https://www.fravega.com/p/fixture-second/", "ARS"
            )
            assert created
            assert second_listing.product_id != listing.product_id
            assert len(session.scalars(select(Product)).all()) == 2
    finally:
        engine.dispose()


def test_listing_validation_and_conflicts_do_not_overwrite(tmp_path):
    path = cli.init_db(tmp_path / "catalog.sqlite3")
    engine = cli._make_engine(path)
    try:
        with Session(engine) as session:
            store, _ = cli.add_store(session, "Frávega", "https://www.fravega.com")
            with pytest.raises(ValueError, match="GTIN"):
                cli.add_listing(session, store.id, "Fixture", SYNTHETIC_URL, "ARS", "bad")
            with pytest.raises(ValueError, match="checksum"):
                cli.add_listing(session, store.id, "Fixture", SYNTHETIC_URL, "ARS", "0123456789013")
            with pytest.raises(ValueError, match="HTTPS"):
                cli.add_listing(session, store.id, "Fixture", "http://www.fravega.com/p/x", "ARS")
            cli.add_listing(session, store.id, "Fixture", SYNTHETIC_URL, "ARS")
            with pytest.raises(ValueError, match="otros datos"):
                cli.add_listing(session, store.id, "Otro nombre", SYNTHETIC_URL, "ARS")
    finally:
        engine.dispose()


def test_name_without_gtin_does_not_reuse_or_modify_a_canonical_product(tmp_path):
    path = cli.init_db(tmp_path / "catalog.sqlite3")
    engine = cli._make_engine(path)
    try:
        with Session(engine) as session:
            store, _ = cli.add_store(session, "FrÃ¡vega", "https://www.fravega.com")
            curated = Product(name="Fixture de prueba", barcode="0123456789012")
            session.add(curated)
            session.commit()
            curated_id = curated.id

            listing, created = cli.add_listing(
                session, store.id, "Fixture de prueba",
                "https://www.fravega.com/p/no-gtin/", "ARS",
            )

            assert created is True
            assert listing.product_id != curated_id
            assert session.get(Product, curated_id).barcode == "0123456789012"
            assert len(session.scalars(select(Product)).all()) == 2
    finally:
        engine.dispose()


def test_listing_cli_can_store_explicit_package_measurement(tmp_path):
    path = cli.init_db(tmp_path / "catalog.sqlite3")
    engine = cli._make_engine(path)
    try:
        with Session(engine) as session:
            store, _ = cli.add_store(session, "FrÃ¡vega", "https://www.fravega.com")
            listing, created = cli.add_listing(
                session, store.id, "Pack de fixture", SYNTHETIC_URL, "ARS",
                package_quantity="500", package_unit="ml", package_count=6,
            )

            product = session.get(Product, listing.product_id)
            assert created is True
            assert product.package_quantity == Decimal("500.000000")
            assert product.package_unit == "ml"
            assert product.package_count == 6
    finally:
        engine.dispose()


def test_unlinked_listing_retry_fills_product_and_package_fields_idempotently(tmp_path):
    path = cli.init_db(tmp_path / "catalog.sqlite3")
    engine = cli._make_engine(path)
    try:
        with Session(engine) as session:
            store, _ = cli.add_store(session, "Frávega", "https://www.fravega.com")
            prior = StoreProduct(
                store_id=store.id, product_id=None, product_url=SYNTHETIC_URL,
                product_name="Pack de fixture", currency="ARS",
            )
            session.add(prior)
            session.commit()
            arguments = (session, store.id, "Pack de fixture", SYNTHETIC_URL, "ARS", "0123456789012", "500", "ml", 6)

            retry, created = cli.add_listing(*arguments)
            product_id = retry.product_id
            assert created is False and product_id is not None
            product = session.get(Product, product_id)
            assert (product.package_quantity, product.package_unit, product.package_count) == (
                Decimal("500.000000"), "ml", 6,
            )
            again, created = cli.add_listing(*arguments)
            assert created is False
            assert again.id == prior.id and again.product_id == product_id
            assert len(session.scalars(select(Product)).all()) == 1
    finally:
        engine.dispose()


@pytest.mark.parametrize("quantity", ["0.0000001", "100000000", "NaN", "Infinity"])
def test_listing_rejects_quantity_outside_storage_contract(tmp_path, quantity):
    path = cli.init_db(tmp_path / "catalog.sqlite3")
    engine = cli._make_engine(path)
    try:
        with Session(engine) as session:
            store, _ = cli.add_store(session, "Frávega", "https://www.fravega.com")
            with pytest.raises(ValueError):
                cli.add_listing(
                    session, store.id, "Fixture", SYNTHETIC_URL, "ARS",
                    package_quantity=quantity, package_unit="ml", package_count=1,
                )
    finally:
        engine.dispose()


def test_gtin_conflict_for_existing_listing_requires_review_and_keeps_link(tmp_path):
    path = cli.init_db(tmp_path / "catalog.sqlite3")
    engine = cli._make_engine(path)
    try:
        with Session(engine) as session:
            store, _ = cli.add_store(session, "FrÃ¡vega", "https://www.fravega.com")
            listing, _ = cli.add_listing(
                session, store.id, "Fixture de prueba", SYNTHETIC_URL,
                "ARS", "0123456789012",
            )
            original_product_id = listing.product_id

            with pytest.raises(ValueError, match="GTIN contradice.*revisión manual"):
                cli.add_listing(
                    session, store.id, "Fixture de prueba", SYNTHETIC_URL,
                    "ARS", "1123456789011",
                )

            session.refresh(listing)
            assert listing.product_id == original_product_id
            assert session.get(Product, original_product_id).barcode == "0123456789012"
    finally:
        engine.dispose()


def test_full_cli_flow_with_simulated_http_response(tmp_path, monkeypatch, capsys):
    db_path = tmp_path / "workflow.sqlite3"
    assert cli.main(["--db", str(db_path), "db", "init"]) == 0
    assert cli.main([
        "--db", str(db_path), "store", "add", "--name", "Frávega",
        "--base-url", "https://www.fravega.com", "--country", "AR",
    ]) == 0
    assert cli.main([
        "--db", str(db_path), "listing", "add", "--store-id", "1",
        "--name", "Fixture de prueba (no producto real)", "--url", SYNTHETIC_URL,
        "--currency", "ARS",
    ]) == 0

    def fake_http(url: str) -> str:
        if url.endswith("/robots.txt"):
            return "User-agent: *\nAllow: /p/\n"
        return SYNTHETIC_HTML

    monkeypatch.setattr(cli, "extractor_for_store", lambda _store: FravegaExtractor(
        get_text=fake_http, minimum_interval_seconds=0, sleep=lambda _seconds: None
    ))
    assert cli.main(["--db", str(db_path), "extract", "--store-id", "1"]) == 0
    output = capsys.readouterr().out
    assert "status=SUCCESS" in output
    assert "observations_created=1" in output

    engine = cli._make_engine(db_path)
    try:
        with Session(engine) as session:
            observation = session.scalar(select(PriceObservation))
            assert observation is not None
            assert observation.amount == Decimal("123.45")
            assert session.scalar(select(ExtractionRun)).status == "SUCCESS"
    finally:
        engine.dispose()

    assert cli.main(["--db", str(db_path), "observations", "--store-id", "1"]) == 0
    assert "Fixture de prueba" in capsys.readouterr().out
    assert cli.main(["--db", str(db_path), "runs"]) == 0
    assert "status=SUCCESS" in capsys.readouterr().out
