"""Primitivas compartidas para ingestiones; no contienen scraping de sitios."""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from typing import Protocol, Sequence

from sqlalchemy import select
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
    rate_side: str = "reference"


@dataclass(frozen=True)
class RawPrice:
    amount: Decimal
    observed_at: datetime
    currency: str = "ARS"
    source_url: str | None = None
    is_available: bool | None = None
    promotional_price: Decimal | None = None
    observed_package_quantity: Decimal | None = None
    observed_package_unit: str | None = None
    observed_package_count: int | None = None


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
    if quote.rate_side not in {"reference", "buy", "sell"}:
        raise ValueError("rate_side debe ser reference, buy o sell")
    row = ExchangeRate(source=quote.source, rate_type=quote.rate_type, rate_side=quote.rate_side,
        base_currency=quote.base_currency.upper(), quote_currency=quote.quote_currency.upper(),
        rate=normalize_decimal(quote.rate), observed_at=aware_utc(quote.observed_at))
    session.add(row)
    return row


def persist_quotes(session: Session, quotes: Sequence[RawQuote]) -> int:
    """Insert only quote observations not already stored under the unique key."""
    created = 0
    for quote in quotes:
        observed_at = aware_utc(quote.observed_at)
        identity = (
            quote.source,
            quote.rate_type,
            quote.rate_side,
            quote.base_currency.upper(),
            quote.quote_currency.upper(),
            observed_at,
        )
        exists = session.scalar(
            select(ExchangeRate.id).where(
                ExchangeRate.source == identity[0],
                ExchangeRate.rate_type == identity[1],
                ExchangeRate.rate_side == identity[2],
                ExchangeRate.base_currency == identity[3],
                ExchangeRate.quote_currency == identity[4],
                ExchangeRate.observed_at == identity[5],
            )
        )
        if exists is None:
            persist_quote(session, quote)
            created += 1
    session.flush()
    return created


def persist_price(session: Session, store_product_id: int, price: RawPrice) -> PriceObservation:
    promotional_price = (
        normalize_decimal(price.promotional_price)
        if price.promotional_price is not None else None
    )
    row = PriceObservation(
        store_product_id=store_product_id,
        amount=normalize_decimal(price.amount),
        promotional_price=promotional_price,
        observed_package_quantity=price.observed_package_quantity,
        observed_package_unit=price.observed_package_unit,
        observed_package_count=price.observed_package_count,
        currency=price.currency.upper(),
        source_url=price.source_url,
        is_available=price.is_available,
        observed_at=aware_utc(price.observed_at),
    )
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
