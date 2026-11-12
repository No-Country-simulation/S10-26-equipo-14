"""Fetch official and parallel USD/ARS quotes into the fixed local SQLite DB.

Run from backend with ``python -m app.commands.ingest_exchange_rates``. This
command does not read DATABASE_URL or .env and never migrates the database.
"""

from __future__ import annotations

import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.services.exchange_rate_providers import BcraOfficialProvider, DolarApiBlueProvider
from app.services.ingestion import persist_quotes, record_run

BACKEND_DIR = Path(__file__).resolve().parents[2]
MAIN_DB = (BACKEND_DIR / ".local" / "pricescope.sqlite3").resolve()
ALEMBIC_HEAD = "9c7e2a1f4b60"


def _validate_database() -> None:
    if not MAIN_DB.is_file():
        raise ValueError(f"No existe la SQLite local esperada: {MAIN_DB}")
    connection = sqlite3.connect(f"file:{MAIN_DB.as_posix()}?mode=ro", uri=True)
    try:
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            )
        }
        if not {"alembic_version", "exchange_rates", "extraction_runs"}.issubset(tables):
            raise ValueError("La SQLite no contiene el esquema de cotizaciones esperado.")
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()
        if revision is None or revision[0] != ALEMBIC_HEAD:
            raise ValueError("La SQLite local no está en la revisión esperada; no se migró.")
    finally:
        connection.close()


def main() -> int:
    try:
        providers = (BcraOfficialProvider(), DolarApiBlueProvider())
        fetched: list[tuple[object, datetime, tuple, str | None]] = []
        for provider in providers:
            started = datetime.now(timezone.utc)
            try:
                quotes = tuple(provider.fetch())
                fetched.append((provider, started, quotes, None))
            except Exception as exc:
                # Provider errors are recorded per source without logging headers
                # or response bodies, and the other provider is still attempted.
                fetched.append((provider, started, (), str(exc)[:1000]))

        _validate_database()
        engine = create_engine(URL.create("sqlite", database=str(MAIN_DB)))

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        report = []
        with Session(engine) as session, session.begin():
            for provider, started, quotes, error in fetched:
                source = getattr(provider, "name", "exchange-rate-provider")[:100]
                created = persist_quotes(session, quotes) if quotes else 0
                finished = datetime.now(timezone.utc)
                run = record_run(
                    session,
                    source=f"exchange-rates:{source}",
                    status="failed" if error else "succeeded",
                    records_seen=len(quotes),
                    started_at=started,
                    finished_at=finished,
                    error_summary=error,
                )
                session.flush()
                report.append({"source": source, "status": run.status,
                               "quotes_received": len(quotes), "quotes_created": created})
        engine.dispose()
        print(f"Cotizaciones procesadas en SQLite local {MAIN_DB}: {report}")
        return 0 if any(item[3] is None for item in fetched) else 2
    except Exception as exc:
        print(f"No se pudieron persistir las cotizaciones en SQLite local: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
