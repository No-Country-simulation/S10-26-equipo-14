"""Shared contract for store product extractors."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.models import Store, StoreProduct


class ExtractionError(RuntimeError):
    """A public product page could not be read or normalized safely."""


@dataclass(frozen=True, slots=True)
class ProductSnapshot:
    """Fields observed on one public listing page; absent values remain null."""

    name: str
    amount: Decimal
    currency: str
    source_url: str
    external_id: str | None = None
    barcode: str | None = None
    brand: str | None = None
    model: str | None = None
    description: str | None = None
    category_name: str | None = None
    is_available: bool | None = None
    promotional_price: Decimal | None = None
    extraction_format: str | None = None


class StoreExtractor(Protocol):
    """Common interface for adapters that read one known store listing."""

    name: str

    def supports(self, store: Store) -> bool: ...

    def prepare(self) -> None:
        """Load access rules and fail closed if they cannot be checked."""

    def extract(self, listing: StoreProduct) -> ProductSnapshot: ...
