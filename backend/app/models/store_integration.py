"""Technical analysis state kept separate from the global store record."""

from datetime import datetime

from sqlalchemy import BigInteger, CheckConstraint, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class StoreIntegration(Base):
    __tablename__ = "store_integrations"
    __table_args__ = (
        UniqueConstraint("store_id", name="uq_store_integrations_store"),
        CheckConstraint("status IN ('pending', 'analyzing', 'configuration_required', 'active', 'error')", name="ck_store_integrations_status"),
    )

    id: Mapped[int] = mapped_column(ID_TYPE, primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("stores.id", name="fk_store_integrations_store_id_stores", ondelete="CASCADE"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending", server_default="pending")
    analyzer_key: Mapped[str | None] = mapped_column(String(80))
    analysis_message: Mapped[str | None] = mapped_column(Text)
    analysis_candidates: Mapped[list[dict[str, object]] | None] = mapped_column(JSON)
    last_analysis_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
