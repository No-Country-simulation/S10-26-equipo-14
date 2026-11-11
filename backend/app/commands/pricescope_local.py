"""Local-only SQLite workflow for registering and extracting known listings.

This command deliberately never reads application settings or ``.env``. Its
database path is always an explicit local SQLite file.
"""

from __future__ import annotations

import argparse
import os
import re
import sqlite3
import subprocess
import sys
from datetime import timezone
from pathlib import Path
from urllib.parse import urlsplit

from sqlalchemy import create_engine, event, select
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session

from app.extractors import ExtractionError, extractor_for_store
from app.extractors.fravega import FravegaExtractor
from app.models import ExtractionRun, PriceObservation, Product, Store, StoreProduct
from app.services.extraction import run_store_extraction

BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DB = BACKEND_DIR / ".local" / "pricescope.sqlite3"
ALEMBIC_HEAD = "a6f20488d7b1"
MARKET_TABLES = {
    "stores", "categories", "products", "store_products",
    "price_observations", "exchange_rates", "extraction_runs", "alembic_version",
}
EXPECTED_TABLES = MARKET_TABLES | {
    "store_integrations", "store_monitoring_preferences", "store_monitoring_categories",
}
EMPTY_STATE = frozenset()
INITIAL_STATE = frozenset({"stores", "alembic_version"})
MARKET_STATE = frozenset(MARKET_TABLES)
FULL_STATE = frozenset(EXPECTED_TABLES)
SAFE_STATES = {
    EMPTY_STATE,
    INITIAL_STATE,
    MARKET_STATE,
    FULL_STATE,
}
GTIN_RE = re.compile(r"^(?:\d{8}|\d{12}|\d{13}|\d{14})$")


def _local_db_path(raw_path: str | Path) -> Path:
    path = Path(raw_path).expanduser().resolve()
    if path.suffix.lower() not in {".sqlite", ".sqlite3", ".db"}:
        raise ValueError("La base local debe usar extensión .sqlite, .sqlite3 o .db.")
    if str(path).startswith("\\\\"):
        raise ValueError("No se permiten rutas de red para la base SQLite local.")
    return path


def _read_sqlite_state(path: Path) -> tuple[frozenset[str], str | None]:
    if not path.exists() or path.stat().st_size == 0:
        return frozenset(), None
    try:
        connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
        try:
            tables = frozenset(row[0] for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ))
            revision = None
            if "alembic_version" in tables:
                row = connection.execute("SELECT version_num FROM alembic_version").fetchone()
                revision = row[0] if row else None
            return tables, revision
        finally:
            connection.close()
    except sqlite3.Error as exc:
        raise ValueError("El archivo existente no se reconoce como una base SQLite legible.") from exc


