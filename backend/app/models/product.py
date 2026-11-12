from decimal import Decimal

from sqlalchemy import BigInteger, CheckConstraint, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from app.db.base import Base
from app.core.decimal_validation import positive_integer, positive_numeric


class Product(Base):
    """Producto canónico usado para comparar publicaciones equivalentes."""

    __tablename__ = "products"
    __table_args__ = (
        UniqueConstraint("barcode", name="uq_products_barcode"),
        CheckConstraint(
            "package_quantity IS NULL OR (package_quantity > 0 AND package_quantity <= 99999999.999999)",
            name="ck_products_package_quantity_positive",
        ),
        CheckConstraint(
            "package_count IS NULL OR (package_count > 0 AND package_count <= 2147483647)",
            name="ck_products_package_count_positive",
        ),
    )

    id: Mapped[int] = mapped_column(BigInteger().with_variant(Integer, "sqlite"), primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False, index=True)
    brand: Mapped[str | None] = mapped_column(String(120))
    model: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    # Kept as text to preserve leading zeroes in EAN/UPC and future identifiers.
    barcode: Mapped[str | None] = mapped_column(String(64))
    # Original quantity and unit for one presentation; count is the number of
    # identical presentations in the sale package. Unknown values stay NULL.
    package_quantity: Mapped[Decimal | None] = mapped_column(Numeric(14, 6))
    package_unit: Mapped[str | None] = mapped_column(String(20))
    package_count: Mapped[int | None] = mapped_column(Integer)

    @validates("package_quantity")
    def validate_package_quantity(self, _key: str, value: Decimal | None) -> Decimal | None:
        return None if value is None else positive_numeric(
            value, precision=14, scale=6, field="package_quantity"
        )

    @validates("package_count")
    def validate_package_count(self, _key: str, value: int | None) -> int | None:
        return None if value is None else positive_integer(
            value, maximum=2_147_483_647, field="package_count"
        )
    category_id: Mapped[int | None] = mapped_column(ForeignKey("categories.id", ondelete="SET NULL"), index=True)
    category: Mapped["Category | None"] = relationship(back_populates="products")
    # Keep publications linked to their canonical product until explicitly relinked.
    store_products: Mapped[list["StoreProduct"]] = relationship(
        back_populates="product",
        passive_deletes="all",
    )
