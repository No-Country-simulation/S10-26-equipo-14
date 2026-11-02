from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PriceObservation(Base):
    """Observación inmutable de precio de una publicación."""

    __tablename__ = "price_observations"
    __table_args__ = (
        UniqueConstraint("store_product_id", "observed_at", name="uq_price_observations_product_time"),
        CheckConstraint("amount > 0", name="ck_price_observations_amount_positive"),
        Index("ix_price_observations_product_observed", "store_product_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    store_product_id: Mapped[int] = mapped_column(ForeignKey("store_products.id", ondelete="CASCADE"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS", server_default="ARS")
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    store_product: Mapped["StoreProduct"] = relationship(back_populates="observations")
