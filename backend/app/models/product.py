from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Product(Base):
    """Producto canónico usado para comparar publicaciones equivalentes."""

    __tablename__ = "products"
    __table_args__ = (UniqueConstraint("barcode", name="uq_products_barcode"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    # Kept as text to preserve leading zeroes in EAN/UPC and future identifiers.
    barcode: Mapped[str | None] = mapped_column(String(64))
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    category: Mapped["Category | None"] = relationship(back_populates="products")
    # Keep publications linked to their canonical product until explicitly relinked.
    store_products: Mapped[list["StoreProduct"]] = relationship(
        back_populates="product",
        passive_deletes="all",
    )
