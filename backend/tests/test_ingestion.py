from datetime import datetime, timezone
from decimal import Decimal

import pytest

from app.services.ingestion import RawPrice, aware_utc, normalize_decimal


def test_normalizes_decimal_and_rejects_nonpositive_values():
    assert normalize_decimal("123.450") == Decimal("123.450")
    with pytest.raises(ValueError):
        normalize_decimal("NaN")
    with pytest.raises(ValueError):
        normalize_decimal("0")


def test_requires_timezone_and_normalizes_to_utc():
    with pytest.raises(ValueError):
        aware_utc(datetime(2026, 1, 1))
    result = aware_utc(datetime.fromisoformat("2026-01-01T10:00:00-03:00"))
    assert result == datetime(2026, 1, 1, 13, tzinfo=timezone.utc)


def test_raw_price_is_source_neutral():
    record = RawPrice(Decimal("12.30"), datetime(2026, 1, 1, tzinfo=timezone.utc))
    assert record.currency == "ARS"
    assert record.amount == Decimal("12.30")
