from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class PriceObservationCreate(BaseModel):
    store_product_id: int
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="ARS", min_length=3, max_length=3)
    observed_at: datetime


class PriceObservationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    store_product_id: int
    amount: Decimal
    currency: str
    observed_at: datetime


class ExchangeRateOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    rate_type: str
    base_currency: str
    quote_currency: str
    rate: Decimal
    observed_at: datetime
