"""Create initial PriceScope market data schema.

Revision ID: 4db267e3b121
Revises: cb0deba93496
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "4db267e3b121"
down_revision: Union[str, Sequence[str], None] = "cb0deba93496"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table("categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(120), nullable=False), sa.Column("slug", sa.String(140), nullable=False),
        sa.PrimaryKeyConstraint("id"), sa.UniqueConstraint("name", name="uq_categories_name"),
        sa.UniqueConstraint("slug", name="uq_categories_slug"))
    op.create_table("products",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(250), nullable=False), sa.Column("brand", sa.String(120)),
        sa.Column("model", sa.String(120)), sa.Column("description", sa.Text()),
        sa.Column("category_id", sa.BigInteger()), sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_products_name", "products", ["name"])
    op.create_index("ix_products_category_id", "products", ["category_id"])
    op.create_table("store_products",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("store_id", sa.BigInteger(), nullable=False),
        sa.Column("product_id", sa.BigInteger()), sa.Column("external_id", sa.String(180)),
        sa.Column("product_url", sa.Text(), nullable=False), sa.Column("product_name", sa.String(300), nullable=False),
        sa.Column("currency", sa.String(3), server_default="ARS", nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", "external_id", name="uq_store_products_store_external"))
    op.create_index("ix_store_products_store_id", "store_products", ["store_id"])
    op.create_index("ix_store_products_product_id", "store_products", ["product_id"])
    op.create_table("price_observations",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("store_product_id", sa.BigInteger(), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False), sa.Column("currency", sa.String(3), server_default="ARS", nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["store_product_id"], ["store_products.id"], ondelete="CASCADE"), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_product_id", "observed_at", name="uq_price_observations_product_time"),
        sa.CheckConstraint("amount > 0", name="ck_price_observations_amount_positive"))
    op.create_index("ix_price_observations_product_observed", "price_observations", ["store_product_id", "observed_at"])
    op.create_table("exchange_rates",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("source", sa.String(100), nullable=False),
        sa.Column("rate_type", sa.String(30), nullable=False), sa.Column("base_currency", sa.String(3), server_default="USD", nullable=False),
        sa.Column("quote_currency", sa.String(3), server_default="ARS", nullable=False), sa.Column("rate", sa.Numeric(18, 6), nullable=False),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "rate_type", "base_currency", "quote_currency", "observed_at", name="uq_exchange_rates_observation"),
        sa.CheckConstraint("rate > 0", name="ck_exchange_rates_rate_positive"))
    op.create_index("ix_exchange_rates_type_date", "exchange_rates", ["rate_type", "observed_at"])
    op.create_table("extraction_runs",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False), sa.Column("source", sa.String(100), nullable=False),
        sa.Column("status", sa.String(20), nullable=False), sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)), sa.Column("records_seen", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("error_summary", sa.Text()), sa.PrimaryKeyConstraint("id"))
    op.create_index("ix_extraction_runs_source", "extraction_runs", ["source"])


def downgrade() -> None:
    op.drop_index("ix_extraction_runs_source", table_name="extraction_runs")
    op.drop_table("extraction_runs")
    op.drop_index("ix_exchange_rates_type_date", table_name="exchange_rates")
    op.drop_table("exchange_rates")
    op.drop_index("ix_price_observations_product_observed", table_name="price_observations")
    op.drop_table("price_observations")
    op.drop_index("ix_store_products_product_id", table_name="store_products")
    op.drop_index("ix_store_products_store_id", table_name="store_products")
    op.drop_table("store_products")
    op.drop_index("ix_products_category_id", table_name="products")
    op.drop_index("ix_products_name", table_name="products")
    op.drop_table("products")
    op.drop_table("categories")
