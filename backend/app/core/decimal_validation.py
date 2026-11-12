"""Exact positive Decimal validation for persisted SQL NUMERIC columns."""

from decimal import Decimal, InvalidOperation, localcontext


def positive_numeric(
    value: Decimal | str | int,
    *,
    precision: int,
    scale: int,
    field: str,
) -> Decimal:
    """Validate a positive finite number without scale or range rounding."""
    if isinstance(value, (bool, float)):
        raise ValueError(f"{field} debe expresarse como Decimal, texto o entero exacto.")
    try:
        parsed = value if isinstance(value, Decimal) else Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} no es un decimal válido.") from exc
    if not parsed.is_finite() or parsed <= 0:
        raise ValueError(f"{field} debe ser finito y mayor que cero.")

    integer_digits = max(parsed.adjusted() + 1, 0)
    if integer_digits > precision - scale:
        raise ValueError(f"{field} excede el rango NUMERIC({precision},{scale}).")

    digits = parsed.as_tuple().digits
    exponent = parsed.as_tuple().exponent
    trailing_zeroes = 0
    for digit in reversed(digits):
        if digit != 0:
            break
        trailing_zeroes += 1
    meaningful_scale = max(0, -exponent - trailing_zeroes)
    if meaningful_scale > scale:
        raise ValueError(f"{field} excede la escala de {scale} decimales.")

    # A final exact equality check also guards unusual Decimal exponents; the
    # roomy local context avoids borrowing the caller's Decimal precision.
    quantum = Decimal(1).scaleb(-scale)
    try:
        with localcontext() as context:
            context.prec = max(precision + 4, 40)
            if parsed.quantize(quantum) != parsed:
                raise ValueError(f"{field} excede la escala de {scale} decimales.")
    except InvalidOperation as exc:
        raise ValueError(f"{field} excede el rango NUMERIC({precision},{scale}).") from exc
    return parsed


def positive_integer(value: int, *, maximum: int, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not 0 < value <= maximum:
        raise ValueError(f"{field} debe ser un entero positivo no mayor que {maximum}.")
    return value
