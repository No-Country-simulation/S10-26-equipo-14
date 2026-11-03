from datetime import datetime

from pydantic import BaseModel, Field, HttpUrl

from app.schemas.common import ReadModel


# ---------- Stores ----------

class StoreCreate(BaseModel):
    name: str = Field(min_length=1, max_length=150)
    base_url: HttpUrl
    country: str | None = Field(default=None, max_length=100)
    is_active: bool = True


class StoreOut(ReadModel):
    id: int
    name: str
    base_url: str
    country: str | None
    is_active: bool
    created_at: datetime


# ---------- Categories ----------

class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    slug: str = Field(min_length=1, max_length=140)


class CategoryOut(ReadModel):
    id: int
    name: str
    slug: str


# ---------- Products ----------

class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=250)
    brand: str | None = Field(default=None, max_length=120)
    model: str | None = Field(default=None, max_length=120)
    description: str | None = None
    barcode: str | None = Field(default=None, max_length=64)
    category_id: int | None = None


class ProductOut(ReadModel):
    id: int
    name: str
    brand: str | None
    model: str | None
    description: str | None
    barcode: str | None
    category_id: int | None


# ---------- Store products (publications) ----------

class StoreProductCreate(BaseModel):
    store_id: int
    product_id: int | None = None
    category_id: int | None = None
    external_id: str | None = Field(default=None, max_length=180)
    product_url: HttpUrl
    product_name: str = Field(min_length=1, max_length=300)
    currency: str = Field(default="ARS", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")


class StoreProductOut(ReadModel):
    id: int
    store_id: int
    product_id: int | None
    category_id: int | None
    external_id: str | None
    product_url: str
    product_name: str
    currency: str
