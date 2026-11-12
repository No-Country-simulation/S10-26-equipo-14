"""Add optional package measurement metadata to canonical products.

Revision ID: f41d0c2a9b73
Revises: a6f20488d7b1
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f41d0c2a9b73"
down_revision: Union[str, Sequence[str], None] = "a6f20488d7b1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("products", recreate="always") as batch:
            batch.add_column(sa.Column("package_quantity", sa.Numeric(14, 6), nullable=True))
            batch.add_column(sa.Column("package_unit", sa.String(20), nullable=True))
            batch.add_column(sa.Column("package_count", sa.Integer(), nullable=True))
            batch.create_check_constraint(
                "ck_products_package_quantity_positive",
                "package_quantity IS NULL OR (package_quantity > 0 AND package_quantity <= 99999999.999999)",
            )
            batch.create_check_constraint(
                "ck_products_package_count_positive",
                "package_count IS NULL OR (package_count > 0 AND package_count <= 2147483647)",
            )
        return

    op.add_column("products", sa.Column("package_quantity", sa.Numeric(14, 6), nullable=True))
    op.add_column("products", sa.Column("package_unit", sa.String(20), nullable=True))
    op.add_column("products", sa.Column("package_count", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_products_package_quantity_positive",
        "products",
        "package_quantity IS NULL OR (package_quantity > 0 AND package_quantity <= 99999999.999999)",
    )
    op.create_check_constraint(
        "ck_products_package_count_positive",
        "products",
        "package_count IS NULL OR (package_count > 0 AND package_count <= 2147483647)",
    )


def downgrade() -> None:
    # This removes any package metadata collected after upgrade. Back up or
    # export those values before downgrading; the migration cannot restore them.
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("products", recreate="always") as batch:
            batch.drop_constraint("ck_products_package_count_positive", type_="check")
            batch.drop_constraint("ck_products_package_quantity_positive", type_="check")
            batch.drop_column("package_count")
            batch.drop_column("package_unit")
            batch.drop_column("package_quantity")
        return

    op.drop_constraint("ck_products_package_count_positive", "products", type_="check")
    op.drop_constraint("ck_products_package_quantity_positive", "products", type_="check")
    op.drop_column("products", "package_count")
    op.drop_column("products", "package_unit")
    op.drop_column("products", "package_quantity")
