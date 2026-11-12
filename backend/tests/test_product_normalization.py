from decimal import Decimal, getcontext

import pytest

from app.services.product_normalization import calculate_unit_prices, normalize_quantity
from app.models import Product


@pytest.mark.parametrize(
    ("quantity", "unit", "expected_quantity", "expected_unit"),
    [
        ("1", "kg", Decimal("1000"), "g"),
        ("1", "L", Decimal("1000"), "ml"),
        ("250", "g", Decimal("250"), "g"),
        ("330", "ml", Decimal("330"), "ml"),
        ("1", "unidad", Decimal("1"), "unidad"),
    ],
)
def test_normalizes_supported_package_units(quantity, unit, expected_quantity, expected_unit):
    result = normalize_quantity(quantity, unit, 1)

    assert result.available is True
    assert result.total_quantity == expected_quantity
    assert result.unit == expected_unit


def test_multipack_quantity_and_regular_promotional_unit_prices():
    result = calculate_unit_prices(
        package_quantity=Decimal("500"),
        package_unit="ml",
        package_count=6,
        price=Decimal("1500.00"),
        promotional_price=Decimal("1200.00"),
        currency="ars",
    )

    assert result.available is True
    assert result.total_quantity == Decimal("3000")
    assert result.unit == "ml"
    assert result.regular_price_per_unit == Decimal("0.5")
    assert result.promotional_price_per_unit == Decimal("0.4")
    assert result.currency == "ARS"


def test_two_by_one_kilogram_is_two_thousand_grams():
    result = normalize_quantity("1", "kg", 2)
    assert result.available and result.total_quantity == Decimal("2000")


@pytest.mark.parametrize(
    ("kwargs", "reason"),
    [
        ({"package_quantity": "0", "package_unit": "g", "package_count": 1}, "invalid_package_quantity"),
        ({"package_quantity": "-1", "package_unit": "g", "package_count": 1}, "invalid_package_quantity"),
        ({"package_quantity": "1", "package_unit": "g", "package_count": 0}, "invalid_package_count"),
        ({"package_quantity": "1", "package_unit": "g", "package_count": -2}, "invalid_package_count"),
        ({"package_quantity": "1", "package_unit": "oz", "package_count": 1}, "unsupported_package_unit"),
        ({"package_quantity": None, "package_unit": None, "package_count": None}, "missing_package_quantity"),
        ({"package_quantity": "1", "package_unit": None, "package_count": 1}, "missing_package_unit"),
        ({"package_quantity": "1", "package_unit": "g", "package_count": None}, "missing_package_count"),
    ],
)
def test_missing_or_invalid_package_data_is_explicitly_unavailable(kwargs, reason):
    result = calculate_unit_prices(
        **kwargs,
        price="25.00",
        currency="ARS",
    )

    assert result.available is False
    assert result.reason == reason
    assert result.regular_price_per_unit is None


@pytest.mark.parametrize("price", ["1.001", "1000000000000", "-1", "NaN", "Infinity"])
def test_regular_prices_must_fit_numeric_14_2(price):
    result = calculate_unit_prices(
        package_quantity="1", package_unit="g", package_count=1,
        price=price, currency="ARS",
    )
    assert not result.available and result.reason == "invalid_price"


def test_unit_price_rounding_is_independent_of_global_decimal_context():
    prior = getcontext().prec
    try:
        getcontext().prec = 3
        result = calculate_unit_prices(
            package_quantity="3", package_unit="unidad", package_count=1,
            price="10", currency="ARS",
        )
    finally:
        getcontext().prec = prior
    assert result.regular_price_per_unit == Decimal("3.333333333333333333333333333")


@pytest.mark.parametrize("quantity", ["0", "-1", "0.0000001", "100000000", "NaN"])
def test_product_model_rejects_quantity_outside_numeric_14_6(quantity):
    with pytest.raises(ValueError):
        Product(name="Fixture", package_quantity=Decimal(quantity))


@pytest.mark.parametrize("count", [0, -1, 2_147_483_648, True])
def test_product_model_rejects_invalid_package_count(count):
    with pytest.raises(ValueError):
        Product(name="Fixture", package_count=count)


def test_dimensions_must_be_compatible():
    result = calculate_unit_prices(
        package_quantity="1", package_unit="kg", package_count=1,
        price="10", currency="ARS", target_unit="ml",
    )

    assert result.available is False
    assert result.reason == "incompatible_dimensions"


@pytest.mark.parametrize(
    ("price", "currency", "promotional_price", "reason"),
    [
        ("0", "ARS", None, "invalid_price"),
        ("NaN", "ARS", None, "invalid_price"),
        ("10", "XXX", None, "unsupported_currency"),
        ("10", "ARS", "-1", "invalid_promotional_price"),
    ],
)
def test_invalid_price_currency_or_promotion_is_unavailable(price, currency, promotional_price, reason):
    result = calculate_unit_prices(
        package_quantity="1", package_unit="kg", package_count=1,
        price=price, promotional_price=promotional_price, currency=currency,
    )

    if reason == "invalid_promotional_price":
        assert result.available is True
        assert result.regular_price_per_unit == Decimal("0.01")
        assert result.promotional_price_per_unit is None
        assert result.promotional_reason == reason
    else:
        assert result.available is False
        assert result.reason == reason


def test_original_prices_are_not_mutated():
    original = Decimal("19.99")
    promotional = Decimal("17.50")
    calculate_unit_prices(
        package_quantity="500", package_unit="g", package_count=1,
        price=original, promotional_price=promotional, currency="ARS",
    )

    assert original == Decimal("19.99")
    assert promotional == Decimal("17.50")