def _make_engine(path: Path):
    engine = create_engine(URL.create("sqlite", database=str(path)))

    @event.listens_for(engine, "connect")
    def _enable_foreign_keys(connection, _record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


def init_db(raw_path: str | Path) -> Path:
    path = _local_db_path(raw_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tables, revision = _read_sqlite_state(path)
    if tables not in SAFE_STATES:
        raise ValueError(f"Esquema SQLite inesperado; no se migró. Tablas detectadas: {', '.join(sorted(tables))}.")
    if tables == INITIAL_STATE and revision != "cb0deba93496":
        raise ValueError("La base solo tiene stores, pero su revisión Alembic no es la inicial esperada.")
    if tables == MARKET_STATE and revision not in {"4db267e3b121", "d8f31a9c0e42"}:
        raise ValueError("El esquema de mercado tiene una revisión Alembic inesperada.")
    if tables == FULL_STATE and revision != ALEMBIC_HEAD:
        raise ValueError("El esquema SQLite completo tiene una revisión Alembic inesperada.")

    database_url = URL.create("sqlite", database=str(path)).render_as_string(hide_password=False)
    environment = {**os.environ, "DATABASE_URL": database_url}
    completed = subprocess.run(
        [sys.executable, "-m", "alembic", "-c", "alembic.ini", "upgrade", "head"],
        cwd=BACKEND_DIR,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode:
        # Avoid emitting the constructed URL even if Alembic includes it in diagnostics.
        message = "\n".join(line for line in (completed.stdout + completed.stderr).splitlines()
                             if "sqlite:///" not in line and "DATABASE_URL" not in line)
        raise RuntimeError(f"Alembic no pudo inicializar SQLite (código {completed.returncode}).\n{message}")
    final_tables, final_revision = _read_sqlite_state(path)
    if final_tables != EXPECTED_TABLES or final_revision != ALEMBIC_HEAD:
        raise RuntimeError("La validación posterior de esquema SQLite no coincide con el head esperado.")
    return path


def _assert_initialized(path: Path) -> None:
    tables, revision = _read_sqlite_state(path)
    if tables != EXPECTED_TABLES or revision != ALEMBIC_HEAD:
        raise ValueError("La base no está inicializada en el head esperado; ejecuta primero `db init`.")


def _validate_https_url(value: str):
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or parsed.query or parsed.fragment or parsed.port not in {None, 443}):
        raise ValueError("La URL debe ser HTTPS pública y no incluir credenciales, query ni fragmento.")
    return parsed


def _store_host(host: str | None) -> str | None:
    if host and host.lower() in {"fravega.com", "www.fravega.com"}:
        return "fravega.com"
    return host.lower() if host else None


def _normalize_listing_url(value: str) -> str:
    parsed = _validate_https_url(value)
    path = parsed.path.rstrip("/") or "/"
    return f"https://{parsed.netloc.lower()}{path}"


def add_store(session: Session, name: str, base_url: str, country: str | None = None) -> tuple[Store, bool]:
    name = name.strip()
    parsed = _validate_https_url(base_url)
    if (not name or len(name) > 150 or parsed.path not in {"", "/"}
            or parsed.port not in {None, 443}):
        raise ValueError("Nombre vacío/largo o URL base que no apunta a la raíz del sitio.")
    normalized_url = f"https://{parsed.netloc.lower()}"
    matches = session.scalars(select(Store).where(Store.name.ilike(name))).all()
    for store in matches:
        if store.base_url.rstrip("/").lower() == normalized_url.lower():
            return store, False
        raise ValueError("Ya existe una tienda con ese nombre y otra URL base.")
    for existing_store in session.scalars(select(Store)).all():
        existing_host = urlsplit(existing_store.base_url).hostname
        if _store_host(existing_host) == _store_host(parsed.hostname):
            raise ValueError("Ya existe una tienda para ese host con otra configuración.")
    store = Store(name=name, base_url=normalized_url, country=country.strip() if country else None)
    session.add(store)
    session.commit()
    return store, True


def add_listing(session: Session, store_id: int, name: str, url: str,
                currency: str, gtin: str | None = None) -> tuple[StoreProduct, bool]:
    store = session.get(Store, store_id)
    if store is None:
        raise ValueError(f"No existe la tienda {store_id}.")
    name = name.strip()
    parsed = _validate_https_url(url)
    store_host = urlsplit(store.base_url).hostname
    if parsed.hostname != store_host:
        raise ValueError("La publicación debe pertenecer al mismo host de la tienda registrada.")
    if store_host in {"fravega.com", "www.fravega.com"}:
        FravegaExtractor.validate_product_url(url)
    if not name or len(name) > 250:
        raise ValueError("El nombre está vacío o excede 250 caracteres (límite del producto canónico).")
    if not re.fullmatch(r"[A-Za-z]{3}", currency):
        raise ValueError("La moneda debe tener tres letras ASCII.")
    currency = currency.upper()
    if gtin is not None and not GTIN_RE.fullmatch(gtin):
        raise ValueError("El GTIN debe tener 8, 12, 13 o 14 dígitos, conservado como texto.")

    normalized_url = _normalize_listing_url(url)
    existing = next((item for item in session.scalars(
        select(StoreProduct).where(StoreProduct.store_id == store_id)
    ).all() if _normalize_listing_url(item.product_url) == normalized_url), None)
    if existing:
        if (existing.product_name, existing.currency, existing.product.barcode if existing.product else None) == (name, currency, gtin):
            return existing, False
        raise ValueError("La URL ya está registrada con otros datos; no se sobrescribió.")

    if gtin:
        product = session.scalar(select(Product).where(Product.barcode == gtin))
        if product is None:
            same_name = session.scalars(select(Product).where(Product.name.ilike(name)).limit(2)).all()
            unkeyed = [candidate for candidate in same_name if candidate.barcode is None]
            if len(unkeyed) == 1 and len(same_name) == 1:
                product = unkeyed[0]
                product.barcode = gtin
    else:
        candidates = session.scalars(select(Product).where(Product.name.ilike(name)).limit(2)).all()
        if len(candidates) > 1:
            raise ValueError("El nombre coincide con varios productos canónicos; registra un GTIN para resolverlo.")
        product = candidates[0] if candidates else None
    if product is None:
        product = Product(name=name, barcode=gtin)
        session.add(product)
        session.flush()
    listing = StoreProduct(store_id=store_id, product_id=product.id, product_url=normalized_url,
                           product_name=name, currency=currency)
    session.add(listing)
    session.commit()
    return listing, True


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", default=str(DEFAULT_DB), help="Archivo SQLite local (por defecto backend/.local/pricescope.sqlite3)")
    commands = parser.add_subparsers(dest="command", required=True)
    db = commands.add_parser("db", help="Operaciones de esquema local")
    db_sub = db.add_subparsers(dest="db_command", required=True)
    db_sub.add_parser("init", help="Aplicar las migraciones existentes a SQLite local")
    store = commands.add_parser("store", help="Registrar tienda")
    store_sub = store.add_subparsers(dest="store_command", required=True)
    store_add = store_sub.add_parser("add")
    store_add.add_argument("--name", required=True)
    store_add.add_argument("--base-url", required=True)
    store_add.add_argument("--country")
    listing = commands.add_parser("listing", help="Registrar publicación conocida")
    listing_sub = listing.add_subparsers(dest="listing_command", required=True)
    listing_add = listing_sub.add_parser("add")
    listing_add.add_argument("--store-id", type=int, required=True)
    listing_add.add_argument("--name", required=True)
    listing_add.add_argument("--url", required=True)
    listing_add.add_argument("--currency", required=True)
    listing_add.add_argument("--gtin")
    extract = commands.add_parser("extract", help="Ejecutar extracción de una tienda")
    extract.add_argument("--store-id", type=int, required=True)
    observations = commands.add_parser("observations", help="Consultar historial local")
    observations.add_argument("--store-id", type=int, required=True)
    observations.add_argument("--limit", type=int, default=20)
    runs = commands.add_parser("runs", help="Consultar ejecuciones locales")
    runs.add_argument("--limit", type=int, default=20)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        path = _local_db_path(args.db)
        if args.command == "db":
            initialized = init_db(path)
            print(f"SQLite inicializado localmente: {initialized}")
            return 0
        _assert_initialized(path)
        if not path.exists():
            raise ValueError("No existe el archivo SQLite local; ejecuta `db init`.")
        engine = _make_engine(path)
        try:
          with Session(engine) as session:
            if args.command == "store":
                item, created = add_store(session, args.name, args.base_url, args.country)
                print(f"store_id={item.id} {'creada' if created else 'ya_existía'}")
            elif args.command == "listing":
                item, created = add_listing(session, args.store_id, args.name, args.url, args.currency, args.gtin)
                print(f"listing_id={item.id} product_id={item.product_id} {'creada' if created else 'ya_existía'}")
            elif args.command == "extract":
                store = session.get(Store, args.store_id)
                if store is None:
                    raise ValueError(f"No existe la tienda {args.store_id}.")
                result = run_store_extraction(session, args.store_id, extractor_for_store(store))
                print(f"run_id={result.run_id} source={result.source} status={result.status} records_seen={result.records_seen} observations_created={result.observations_created}")
                for error in result.errors:
                    print(f"ERROR: {error}", file=sys.stderr)
                return 0 if result.status == "SUCCESS" else 1
            elif args.command == "observations":
                if args.limit < 1 or args.limit > 500:
                    raise ValueError("--limit debe estar entre 1 y 500.")
                rows = session.execute(select(PriceObservation, StoreProduct).join(StoreProduct)
                    .where(StoreProduct.store_id == args.store_id)
                    .order_by(PriceObservation.observed_at.desc()).limit(args.limit)).all()
                if not rows:
                    print("Sin observaciones para esta tienda.")
                for observation, listing in rows:
                    observed = observation.observed_at
                    if observed.tzinfo is None:
                        observed = observed.replace(tzinfo=timezone.utc)
                    print(f"{observed.isoformat()} | {observation.amount} {observation.currency} | {listing.product_name} | {observation.source_url or listing.product_url}")
            elif args.command == "runs":
                if args.limit < 1 or args.limit > 500:
                    raise ValueError("--limit debe estar entre 1 y 500.")
                rows = session.scalars(select(ExtractionRun).order_by(ExtractionRun.started_at.desc()).limit(args.limit)).all()
                if not rows:
                    print("Sin ejecuciones registradas.")
                for run in rows:
                    print(f"run_id={run.id} source={run.source} status={run.status} records_seen={run.records_seen} started_at={run.started_at.isoformat()} errors={run.error_summary or '-'}")
          return 0
        finally:
            engine.dispose()
    except (ValueError, RuntimeError, ExtractionError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
