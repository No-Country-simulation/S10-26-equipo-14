"""Daily production ingestion entry point for a hosted scheduler.

Invoke with ``python -m app.commands.daily_ingestion``. It uses the configured
SQLAlchemy database URL and appends extraction/FX run history; it never migrates
or seeds the database.
"""

from __future__ import annotations

import json
import sys
from contextlib import contextmanager
from datetime import datetime, time, timezone

from sqlalchemy import select, text
from sqlalchemy.orm import sessionmaker

from app.db.session import SessionLocal
from app.extractors import ExtractionError, extractor_for_store
from app.models import ExtractionRun, Store, StoreMonitoringPreference
from app.services.exchange_rate_providers import BcraOfficialProvider, DolarApiBlueProvider
from app.services.extraction import run_store_extraction
from app.services.ingestion import persist_quotes

_DAILY_LOCK_ID = 0x5052494345444149


@contextmanager
def _postgres_lock(session, lock_id: int):
    """Use a transaction-scoped lock held on a separate connection."""
    bind = session.get_bind()
    if bind.dialect.name != "postgresql":
        yield True
        return
    with bind.connect() as connection:
        transaction = connection.begin()
        try:
            acquired = bool(connection.execute(
                text("SELECT pg_try_advisory_xact_lock(:lock_id)"), {"lock_id": lock_id}
            ).scalar_one())
            yield acquired
        finally:
            transaction.rollback()


def run_daily_ingestion(
    session_factory: sessionmaker = SessionLocal,
    *,
    now: datetime | None = None,
    providers=None,
) -> dict[str, object]:
    """Run enabled stores and public FX providers once per UTC calendar day."""
    instant = now or datetime.now(timezone.utc)
    if instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("now debe incluir zona horaria")
    instant = instant.astimezone(timezone.utc)
    day_start = datetime.combine(instant.date(), time.min, tzinfo=timezone.utc)
    day_end = datetime.combine(instant.date(), time.max, tzinfo=timezone.utc)
    provider_list = tuple(providers or (BcraOfficialProvider(), DolarApiBlueProvider()))
    store_results: list[dict[str, object]] = []
    quote_results: list[dict[str, object]] = []

    with session_factory() as session:
        with _postgres_lock(session, _DAILY_LOCK_ID) as acquired:
            if not acquired:
                return {"status": "already_running", "stores": [], "exchange_rates": []}
            previous = session.scalars(select(ExtractionRun).where(
                ExtractionRun.source == "daily-pipeline",
                ExtractionRun.started_at >= day_start,
                ExtractionRun.started_at <= day_end,
            ).order_by(ExtractionRun.started_at.desc())).first()
            if previous and previous.status != "running":
                return {"status": "already_completed", "run_id": previous.id, "stores": [], "exchange_rates": []}
            if previous and previous.status == "running":
                previous.status = "ABANDONED"
                previous.finished_at = instant
                previous.error_summary = "Ejecución diaria anterior interrumpida; se reanuda bajo bloqueo exclusivo."
                session.commit()

            pipeline = ExtractionRun(
                source="daily-pipeline", store_id=None, status="running", records_seen=0,
                started_at=instant,
            )
            session.add(pipeline)
            session.commit()
            pipeline_id = pipeline.id

            store_ids = session.scalars(
                select(Store.id)
                .join(StoreMonitoringPreference, StoreMonitoringPreference.store_id == Store.id)
                .where(Store.is_active.is_(True), StoreMonitoringPreference.is_enabled.is_(True))
                .order_by(Store.id)
            ).all()
            for store_id in store_ids:
                with _postgres_lock(session, 0x5052494353434F50 ^ store_id) as store_locked:
                    if not store_locked:
                        store_results.append({"store_id": store_id, "status": "already_running"})
                        continue
                    try:
                        store = session.get(Store, store_id)
                        if store is None:
                            continue
                        result = run_store_extraction(session, store_id, extractor_for_store(store))
                        store_results.append({
                            "store_id": store_id, "run_id": result.run_id, "status": result.status,
                            "records_seen": result.records_seen,
                            "products_created": result.products_created,
                            "prices_changed": result.prices_changed,
                            "observations_created": result.observations_created,
                            "errors": list(result.errors),
                        })
                    except (ExtractionError, ValueError) as exc:
                        store_results.append({"store_id": store_id, "status": "failed", "error": str(exc)[:500]})
                    except Exception:
                        # Do not log connection strings, headers, or arbitrary exception payloads.
                        store_results.append({"store_id": store_id, "status": "failed", "error": "Error interno durante la extracción."})

            for provider in provider_list:
                started = datetime.now(timezone.utc)
                quote_run = ExtractionRun(
                    source=f"exchange-rates:{provider.name}"[:100], store_id=None,
                    status="running", records_seen=0, started_at=started,
                )
                session.add(quote_run)
                session.commit()
                quote_run_id = quote_run.id
                try:
                    quotes = tuple(provider.fetch())
                    count = persist_quotes(session, quotes)
                    row = session.get(ExtractionRun, quote_run_id)
                    row.status = "SUCCESS"
                    row.records_seen = len(quotes)
                    row.finished_at = datetime.now(timezone.utc)
                    session.commit()
                    quote_results.append({"run_id": quote_run_id, "source": provider.name,
                                          "status": "SUCCESS", "quotes_seen": len(quotes),
                                          "quotes_created": count})
                except Exception:
                    session.rollback()
                    row = session.get(ExtractionRun, quote_run_id)
                    if row is not None:
                        row.status = "FAILED"
                        row.finished_at = datetime.now(timezone.utc)
                        row.error_summary = "No se pudo obtener o persistir la cotización pública."
                        session.commit()
                    quote_results.append({"run_id": quote_run_id, "source": provider.name,
                                          "status": "FAILED", "error": "Fuente pública no disponible o respuesta inválida."})

            failures = sum(item.get("status") not in {"SUCCESS", "PARTIAL_SUCCESS"} for item in store_results)
            failures += sum(item.get("status") != "SUCCESS" for item in quote_results)
            has_success = any(item.get("status") in {"SUCCESS", "PARTIAL_SUCCESS"} for item in store_results + quote_results)
            pipeline = session.get(ExtractionRun, pipeline_id)
            pipeline.status = "PARTIAL_SUCCESS" if failures and has_success else "FAILED" if failures else "SUCCESS"
            pipeline.records_seen = sum(int(item.get("records_seen", item.get("quotes_seen", 0))) for item in store_results + quote_results)
            pipeline.finished_at = datetime.now(timezone.utc)
            pipeline.error_summary = f"Fallos: {failures}" if failures else None
            session.commit()

    return {"run_id": pipeline_id, "status": pipeline.status,
            "stores": store_results, "exchange_rates": quote_results}


def main() -> int:
    try:
        result = run_daily_ingestion()
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, default=str))
        return 0 if result.get("status") in {"SUCCESS", "PARTIAL_SUCCESS", "already_completed", "already_running"} else 1
    except Exception:
        print("No se pudo ejecutar la ingestión diaria; revise el estado del servicio y la conexión sin imprimir credenciales.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
