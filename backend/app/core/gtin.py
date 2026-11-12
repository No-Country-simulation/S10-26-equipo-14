"""GTIN format and check-digit validation; identifiers stay strings."""

_SUPPORTED_LENGTHS = frozenset({8, 12, 13, 14})


def is_valid_gtin(value: str | None) -> bool:
    """Validate GTIN-8/12/13/14 length, ASCII digits, and modulo-10 check digit.

    A valid check digit detects transcription errors; it does not establish that
    the code belongs to a particular product. Product association still needs
    trusted source or operator evidence.
    """
    if not isinstance(value, str) or len(value) not in _SUPPORTED_LENGTHS:
        return False
    if not value.isascii() or not value.isdigit():
        return False

    payload = value[:-1]
    weighted_sum = sum(
        int(digit) * (3 if index % 2 == 0 else 1)
        for index, digit in enumerate(reversed(payload))
    )
    expected_check_digit = (10 - weighted_sum % 10) % 10
    return expected_check_digit == int(value[-1])
