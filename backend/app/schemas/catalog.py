from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator

from app.core.currency import normalize_currency


class ReadModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class StoreOut(ReadModel):
    id: int
    name: str
    base_url: str
    country: str | None
    is_active: bool
    created_at: datetime


class CategoryOut(ReadModel):
    id: int
    name: str
    slug: str


class ProductOut(ReadModel):
    id: int
    name: str
    brand: str | None
    model: str | None
    description: str | None
    barcode: str | None
    category_id: int | None
    package_quantity: Decimal | None = None
    package_unit: str | None = None
    package_count: int | None = None
    normalized_quantity: Decimal | None = None
    normalized_unit: str | None = None
    normalization_unavailable_reason: str | None = None


class ProductPageOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int


class LatestProductPriceOut(BaseModel):
    amount: str
    promotional_price: str | None = None
    currency: str
    observed_at: datetime
    store_id: int
    store_name: str
    store_product_id: int
    source_url: str | None
    is_available: bool | None
    normalized_quantity: Decimal | None = None
    normalized_unit: str | None = None
    normalized_price: Decimal | None = None
    normalized_promotional_price: Decimal | None = None
    normalization_unavailable_reason: str | None = None
    promotional_normalization_unavailable_reason: str | None = None


class PricedProductOut(ProductOut):
    latest_price: LatestProductPriceOut | None


class PricedProductPageOut(BaseModel):
    items: list[PricedProductOut]
    total: int
    limit: int
    offset: int
    verified_only: bool = False


class StoreProductCreate(BaseModel):
    store_id: int
    product_id: int | None = None
    category_id: int | None = None
    external_id: str | None = Field(default=None, max_length=180)
    product_url: HttpUrl
    product_name: str = Field(min_length=1, max_length=300)
    currency: str = Field(default="ARS", min_length=3, max_length=3)


class ManagedStoreProductCreate(BaseModel):
    product_url: HttpUrl
    product_name: str = Field(min_length=1, max_length=300)
    currency: str = Field(default="ARS", min_length=3, max_length=3)
    external_id: str | None = Field(default=None, max_length=180)
    product_id: int | None = Field(default=None, gt=0)
    category_id: int | None = Field(default=None, gt=0)

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, value: str) -> str:
        normalized = normalize_currency(value)
        if normalized is None:
            raise ValueError("La moneda debe ser un código ISO 4217 admitido.")
        return normalized

    @field_validator("product_name")
    @classmethod
    def trim_product_name(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El nombre de la publicación no puede estar vacío.")
        return value


class StoreProductOut(ReadModel):
    id: int
    store_id: int
    product_id: int | None
    category_id: int | None
    external_id: str | None
    product_url: str
    product_name: str
    currency: str
    package_quantity: Decimal | None = None
    package_unit: str | None = None
    package_count: int | None = None
    normalized_quantity: Decimal | None = None
    normalized_unit: str | None = None
    normalization_unavailable_reason: str | None = None
