"""Currency validation shared by ingestion and price calculations."""

SUPPORTED_ISO_CURRENCIES = frozenset(
    "ARS USD BRL CLP UYU BOB PYG COP MXN PEN EUR GBP JPY CNY CAD AUD CHF "
    "INR KRW NZD ZAR SEK NOK DKK PLN CZK HUF TRY ILS AED SAR TWD HKD SGD "
    "IDR THB VND".split()
)


def normalize_currency(value: str | None) -> str | None:
    if not value:
        return None
    normalized = value.strip().upper()
    return normalized if normalized in SUPPORTED_ISO_CURRENCIES else None


def is_supported_iso_currency(value: str | None) -> bool:
    return normalize_currency(value) is not None
