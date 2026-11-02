"""Primitivas compartidas para ingestiones; no contienen scraping de sitios."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Protocol, Sequence

from sqlalchemy.orm import Session

from app.models import ExchangeRate, ExtractionRun, PriceObservation


@dataclass(frozen=True)
class RawQuote:
    rate: Decimal
    observed_at: datetime
    rate_type: str
    source: str
    base_currency: str = "USD"
    quote_currency: str = "ARS"


@dataclass(frozen=True)
class RawPrice:
    amount: Decimal
    observed_at: datetime
    currency: str = "ARS"


class ExchangeRateProvider(Protocol):
    name: str

    def fetch(self) -> Sequence[RawQuote]: ...


class PriceProvider(Protocol):
    name: str

    def fetch(self) -> Sequence[tuple[int, RawPrice]]: ...


def normalize_decimal(value: Decimal | str | int) -> Decimal:
    try:
        result = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Importe inválido") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError("El importe debe ser decimal, finito y mayor que cero")
    return result


def aware_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("La fecha debe incluir zona horaria")
    return value.astimezone(timezone.utc)


def persist_quote(session: Session, quote: RawQuote) -> ExchangeRate:
    row = ExchangeRate(source=quote.source, rate_type=quote.rate_type,
        base_currency=quote.base_currency.upper(), quote_currency=quote.quote_currency.upper(),
        rate=normalize_decimal(quote.rate), observed_at=aware_utc(quote.observed_at))
    session.add(row)
    return row


def persist_price(session: Session, store_product_id: int, price: RawPrice) -> PriceObservation:
    row = PriceObservation(store_product_id=store_product_id, amount=normalize_decimal(price.amount),
        currency=price.currency.upper(), observed_at=aware_utc(price.observed_at))
    session.add(row)
    return row


def record_run(session: Session, source: str, status: str, records_seen: int,
                started_at: datetime, finished_at: datetime, error_summary: str | None = None) -> ExtractionRun:
    if status not in {"succeeded", "failed", "partial"}:
        raise ValueError("Estado de ejecución inválido")
    row = ExtractionRun(source=source, status=status, records_seen=records_seen,
        started_at=aware_utc(started_at), finished_at=aware_utc(finished_at), error_summary=error_summary)
    session.add(row)
    return row
