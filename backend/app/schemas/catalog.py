from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


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


class ProductPageOut(BaseModel):
    items: list[ProductOut]
    total: int
    limit: int
    offset: int


class StoreProductCreate(BaseModel):
    store_id: int
    product_id: int | None = None
    category_id: int | None = None
    external_id: str | None = Field(default=None, max_length=180)
    product_url: HttpUrl
    product_name: str = Field(min_length=1, max_length=300)
    currency: str = Field(default="ARS", min_length=3, max_length=3)


class StoreProductOut(ReadModel):
    id: int
    store_id: int
    product_id: int | None
    category_id: int | None
    external_id: str | None
    product_url: str
    product_name: str
    currency: str
