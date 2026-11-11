"""Tienda-specific adapters for public product pages."""

from app.extractors.base import ExtractionError, ProductSnapshot, StoreExtractor
from app.extractors.fravega import FravegaExtractor
from app.extractors.public_store import PublicStoreExtractor


def extractor_for_store(store) -> StoreExtractor:
    """Return the single configured adapter that supports ``store``."""
    # Keep the provider-specific adapter first; all other registered public
    # HTTPS hosts use the shared evidence-based HTML strategies.
    adapters: tuple[StoreExtractor, ...] = (FravegaExtractor(), PublicStoreExtractor())
    matches = [adapter for adapter in adapters if adapter.supports(store)]
    if not matches:
        raise ExtractionError(
            f"No hay un extractor configurado para la tienda {store.name!r}."
        )
    if len(matches) > 1:
        raise ExtractionError(
            f"Hay varios extractores configurados para la tienda {store.name!r}."
        )
    return matches[0]


__all__ = [
    "ExtractionError",
    "FravegaExtractor",
    "PublicStoreExtractor",
    "ProductSnapshot",
    "StoreExtractor",
    "extractor_for_store",
]
