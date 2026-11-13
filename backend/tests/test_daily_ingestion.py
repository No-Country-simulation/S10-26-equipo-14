from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
import app.models  # noqa: F401
from app.commands import daily_ingestion
from app.models import ExchangeRate, ExtractionRun, Store, StoreMonitoringPreference
class _Provider:
    name = "Verified test provider"

    def fetch(self):
        from app.services.ingestion import RawQuote
        return (RawQuote(Decimal("1250.5"), datetime(2026, 11, 12, tzinfo=timezone.utc),
                         "official", "Verified test provider"),)


def test_daily_ingestion_runs_enabled_stores_and_persists_real_quote_records(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'daily.sqlite'}")
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    store_id = None
    with factory.begin() as session:
        store = Store(name="Test", base_url="https://www.carrefour.com.ar", country="AR")
        session.add(store)
        session.flush()
        store_id = store.id
        session.add(StoreMonitoringPreference(store_id=store.id, currency="ARS", interval_hours=24, is_enabled=True))

    class _Result:
        run_id = 45
        status = "SUCCESS"
        records_seen = 2
        observations_created = 2
        errors = ()

    monkeypatch.setattr(daily_ingestion, "extractor_for_store", lambda _store: object())
    monkeypatch.setattr(daily_ingestion, "run_store_extraction", lambda *_args: _Result())
    instant = datetime(2026, 11, 12, 3, tzinfo=timezone.utc)
    try:
        result = daily_ingestion.run_daily_ingestion(factory, now=instant, providers=(_Provider(),))
        assert result["status"] == "SUCCESS"
        assert result["stores"][0]["store_id"] == store_id
        assert result["stores"][0]["observations_created"] == 2
        assert result["exchange_rates"][0]["quotes_created"] == 1
        with factory() as session:
            rate = session.scalar(select(ExchangeRate))
            assert rate.source == "Verified test provider"
            assert rate.rate == Decimal("1250.500000")
            pipeline = session.scalar(select(ExtractionRun).where(ExtractionRun.source == "daily-pipeline"))
            assert pipeline.finished_at is not None
        duplicate = daily_ingestion.run_daily_ingestion(factory, now=instant, providers=(_Provider(),))
        assert duplicate["status"] == "already_completed"
        with factory() as session:
            assert session.scalar(select(func.count()).select_from(ExchangeRate)) == 1
            assert session.scalar(select(func.count()).select_from(ExtractionRun).where(ExtractionRun.source == "daily-pipeline")) == 1
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()
