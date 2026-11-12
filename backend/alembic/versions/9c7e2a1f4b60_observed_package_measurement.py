"""Persist explicitly observed package measurements with price history.

Revision ID: 9c7e2a1f4b60
Revises: f41d0c2a9b73
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "9c7e2a1f4b60"
down_revision: Union[str, Sequence[str], None] = "f41d0c2a9b73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # SQLite supports additive column changes directly. Avoid batch mode,
        # which rebuilds and swaps the entire history table.
        op.execute(sa.text(
            "ALTER TABLE price_observations ADD COLUMN observed_package_quantity "
            "NUMERIC(14, 6) CHECK (observed_package_quantity IS NULL OR observed_package_quantity > 0)"
        ))
        op.execute(sa.text("ALTER TABLE price_observations ADD COLUMN observed_package_unit VARCHAR(20)"))
        op.execute(sa.text(
            "ALTER TABLE price_observations ADD COLUMN observed_package_count INTEGER "
            "CHECK (observed_package_count IS NULL OR observed_package_count > 0)"
        ))
        return
    op.add_column("price_observations", sa.Column("observed_package_quantity", sa.Numeric(14, 6), nullable=True))
    op.add_column("price_observations", sa.Column("observed_package_unit", sa.String(20), nullable=True))
    op.add_column("price_observations", sa.Column("observed_package_count", sa.Integer(), nullable=True))
    op.create_check_constraint(
        "ck_price_observations_package_quantity_positive", "price_observations",
        "observed_package_quantity IS NULL OR observed_package_quantity > 0",
    )
    op.create_check_constraint(
        "ck_price_observations_package_count_positive", "price_observations",
        "observed_package_count IS NULL OR observed_package_count > 0",
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        # Downgrade intentionally discards measurements introduced by this
        # revision, while batch mode copies all columns retained by the parent.
        with op.batch_alter_table("price_observations", recreate="always") as batch:
            batch.drop_column("observed_package_count")
            batch.drop_column("observed_package_unit")
            batch.drop_column("observed_package_quantity")
        return
    op.drop_constraint("ck_price_observations_package_count_positive", "price_observations", type_="check")
    op.drop_constraint("ck_price_observations_package_quantity_positive", "price_observations", type_="check")
    op.drop_column("price_observations", "observed_package_count")
    op.drop_column("price_observations", "observed_package_unit")
    op.drop_column("price_observations", "observed_package_quantity")
