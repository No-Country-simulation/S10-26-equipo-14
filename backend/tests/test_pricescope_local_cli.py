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
            assert second_listing.product_id == listing.product_id
            assert len(session.scalars(select(Product)).all()) == 1
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
            with pytest.raises(ValueError, match="HTTPS"):
                cli.add_listing(session, store.id, "Fixture", "http://www.fravega.com/p/x", "ARS")
            cli.add_listing(session, store.id, "Fixture", SYNTHETIC_URL, "ARS")
            with pytest.raises(ValueError, match="otros datos"):
                cli.add_listing(session, store.id, "Otro nombre", SYNTHETIC_URL, "ARS")
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
