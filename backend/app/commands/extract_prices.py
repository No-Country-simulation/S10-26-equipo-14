"""Manually run one store extraction against a local development database."""

import argparse
import sys

from app.db.session import SessionLocal, engine
from app.extractors import ExtractionError, extractor_for_store
from app.models import Store
from app.services.extraction import run_store_extraction


def _is_local_database() -> bool:
    if engine.url.get_backend_name() == "sqlite":
        return True
    return (engine.url.host or "").lower() in {"localhost", "127.0.0.1", "::1"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--store-id", type=int, required=True, help="ID de una tienda activa ya registrada")
    args = parser.parse_args(argv)

    # This command persists history. Keep it local-only so a workstation .env
    # cannot accidentally send observations to Neon or another remote database.
    if not _is_local_database():
        print(
            "Refusado: el comando solo puede escribir en SQLite o PostgreSQL local.",
            file=sys.stderr,
        )
        return 2

    try:
        with SessionLocal() as session:
            store = session.get(Store, args.store_id)
            if store is None:
                raise ExtractionError(f"No existe la tienda con id {args.store_id}.")
            extractor = extractor_for_store(store)
            result = run_store_extraction(session, store.id, extractor)
    except (ExtractionError, ValueError) as exc:
        print(f"Extracción no iniciada: {exc}", file=sys.stderr)
        return 2
    finally:
        engine.dispose()

    print(
        f"run_id={result.run_id} source={result.source} status={result.status} "
        f"records_seen={result.records_seen} observations_created={result.observations_created}"
    )
    for error in result.errors:
        print(f"ERROR: {error}", file=sys.stderr)
    return 0 if result.status == "SUCCESS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
