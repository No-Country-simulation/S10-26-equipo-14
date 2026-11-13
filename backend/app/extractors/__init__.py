"""Tienda-specific adapters for public product pages."""

from app.extractors.base import ExtractionError, ProductSnapshot, StoreExtractor
from app.extractors.fravega import FravegaExtractor
from app.extractors.public_store import PublicStoreExtractor
from app.extractors.verified_stores import (
    CetrogarExtractor,
    CredicoopExtractor,
    OnCityExtractor,
)


def extractor_for_store(store) -> StoreExtractor:
    """Return the single configured adapter that supports ``store``."""
    # Prefer explicit, host-bound adapters; the generic HTML parser remains a
    # diagnostic fallback and is never treated as verified store coverage.
    adapters: tuple[StoreExtractor, ...] = (
        FravegaExtractor(),
        CetrogarExtractor(),
        CredicoopExtractor(),
        OnCityExtractor(),
    )
    matches = [adapter for adapter in adapters if adapter.supports(store)]
    if len(matches) > 1:
        raise ExtractionError(
            f"Hay varios extractores configurados para la tienda {store.name!r}."
        )
    if matches:
        return matches[0]

    fallback = PublicStoreExtractor()
    if fallback.supports(store):
        return fallback
    raise ExtractionError(
        f"No hay un extractor configurado para la tienda {store.name!r}."
    )


__all__ = [
    "ExtractionError",
    "FravegaExtractor",
    "PublicStoreExtractor",
    "CetrogarExtractor",
    "CredicoopExtractor",
    "OnCityExtractor",
    "ProductSnapshot",
    "StoreExtractor",
    "extractor_for_store",
]
