from datetime import datetime

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

ID_TYPE = BigInteger().with_variant(Integer, "sqlite")


class ExtractionRun(Base):
    """Auditoría de una ejecución de un conector de datos."""

    __tablename__ = "extraction_runs"

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    source: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    store_id: Mapped[int | None] = mapped_column(ID_TYPE, ForeignKey("stores.id", name="fk_extraction_runs_store_id_stores", ondelete="SET NULL"), index=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    records_seen: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0, server_default="0")
    error_summary: Mapped[str | None] = mapped_column(Text)
