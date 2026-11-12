"""Conservative quantity and unit-price normalization for product packages."""

from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP, localcontext

from app.core.currency import normalize_currency
from app.core.decimal_validation import positive_integer, positive_numeric

UNIT_PRICE_SIGNIFICANT_DIGITS = 28
UNIT_PRICE_ROUNDING = ROUND_HALF_UP


@dataclass(frozen=True, slots=True)
class _Unit:
    dimension: str
    base_unit: str
    factor: Decimal


_UNIT_ALIASES = {
    "kg": _Unit("mass", "g", Decimal("1000")),
    "kilogramo": _Unit("mass", "g", Decimal("1000")),
    "kilogramos": _Unit("mass", "g", Decimal("1000")),
    "g": _Unit("mass", "g", Decimal("1")),
    "gramo": _Unit("mass", "g", Decimal("1")),
    "gramos": _Unit("mass", "g", Decimal("1")),
    "l": _Unit("volume", "ml", Decimal("1000")),
    "litro": _Unit("volume", "ml", Decimal("1000")),
    "litros": _Unit("volume", "ml", Decimal("1000")),
    "ml": _Unit("volume", "ml", Decimal("1")),
    "mililitro": _Unit("volume", "ml", Decimal("1")),
    "mililitros": _Unit("volume", "ml", Decimal("1")),
    "unidad": _Unit("count", "unidad", Decimal("1")),
    "unidades": _Unit("count", "unidad", Decimal("1")),
    "u": _Unit("count", "unidad", Decimal("1")),
    "ud": _Unit("count", "unidad", Decimal("1")),
}


@dataclass(frozen=True, slots=True)
class QuantityNormalization:
    available: bool
    reason: str | None
    total_quantity: Decimal | None
    unit: str | None
    dimension: str | None


@dataclass(frozen=True, slots=True)
class UnitPriceNormalization:
    available: bool
    reason: str | None
    total_quantity: Decimal | None
    unit: str | None
    regular_price_per_unit: Decimal | None
    promotional_price_per_unit: Decimal | None
    currency: str | None
    promotional_reason: str | None = None


def _unit_for(value: str | None) -> _Unit | None:
    if not value:
        return None
    return _UNIT_ALIASES.get(value.strip().casefold())


def normalize_quantity(
    package_quantity: Decimal | str | int | None,
    package_unit: str | None,
    package_count: int | None,
    *,
    target_unit: str | None = None,
) -> QuantityNormalization:
    """Normalize to a compatible base unit; never infer omitted package data."""
    if package_quantity is None:
        return QuantityNormalization(False, "missing_package_quantity", None, None, None)
    try:
        quantity = positive_numeric(package_quantity, precision=14, scale=6, field="package_quantity")
    except ValueError:
        return QuantityNormalization(False, "invalid_package_quantity", None, None, None)
    if package_unit is None or not package_unit.strip():
        return QuantityNormalization(False, "missing_package_unit", None, None, None)
    source = _unit_for(package_unit)
    if source is None:
        return QuantityNormalization(False, "unsupported_package_unit", None, None, None)
    if package_count is None:
        return QuantityNormalization(False, "missing_package_count", None, None, None)
    try:
        count = positive_integer(package_count, maximum=2_147_483_647, field="package_count")
    except ValueError:
        return QuantityNormalization(False, "invalid_package_count", None, None, None)

    target = _unit_for(target_unit) if target_unit is not None else _Unit(
        source.dimension, source.base_unit, Decimal("1")
    )
    if target_unit is not None and target is None:
        return QuantityNormalization(False, "unsupported_target_unit", None, None, None)
    if target.dimension != source.dimension:
        return QuantityNormalization(False, "incompatible_dimensions", None, None, None)

    with localcontext() as context:
        context.prec = 40
        total = quantity * Decimal(count) * source.factor / target.factor
    unit = target.base_unit if target_unit is None else target_unit.strip().lower()
    return QuantityNormalization(True, None, total, unit, source.dimension)


def calculate_unit_prices(
    *,
    package_quantity: Decimal | str | int | None,
    package_unit: str | None,
    package_count: int | None,
    price: Decimal | str | int | None,
    currency: str | None,
    promotional_price: Decimal | str | int | None = None,
    target_unit: str | None = None,
) -> UnitPriceNormalization:
    """Return per-unit prices at 28 significant digits, ROUND_HALF_UP.

    Stored package and price inputs retain their original precision. The
    normalized result has its own explicit rounding policy and never converts
    currencies. Invalid optional promotion leaves the valid regular result
    available and reports ``promotional_reason``.
    """
    normalized_currency = normalize_currency(currency)
    if normalized_currency is None:
        return UnitPriceNormalization(False, "unsupported_currency", None, None, None, None, None)
    try:
        regular_price = positive_numeric(price, precision=14, scale=2, field="price")
    except ValueError:
        return UnitPriceNormalization(False, "invalid_price", None, None, None, None, normalized_currency)

    promo: Decimal | None = None
    promo_reason: str | None = None
    if promotional_price is not None:
        try:
            promo = positive_numeric(promotional_price, precision=14, scale=2, field="promotional_price")
        except ValueError:
            promo_reason = "invalid_promotional_price"

    quantity = normalize_quantity(package_quantity, package_unit, package_count, target_unit=target_unit)
    if not quantity.available:
        return UnitPriceNormalization(
            False, quantity.reason, None, quantity.unit, None, None,
            normalized_currency, promo_reason,
        )

    assert quantity.total_quantity is not None and quantity.total_quantity > 0
    with localcontext() as context:
        context.prec = UNIT_PRICE_SIGNIFICANT_DIGITS
        context.rounding = UNIT_PRICE_ROUNDING
        regular_result = regular_price / quantity.total_quantity
        promo_result = promo / quantity.total_quantity if promo is not None else None
    return UnitPriceNormalization(
        True, None, quantity.total_quantity, quantity.unit, regular_result,
        promo_result, normalized_currency, promo_reason,
    )
