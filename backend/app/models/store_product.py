from sqlalchemy import BigInteger, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class StoreProduct(Base):
    """Publicación de producto en una tienda."""

    __tablename__ = "store_products"
    __table_args__ = (UniqueConstraint("store_id", "external_id", name="uq_store_products_store_external"),)

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    store_id: Mapped[int] = mapped_column(ForeignKey("stores.id", ondelete="RESTRICT"), nullable=False, index=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="RESTRICT"), index=True)
    # Store-assigned taxonomy may differ from the canonical product category.
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("categories.id", ondelete="SET NULL", name="fk_store_products_category_id_categories"),
        index=True,
    )
    external_id: Mapped[str | None] = mapped_column(String(180))
    product_url: Mapped[str] = mapped_column(Text, nullable=False)
    product_name: Mapped[str] = mapped_column(String(300), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS", server_default="ARS")
    store: Mapped["Store"] = relationship(back_populates="products")
    product: Mapped["Product | None"] = relationship(back_populates="store_products")
    category: Mapped["Category | None"] = relationship(back_populates="store_products")
    # Do not let ORM null the non-null FK or delete observations implicitly.
    observations: Mapped[list["PriceObservation"]] = relationship(
        back_populates="store_product",
        passive_deletes="all",
    )
