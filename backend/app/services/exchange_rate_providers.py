"""Explicit, bounded providers for official and parallel USD/ARS quotes."""

from __future__ import annotations

import json
from datetime import date, datetime, time, timezone
from decimal import Decimal, InvalidOperation
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.services.ingestion import RawQuote

_USER_AGENT = "PriceScope/0.1 (public exchange-rate ingestion)"
_MAX_RESPONSE_BYTES = 1_000_000


def _read_json(url: str, *, timeout_seconds: float = 10) -> object:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": _USER_AGENT})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            if response.status != 200:
                raise ValueError(f"Quote provider returned HTTP {response.status}.")
            content_type = response.headers.get_content_type()
            if content_type != "application/json":
                raise ValueError("Quote provider returned a non-JSON response.")
            body = response.read(_MAX_RESPONSE_BYTES + 1)
    except (URLError, TimeoutError, OSError) as exc:
        raise RuntimeError("Could not fetch the public exchange-rate source.") from exc
    if len(body) > _MAX_RESPONSE_BYTES:
        raise ValueError("Exchange-rate response exceeded the local size limit.")
    return json.loads(body)


def _decimal(value: object) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError("Quote provider returned an invalid rate.") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError("Quote provider returned a non-positive rate.")
    return result


class BcraOfficialProvider:
    """Official minorista USD selling quote published by the BCRA API."""

    name = "BCRA Principales Variables"
    url = "https://api.bcra.gob.ar/estadisticas/v2.0/principalesvariables"

    def __init__(self, get_json=None) -> None:
        self._get_json = get_json or _read_json

    def fetch(self) -> tuple[RawQuote, ...]:
        payload = self._get_json(self.url)
        if not isinstance(payload, dict) or payload.get("status") != 200:
            raise ValueError("BCRA returned an unexpected response.")
        rows = payload.get("results")
        if not isinstance(rows, list):
            raise ValueError("BCRA response is missing results.")
        candidates = [
            row for row in rows
            if isinstance(row, dict)
            and row.get("idVariable") == 4
            and "Tipo de Cambio Minorista" in str(row.get("descripcion", ""))
            and "vendedor" in str(row.get("descripcion", "")).casefold()
        ]
        if not candidates:
            raise ValueError("BCRA response has no official minorista selling rate (variable 4).")
        row = max(candidates, key=lambda item: str(item.get("fecha", "")))
        observed_day = date.fromisoformat(str(row["fecha"]))
        observed_at = datetime.combine(observed_day, time.min, tzinfo=timezone.utc)
        return (RawQuote(
            rate=_decimal(row.get("valor")),
            observed_at=observed_at,
            rate_type="official",
            rate_side="reference",
            source=self.name,
        ),)


class DolarApiBlueProvider:
    """Parallel blue-market USD buy/sell quotes with source update timestamp."""

    name = "DolarApi"
    url = "https://dolarapi.com/v1/dolares/blue"

    def __init__(self, get_json=None) -> None:
        self._get_json = get_json or _read_json

    def fetch(self) -> tuple[RawQuote, ...]:
        payload = self._get_json(self.url)
        if not isinstance(payload, dict):
            raise ValueError("DolarApi returned an unexpected response.")
        observed_at = datetime.fromisoformat(str(payload["fechaActualizacion"]).replace("Z", "+00:00"))
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("DolarApi update timestamp must include a timezone.")
        observed_at = observed_at.astimezone(timezone.utc)
        return tuple(
            RawQuote(
                rate=_decimal(payload[field]),
                observed_at=observed_at,
                rate_type="parallel",
                rate_side=side,
                source=self.name,
            )
            for field, side in (("compra", "buy"), ("venta", "sell"))
        )


class MonedApiProvider:
    """Fetch real USD/ARS official or blue quotes from MonedAPI."""

    name = "MonedAPI"

    def __init__(self, rate_type: str, get_json=None) -> None:
        if rate_type not in {"official", "parallel"}:
            raise ValueError("rate_type must be official or parallel")
        self.rate_type = rate_type
        self.origin = "oficial" if rate_type == "official" else "blue"
        self._get_json = get_json or _read_json

    def fetch(self) -> tuple[RawQuote, ...]:
        payload = self._get_json(f"https://monedapi.ar/api/v2/usd/{self.origin}")
        if not isinstance(payload, dict):
            raise ValueError("MonedAPI returned an unexpected response.")
        timestamp = payload.get("lastScrapedAt")
        if not isinstance(timestamp, str):
            raise ValueError("MonedAPI response is missing lastScrapedAt.")
        observed_at = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        if observed_at.tzinfo is None or observed_at.utcoffset() is None:
            raise ValueError("MonedAPI timestamp must include a timezone.")
        observed_at = observed_at.astimezone(timezone.utc)

        if self.rate_type == "official":
            return (RawQuote(
                rate=_decimal(payload.get("sell")),
                observed_at=observed_at,
                rate_type="official",
                rate_side="reference",
                source=self.name,
            ),)

        return tuple(
            RawQuote(
                rate=_decimal(payload.get(field)),
                observed_at=observed_at,
                rate_type="parallel",
                rate_side=side,
                source=self.name,
            )
            for field, side in (("buy", "buy"), ("sell", "sell"))
        )
