from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import ReadModel


# ---------- Price observations ----------

class PriceObservationCreate(BaseModel):
    store_product_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    promotional_price: Decimal | None = Field(default=None, gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="ARS", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    source_url: str | None = None
    is_available: bool | None = None
    observed_at: datetime


class PriceObservationOut(ReadModel):
    id: int
    store_product_id: int
    amount: Decimal
    promotional_price: Decimal | None
    currency: str
    source_url: str | None
    is_available: bool | None
    observed_at: datetime


# ---------- Exchange rates ----------

class ExchangeRateCreate(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    rate_type: str = Field(min_length=1, max_length=30)
    rate_side: str = Field(default="reference", pattern=r"^(reference|buy|sell)$")
    base_currency: str = Field(default="USD", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    quote_currency: str = Field(default="ARS", min_length=3, max_length=3, pattern=r"^[A-Z]{3}$")
    rate: Decimal = Field(gt=0, max_digits=18, decimal_places=6)
    observed_at: datetime


class ExchangeRateOut(ReadModel):
    id: int
    source: str
    rate_type: str
    rate_side: str
    base_currency: str
    quote_currency: str
    rate: Decimal
    observed_at: datetime
