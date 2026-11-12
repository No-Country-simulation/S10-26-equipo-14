"""Register the initial PriceScope target stores without configuring extractors.

This module works with a caller-provided SQLAlchemy session, so it can be used
with either SQLite or PostgreSQL. It does not create schemas, migrate, connect
to a database, or commit the caller's transaction.
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.models import Store, StoreIntegration

BACKEND_DIR = Path(__file__).resolve().parents[2]
MAIN_DB = (BACKEND_DIR / ".local" / "pricescope.sqlite3").resolve()
ALEMBIC_HEAD = "9c7e2a1f4b60"
REQUIRED_TABLES = {"alembic_version", "stores", "store_integrations"}
STORE_NAME_ALIASES = {
    "Tienda Credicoop": ("Tienda Credicoop ficha real",),
}


TARGET_STORE_NAMES = (
    "Tienda Credicoop",
    "Fr\u00e1vega",
    "Carrefour",
    "Coto Digital",
    "Jumbo",
    "D\u00eda Online",
    "Changom\u00e1s",
    "Cetrogar",
    "Naldo",
    "Megatone",
    "On City",
    "Easy",
    "Coppel",
    "Farmacity",
    "Musimundo",
)

UNCONFIGURED_MESSAGE = (
    "Tienda registrada para PriceScope. URL base pendiente de verificaci\u00f3n; "
    "no se configur\u00f3 ni verific\u00f3 ning\u00fan extractor."
)


def populate(session: Session) -> dict[str, int]:
    """Add missing target stores and pending integrations without overwriting.

    Matching is case-insensitive by store name. Existing stores and integration
    records are left untouched, including their URLs, status, and analysis data.
    The caller controls commit/rollback.
    """
    counts = {"stores": 0, "integrations": 0}

    for name in TARGET_STORE_NAMES:
        accepted_names = (name, *STORE_NAME_ALIASES.get(name, ()))
        matches = session.scalars(
            select(Store).where(func.lower(Store.name).in_(
                tuple(candidate.lower() for candidate in accepted_names)
            ))
        ).all()
        if len(matches) > 1:
            raise ValueError(
                f"Hay varias tiendas existentes que coinciden con {name!r}; "
                "no se modific\u00f3 ninguna."
            )

        if matches:
            store = matches[0]
        else:
            # Empty base_url explicitly represents an unknown URL. In particular,
            # do not fabricate a URL or infer one from the store's name.
            store = Store(name=name, base_url="", country="AR", is_active=True)
            session.add(store)
            session.flush()
            counts["stores"] += 1

        integration = session.scalar(
            select(StoreIntegration).where(StoreIntegration.store_id == store.id)
        )
        if integration is None:
            session.add(
                StoreIntegration(
                    store_id=store.id,
                    status="configuration_required",
                    analyzer_key=None,
                    analysis_message=UNCONFIGURED_MESSAGE,
                    analysis_candidates=[],
                )
            )
            counts["integrations"] += 1

    session.flush()
    return counts


def _validate_database() -> None:
    """Refuse missing, unexpected, or non-current local SQLite databases."""
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
        if not REQUIRED_TABLES.issubset(tables):
            raise ValueError("La SQLite local no contiene el esquema de tiendas esperado.")
        revision = connection.execute(
            "SELECT version_num FROM alembic_version"
        ).fetchone()
        if revision is None or revision[0] != ALEMBIC_HEAD:
            raise ValueError(
                f"Revisión Alembic inesperada ({revision[0] if revision else None!r}); "
                f"se requiere {ALEMBIC_HEAD}."
            )
    finally:
        connection.close()


def main() -> int:
    """Seed only backend/.local/pricescope.sqlite3; ignores DATABASE_URL/.env."""
    try:
        _validate_database()
        # Construct an explicit SQLite URL from this module's fixed local path.
        engine = create_engine(URL.create("sqlite", database=str(MAIN_DB)))

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        with Session(engine) as session, session.begin():
            counts = populate(session)
        engine.dispose()
        print(f"Seed de tiendas aplicado a SQLite local {MAIN_DB}: {counts}")
        return 0
    except Exception as exc:
        print(f"No se aplicó el seed de tiendas: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
