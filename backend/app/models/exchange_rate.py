from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ExchangeRate(Base):
    """Cotización con moneda base, cotizada y fuente identificable."""

    __tablename__ = "exchange_rates"
    __table_args__ = (
        UniqueConstraint("source", "rate_type", "base_currency", "quote_currency", "observed_at", name="uq_exchange_rates_observation"),
        CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"),
        Index("ix_exchange_rates_type_date", "rate_type", "observed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    rate_type: Mapped[str] = mapped_column(String(30), nullable=False)
    base_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="USD", server_default="USD")
    quote_currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS", server_default="ARS")
    rate: Mapped[Decimal] = mapped_column(Numeric(18, 6), nullable=False)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
