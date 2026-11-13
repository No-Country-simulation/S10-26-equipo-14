from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.db.base import Base
import app.models  # noqa: F401 - register all mapped tables
from app.models import ExchangeRate
from app.services.exchange_rate_providers import BcraOfficialProvider, DolarApiBlueProvider, MonedApiProvider
from app.services.ingestion import persist_quotes


def test_bcra_provider_uses_current_official_usd_ars_quote():
    provider = BcraOfficialProvider(get_json=lambda _url: {
        "status": 200,
        "results": {"fecha": "2026-11-12", "detalle": [
            {"codigoMoneda": "USD", "tipoCotizacion": 1412.25},
            {"codigoMoneda": "EUR", "tipoCotizacion": 1600},
        ]},
    })
    quote, = provider.fetch()
    assert quote.rate == Decimal("1412.25")
    assert quote.rate_type == "official"
    assert quote.rate_side == "reference"
    assert quote.source == "BCRA Estadísticas Cambiarias"
    assert quote.observed_at == datetime(2026, 11, 12, tzinfo=timezone.utc)


def test_parallel_provider_preserves_buy_sell_and_published_timestamp():
    provider = DolarApiBlueProvider(get_json=lambda _url: {
        "compra": 1395,
        "venta": 1415.5,
        "fechaActualizacion": "2026-11-12T14:30:00-03:00",
    })
    buy, sell = provider.fetch()
    assert (buy.rate, buy.rate_side) == (Decimal("1395"), "buy")
    assert (sell.rate, sell.rate_side) == (Decimal("1415.5"), "sell")
    assert buy.rate_type == sell.rate_type == "parallel"
    assert buy.observed_at == sell.observed_at == datetime(2026, 11, 12, 17, 30, tzinfo=timezone.utc)


def test_persist_quotes_is_idempotent_and_keeps_source_and_type():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    try:
        provider = DolarApiBlueProvider(get_json=lambda _url: {
            "compra": 1395,
            "venta": 1415,
            "fechaActualizacion": "2026-11-12T14:30:00-03:00",
        })
        quotes = provider.fetch()
        with Session(engine) as session, session.begin():
            assert persist_quotes(session, quotes) == 2
        with Session(engine) as session, session.begin():
            assert persist_quotes(session, quotes) == 0
            assert session.scalar(select(func.count()).select_from(ExchangeRate)) == 2
            records = session.scalars(select(ExchangeRate).order_by(ExchangeRate.rate_side)).all()
            assert {row.source for row in records} == {"DolarApi"}
            assert {row.rate_type for row in records} == {"parallel"}
            assert {row.rate_side for row in records} == {"buy", "sell"}
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()



def test_monedapi_official_provider_maps_sell_to_reference_and_uses_confirmation_time():
    provider = MonedApiProvider("official", get_json=lambda _url: {
        "buy": 1400,
        "sell": 1420.5,
        "updatedAt": "2026-11-12T14:25:00.000-03:00",
        "lastScrapedAt": "2026-11-12T14:30:00.000-03:00",
    })
    quote, = provider.fetch()
    assert quote.rate == Decimal("1420.5")
    assert quote.rate_type == "official"
    assert quote.rate_side == "reference"
    assert quote.source == "MonedAPI"
    assert quote.observed_at == datetime(2026, 11, 12, 17, 30, tzinfo=timezone.utc)


def test_monedapi_parallel_provider_preserves_buy_and_sell():
    provider = MonedApiProvider("parallel", get_json=lambda _url: {
        "buy": 1395.25,
        "sell": 1415.75,
        "updatedAt": "2026-11-12T14:25:00.000-03:00",
        "lastScrapedAt": "2026-11-12T14:30:00.000-03:00",
    })
    buy, sell = provider.fetch()
    assert (buy.rate, buy.rate_side) == (Decimal("1395.25"), "buy")
    assert (sell.rate, sell.rate_side) == (Decimal("1415.75"), "sell")
    assert buy.rate_type == sell.rate_type == "parallel"
    assert buy.source == sell.source == "MonedAPI"
    assert buy.observed_at == sell.observed_at == datetime(2026, 11, 12, 17, 30, tzinfo=timezone.utc)


def test_monedapi_provider_rejects_unknown_series():
    import pytest

    with pytest.raises(ValueError, match="official or parallel"):
        MonedApiProvider("blue")
