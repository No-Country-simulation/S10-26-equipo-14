from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Index, Integer, Numeric, String, Text, UniqueConstraint, event, func
from sqlalchemy.exc import InvalidRequestError
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

from app.db.base import Base


class PriceObservation(Base):
    """Observación inmutable de precio de una publicación."""

    __tablename__ = "price_observations"
    __table_args__ = (
        UniqueConstraint("store_product_id", "observed_at", name="uq_price_observations_product_time"),
        CheckConstraint("amount > 0", name="ck_price_observations_amount_positive"),
        CheckConstraint("promotional_price IS NULL OR promotional_price > 0", name="ck_price_observations_promo_positive"),
        Index("ix_price_observations_product_observed", "store_product_id", "observed_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    store_product_id: Mapped[int] = mapped_column(ForeignKey("store_products.id", ondelete="RESTRICT"), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    promotional_price: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS", server_default="ARS")
    source_url: Mapped[str | None] = mapped_column(Text)
    # NULL means that the source did not provide availability information.
    is_available: Mapped[bool | None] = mapped_column(Boolean)
    observed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    store_product: Mapped["StoreProduct"] = relationship(back_populates="observations")


@event.listens_for(Session, "before_flush")
def prevent_unapproved_price_history_deletion(session, _flush_context, _instances):
    """ORM deletes require a separately reviewed retention procedure."""
    if any(isinstance(instance, PriceObservation) for instance in session.deleted):
        raise InvalidRequestError(
            "Price history cannot be deleted without an approved retention procedure"
        )
