"""Add acceptance fields for catalog, price observations, and exchange rates.

Revision ID: d8f31a9c0e42
Revises: 4db267e3b121
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "d8f31a9c0e42"
down_revision: Union[str, Sequence[str], None] = "4db267e3b121"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("products", sa.Column("barcode", sa.String(64), nullable=True))
    op.create_unique_constraint("uq_products_barcode", "products", ["barcode"])

    op.add_column("store_products", sa.Column("category_id", sa.BigInteger(), nullable=True))
    op.create_foreign_key(
        "fk_store_products_category_id_categories",
        "store_products", "categories", ["category_id"], ["id"], ondelete="SET NULL",
    )
    op.create_index("ix_store_products_category_id", "store_products", ["category_id"])

    op.add_column("price_observations", sa.Column("promotional_price", sa.Numeric(14, 2), nullable=True))
    op.add_column("price_observations", sa.Column("source_url", sa.Text(), nullable=True))
    op.add_column("price_observations", sa.Column("is_available", sa.Boolean(), nullable=True))
    op.create_check_constraint(
        "ck_price_observations_promo_positive", "price_observations",
        "promotional_price IS NULL OR promotional_price > 0",
    )

    op.add_column(
        "exchange_rates",
        sa.Column("rate_side", sa.String(10), server_default="reference", nullable=False),
    )
    op.drop_constraint("uq_exchange_rates_observation", "exchange_rates", type_="unique")
    op.create_check_constraint(
        "ck_exchange_rates_rate_side", "exchange_rates",
        "rate_side IN ('reference', 'buy', 'sell')",
    )
    op.create_unique_constraint(
        "uq_exchange_rates_observation", "exchange_rates",
        ["source", "rate_type", "rate_side", "base_currency", "quote_currency", "observed_at"],
    )


def downgrade() -> None:
    has_buy_or_sell = op.get_bind().execute(sa.text(
        "SELECT EXISTS (SELECT 1 FROM exchange_rates WHERE rate_side IN ('buy', 'sell'))"
    )).scalar_one()
    if has_buy_or_sell:
        raise RuntimeError(
            "Cannot downgrade while buy/sell exchange observations exist; "
            "that would erase the distinction between rate sides"
        )

    op.drop_constraint("uq_exchange_rates_observation", "exchange_rates", type_="unique")
    op.drop_constraint("ck_exchange_rates_rate_side", "exchange_rates", type_="check")
    op.create_unique_constraint(
        "uq_exchange_rates_observation", "exchange_rates",
        ["source", "rate_type", "base_currency", "quote_currency", "observed_at"],
    )
    op.drop_column("exchange_rates", "rate_side")

    op.drop_constraint("ck_price_observations_promo_positive", "price_observations", type_="check")
    op.drop_column("price_observations", "is_available")
    op.drop_column("price_observations", "source_url")
    op.drop_column("price_observations", "promotional_price")

    op.drop_index("ix_store_products_category_id", table_name="store_products")
    op.drop_constraint("fk_store_products_category_id_categories", "store_products", type_="foreignkey")
    op.drop_column("store_products", "category_id")

    op.drop_constraint("uq_products_barcode", "products", type_="unique")
    op.drop_column("products", "barcode")
