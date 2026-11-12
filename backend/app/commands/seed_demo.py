"""Populate the existing local SQLite database with clearly synthetic demo data.

The command is a dry run unless ``--apply`` is supplied. It never reads .env,
never creates a database, never migrates, and never accesses the network.
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, event, inspect, select
from sqlalchemy.orm import Session

from app.models import (
    Category,
    ExchangeRate,
    PriceObservation,
    Product,
    Store,
    StoreIntegration,
    StoreMonitoringPreference,
    StoreProduct,
)

BACKEND_DIR = Path(__file__).resolve().parents[2]
MAIN_DB = (BACKEND_DIR / ".local" / "pricescope.sqlite3").resolve()
ALEMBIC_HEAD = "9c7e2a1f4b60"
PRODUCT_COUNT = 21
OBSERVATION_DATES = tuple(
    datetime(2026, 11, day, 12, tzinfo=timezone.utc) for day in (1, 2, 3)
)
CATEGORIES = (
    ("DEMO PriceScope Alimentos", "demo-pricescope-alimentos"),
    ("DEMO PriceScope Hogar", "demo-pricescope-hogar"),
    ("DEMO PriceScope Tecnología", "demo-pricescope-tecnologia"),
)
STORES = (
    ("DEMO PriceScope Tienda A", "https://pricescope-demo-a.example.invalid"),
    ("DEMO PriceScope Tienda B", "https://pricescope-demo-b.example.invalid"),
)
RATE_SOURCE = "DEMO sintético local (no es una fuente real)"


def _get_or_create(session: Session, model, criteria: dict, values: dict):
    row = session.scalar(select(model).filter_by(**criteria))
    if row is None:
        row = model(**values)
        session.add(row)
        session.flush()
        return row, True
    for field, expected in values.items():
        current = getattr(row, field)
        if isinstance(current, datetime) and isinstance(expected, datetime):
            current = current.replace(tzinfo=timezone.utc) if current.tzinfo is None else current.astimezone(timezone.utc)
            expected = expected.replace(tzinfo=timezone.utc) if expected.tzinfo is None else expected.astimezone(timezone.utc)
        if current != expected:
            raise ValueError(
                f"Conflicto con el registro demo existente {model.__tablename__}.{field}; "
                "no se sobrescribieron datos."
            )
    return row, False


def populate(session: Session) -> dict[str, int]:
    """Create the fixture idempotently; existing conflicts cause a rollback."""
    counts = {"categories": 0, "stores": 0, "products": 0, "listings": 0, "observations": 0, "rates": 0}
    categories: list[Category] = []
    for name, slug in CATEGORIES:
        row, created = _get_or_create(session, Category, {"slug": slug}, {"name": name, "slug": slug})
        categories.append(row)
        counts["categories"] += int(created)

    stores: list[Store] = []
    for name, base_url in STORES:
        store, created = _get_or_create(
            session,
            Store,
            {"name": name},
            {"name": name, "base_url": base_url, "country": "AR", "is_active": True},
        )
        stores.append(store)
        counts["stores"] += int(created)

        integration, integration_created = _get_or_create(
            session,
            StoreIntegration,
            {"store_id": store.id},
            {
                "store_id": store.id,
                "status": "pending",
                "analyzer_key": None,
                "analysis_message": "Fixture sintética; no se analizó ni consultó el sitio.",
                "analysis_candidates": [],
            },
        )
        del integration
        preference, preference_created = _get_or_create(
            session,
            StoreMonitoringPreference,
            {"store_id": store.id},
            {"store_id": store.id, "currency": "ARS", "interval_hours": 24, "is_enabled": False},
        )
        del preference
        if integration_created or preference_created:
            session.flush()

    products: list[Product] = []
    for number in range(1, PRODUCT_COUNT + 1):
        category = categories[(number - 1) % len(categories)]
        name = f"DEMO PriceScope Producto {number:02d}"
        product, created = _get_or_create(
            session,
            Product,
            {"name": name},
            {"name": name, "brand": "DEMO sintético", "model": f"DEMO-{number:02d}", "category_id": category.id},
        )
        products.append(product)
        counts["products"] += int(created)

        for store_index, store in enumerate(stores):
            external_id = f"demo-pricescope-{number:02d}"
            product_url = f"{store.base_url}/items/{number:02d}"
            listing, listing_created = _get_or_create(
                session,
                StoreProduct,
                {"store_id": store.id, "external_id": external_id},
                {
                    "store_id": store.id,
                    "product_id": product.id,
                    "category_id": category.id,
                    "external_id": external_id,
                    "product_url": product_url,
                    "product_name": name,
                    "currency": "ARS",
                },
            )
            counts["listings"] += int(listing_created)

            for date_index, observed_at in enumerate(OBSERVATION_DATES):
                amount = Decimal(1000 + number * 25 + store_index * 75 + date_index * 10).quantize(Decimal("0.01"))
                observation, created_observation = _get_or_create(
                    session,
                    PriceObservation,
                    {"store_product_id": listing.id, "observed_at": observed_at},
                    {
                        "store_product_id": listing.id,
                        "amount": amount,
                        "currency": "ARS",
                        "source_url": product_url,
                        "is_available": True,
                        "observed_at": observed_at,
                    },
                )
                del observation
                counts["observations"] += int(created_observation)

    for date_index, observed_at in enumerate(OBSERVATION_DATES):
        rate_values = {
            "source": RATE_SOURCE,
            "rate_type": "demo",
            "rate_side": "reference",
            "base_currency": "USD",
            "quote_currency": "ARS",
            "observed_at": observed_at,
        }
        rate, created = _get_or_create(
            session,
            ExchangeRate,
            rate_values,
            {**rate_values, "rate": Decimal(1400 + date_index * 25).quantize(Decimal("0.000001"))},
        )
        del rate
        counts["rates"] += int(created)

    session.flush()
    if session.scalar(select(Product.id).where(Product.name.like("DEMO PriceScope Producto%"))) is None:
        raise RuntimeError("El fixture no creó los productos demo esperados.")
    return counts


def _validate_database(path: Path) -> None:
    if path != MAIN_DB:
        raise ValueError(f"Este fixture solo admite la SQLite principal: {MAIN_DB}")
    if not path.is_file():
        raise ValueError("La SQLite principal no existe; el fixture no crea bases de datos.")
    with create_engine(f"sqlite:///{path.as_posix()}").connect() as connection:
        inspector = inspect(connection)
        required = {"alembic_version", "categories", "stores", "products", "store_products", "price_observations", "exchange_rates", "extraction_runs"}
        if not required.issubset(set(inspector.get_table_names())):
            raise ValueError("La SQLite principal no tiene el esquema esperado; no se ejecutó ninguna migración.")
        revision = connection.exec_driver_sql("SELECT version_num FROM alembic_version").scalar_one_or_none()
        if revision != ALEMBIC_HEAD:
            raise ValueError(f"Revisión inesperada {revision!r}; se requiere {ALEMBIC_HEAD}.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true", help="Confirmar la inserción del fixture en la SQLite principal")
    args = parser.parse_args(argv)
    try:
        _validate_database(MAIN_DB)
        if not args.apply:
            print(f"Dry run: fixture listo para {MAIN_DB}. No se escribió ningún dato.")
            print(f"Al ejecutar con --apply añadirá hasta 3 categorías, 2 tiendas, {PRODUCT_COUNT} productos, {PRODUCT_COUNT * len(STORES)} listados, {PRODUCT_COUNT * len(STORES) * len(OBSERVATION_DATES)} observaciones y {len(OBSERVATION_DATES)} cotizaciones sintéticas; no crea ejecuciones.")
            return 0

        engine = create_engine(f"sqlite:///{MAIN_DB.as_posix()}")

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(connection, _record):
            connection.execute("PRAGMA foreign_keys=ON")

        with Session(engine) as session, session.begin():
            counts = populate(session)
        print(f"Fixture sintético aplicado de forma idempotente a {MAIN_DB}: {counts}")
        return 0
    except Exception as exc:
        print(f"No se aplicó el fixture: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
