from datetime import datetime, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import (
    CategoryCreate,
    ExchangeRateCreate,
    PriceObservationCreate,
    ProductCreate,
    StoreCreate,
    StoreProductCreate,
)
from app.schemas.catalog import StoreOut, StoreProductOut
from app.schemas.market import PriceObservationOut, ExchangeRateOut


# ---------- Store ----------

def test_store_create_valid():
    s = StoreCreate(name="Tienda", base_url="https://example.com", country="AR")
    assert s.name == "Tienda"
    assert str(s.base_url) == "https://example.com/"


def test_store_create_invalid_missing_name():
    with pytest.raises(ValidationError):
        StoreCreate(base_url="https://example.com")


def test_store_create_invalid_url():
    with pytest.raises(ValidationError):
        StoreCreate(name="Tienda", base_url="not-a-url")


# ---------- Category ----------

def test_category_create_valid():
    c = CategoryCreate(name="Hogar", slug="hogar")
    assert c.slug == "hogar"


def test_category_create_invalid_empty_name():
    with pytest.raises(ValidationError):
        CategoryCreate(name="", slug="hogar")


# ---------- Product ----------

def test_product_create_valid_minimal():
    p = ProductCreate(name="Producto")
    assert p.brand is None
    assert p.category_id is None


def test_product_create_invalid_name_too_long():
    with pytest.raises(ValidationError):
        ProductCreate(name="x" * 251)


# ---------- StoreProduct ----------

def test_store_product_create_valid():
    sp = StoreProductCreate(
        store_id=1,
        product_url="https://example.com/item",
        product_name="Articulo",
    )
    assert sp.currency == "ARS"


def test_store_product_create_invalid_currency_length():
    with pytest.raises(ValidationError):
        StoreProductCreate(
            store_id=1,
            product_url="https://example.com/item",
            product_name="Articulo",
            currency="AR",
        )


def test_store_product_create_invalid_currency_lowercase():
    with pytest.raises(ValidationError):
        StoreProductCreate(
            store_id=1,
            product_url="https://example.com/item",
            product_name="Articulo",
            currency="ars",
        )


def test_store_product_create_invalid_missing_url():
    with pytest.raises(ValidationError):
        StoreProductCreate(store_id=1, product_name="Articulo")


# ---------- PriceObservation ----------

def test_price_observation_create_valid():
    po = PriceObservationCreate(
        store_product_id=1,
        amount="1234567890.12",
        promotional_price="1199999999.99",
        currency="ARS",
        source_url="https://example.com/item",
        is_available=False,
        observed_at="2026-11-01T10:00:00-03:00",
    )
    assert po.amount == Decimal("1234567890.12")
    assert po.promotional_price == Decimal("1199999999.99")
    assert isinstance(po.amount, Decimal)


def test_price_observation_create_invalid_amount_zero():
    with pytest.raises(ValidationError):
        PriceObservationCreate(
            store_product_id=1,
            amount="0",
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )


def test_price_observation_create_invalid_amount_negative():
    with pytest.raises(ValidationError):
        PriceObservationCreate(
            store_product_id=1,
            amount="-5",
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )


def test_price_observation_create_invalid_promotional_price_negative():
    with pytest.raises(ValidationError):
        PriceObservationCreate(
            store_product_id=1,
            amount="10",
            promotional_price="-1",
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )


def test_price_observation_create_invalid_observed_at():
    with pytest.raises(ValidationError):
        PriceObservationCreate(
            store_product_id=1,
            amount="10",
            observed_at="not-a-date",
        )


def test_price_observation_create_missing_required():
    with pytest.raises(ValidationError):
        PriceObservationCreate(store_product_id=1, amount="10")


# ---------- ExchangeRate ----------

def test_exchange_rate_create_valid():
    er = ExchangeRateCreate(
        source="Proveedor",
        rate_type="blue",
        rate_side="buy",
        base_currency="USD",
        quote_currency="ARS",
        rate="1400.123456",
        observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    assert er.rate == Decimal("1400.123456")


def test_exchange_rate_create_invalid_rate_zero():
    with pytest.raises(ValidationError):
        ExchangeRateCreate(
            source="Proveedor",
            rate_type="blue",
            rate="0",
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )


def test_exchange_rate_create_invalid_rate_side():
    with pytest.raises(ValidationError):
        ExchangeRateCreate(
            source="Proveedor",
            rate_type="blue",
            rate_side="middle",
            rate="10",
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )


def test_exchange_rate_create_invalid_currency():
    with pytest.raises(ValidationError):
        ExchangeRateCreate(
            source="Proveedor",
            rate_type="blue",
            base_currency="US",
            rate="10",
            observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
        )


# ---------- Response schemas: no internal fields / decimal as string ----------

def test_store_out_serializes_created_at_and_no_input_only_fields():
    out = StoreOut(
        id=1,
        name="Tienda",
        base_url="https://example.com",
        country=None,
        is_active=True,
        created_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    data = out.model_dump()
    assert "id" in data
    assert "created_at" in data
    # Create-only fields must not leak
    assert "base_url" in data


def test_price_observation_out_decimal_stays_decimal():
    out = PriceObservationOut(
        id=1,
        store_product_id=2,
        amount=Decimal("123.45"),
        promotional_price=None,
        currency="ARS",
        source_url=None,
        is_available=None,
        observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    assert out.amount == Decimal("123.45")
    import json
    parsed = json.loads(out.model_dump_json())
    assert parsed["amount"] == "123.45"


def test_store_create_rejects_internal_fields():
    # Create schema must not carry internal fields like id/created_at.
    s = StoreCreate(name="Tienda", base_url="https://example.com")
    dumped = s.model_dump()
    assert "id" not in dumped
    assert "created_at" not in dumped


def test_store_product_out_no_internal_extra():
    out = StoreProductOut(
        id=1,
        store_id=2,
        product_id=None,
        category_id=None,
        external_id=None,
        product_url="https://example.com/item",
        product_name="Articulo",
        currency="ARS",
    )
    assert "product_url" in out.model_dump()
    assert "currency" in out.model_dump()


def test_exchange_rate_out_serializes_rate_as_string():
    out = ExchangeRateOut(
        id=1,
        source="Proveedor",
        rate_type="blue",
        rate_side="buy",
        base_currency="USD",
        quote_currency="ARS",
        rate=Decimal("1400.123456"),
        observed_at=datetime(2026, 11, 1, tzinfo=timezone.utc),
    )
    import json
    parsed = json.loads(out.model_dump_json())
    assert parsed["rate"] == "1400.123456"
