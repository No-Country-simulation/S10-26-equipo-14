"""Store-level monitoring preferences; no user or organization scope yet."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class StoreMonitoringPreference(Base):
    __tablename__ = "store_monitoring_preferences"
    __table_args__ = (
        CheckConstraint("interval_hours BETWEEN 1 AND 720", name="ck_store_monitoring_interval_hours"),
    )

    store_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("stores.id", name="fk_store_monitoring_preferences_store_id_stores", ondelete="CASCADE"), primary_key=True)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS", server_default="ARS")
    interval_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=24, server_default="24")
    is_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    categories: Mapped[list["StoreMonitoringCategory"]] = relationship(
        back_populates="preference", cascade="all, delete-orphan"
    )


class StoreMonitoringCategory(Base):
    __tablename__ = "store_monitoring_categories"

    store_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("store_monitoring_preferences.store_id", name="fk_store_monitoring_categories_store_id_preferences", ondelete="CASCADE"), primary_key=True)
    category_id: Mapped[int] = mapped_column(ID_TYPE, ForeignKey("categories.id", name="fk_store_monitoring_categories_category_id_categories", ondelete="RESTRICT"), primary_key=True)
    preference: Mapped[StoreMonitoringPreference] = relationship(back_populates="categories")
