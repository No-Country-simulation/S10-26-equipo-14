"""Add local store analysis and monitoring preferences.

Revision ID: a6f20488d7b1
Revises: d8f31a9c0e42
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "a6f20488d7b1"
down_revision: Union[str, Sequence[str], None] = "d8f31a9c0e42"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ID_TYPE = sa.BigInteger().with_variant(sa.Integer(), "sqlite")


def _timestamp_default():
    return sa.text("CURRENT_TIMESTAMP") if op.get_bind().dialect.name == "sqlite" else sa.func.now()


def upgrade() -> None:
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("extraction_runs", recreate="always") as batch:
            batch.add_column(sa.Column("store_id", ID_TYPE, nullable=True))
            batch.create_foreign_key(
                "fk_extraction_runs_store_id_stores", "stores", ["store_id"], ["id"], ondelete="SET NULL"
            )
            batch.create_index("ix_extraction_runs_store_id", ["store_id"])
    else:
        op.add_column("extraction_runs", sa.Column("store_id", ID_TYPE, nullable=True))
        op.create_foreign_key(
            "fk_extraction_runs_store_id_stores",
            "extraction_runs", "stores", ["store_id"], ["id"], ondelete="SET NULL",
        )
        op.create_index("ix_extraction_runs_store_id", "extraction_runs", ["store_id"])

    op.create_table(
        "store_integrations",
        sa.Column("id", ID_TYPE, nullable=False),
        sa.Column("store_id", ID_TYPE, nullable=False),
        sa.Column("status", sa.String(32), server_default="pending", nullable=False),
        sa.Column("analyzer_key", sa.String(80)),
        sa.Column("analysis_message", sa.Text()),
        sa.Column("analysis_candidates", sa.JSON()),
        sa.Column("last_analysis_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_timestamp_default(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_timestamp_default(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], name="fk_store_integrations_store_id_stores", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("store_id", name="uq_store_integrations_store"),
        sa.CheckConstraint(
            "status IN ('pending', 'analyzing', 'configuration_required', 'active', 'error')",
            name="ck_store_integrations_status",
        ),
    )
    op.create_index("ix_store_integrations_store_id", "store_integrations", ["store_id"])

    op.create_table(
        "store_monitoring_preferences",
        sa.Column("store_id", ID_TYPE, nullable=False),
        sa.Column("currency", sa.String(3), server_default="ARS", nullable=False),
        sa.Column("interval_hours", sa.Integer(), server_default="24", nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=_timestamp_default(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=_timestamp_default(), nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["stores.id"], name="fk_store_monitoring_preferences_store_id_stores", ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("store_id"),
        sa.CheckConstraint("interval_hours BETWEEN 1 AND 720", name="ck_store_monitoring_interval_hours"),
    )

    op.create_table(
        "store_monitoring_categories",
        sa.Column("store_id", ID_TYPE, nullable=False),
        sa.Column("category_id", ID_TYPE, nullable=False),
        sa.ForeignKeyConstraint(["store_id"], ["store_monitoring_preferences.store_id"], name="fk_store_monitoring_categories_store_id_preferences", ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], name="fk_store_monitoring_categories_category_id_categories", ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("store_id", "category_id"),
    )


def downgrade() -> None:
    op.drop_table("store_monitoring_categories")
    op.drop_table("store_monitoring_preferences")
    op.drop_index("ix_store_integrations_store_id", table_name="store_integrations")
    op.drop_table("store_integrations")
    if op.get_bind().dialect.name == "sqlite":
        with op.batch_alter_table("extraction_runs", recreate="always") as batch:
            batch.drop_index("ix_extraction_runs_store_id")
            batch.drop_constraint("fk_extraction_runs_store_id_stores", type_="foreignkey")
            batch.drop_column("store_id")
    else:
        op.drop_index("ix_extraction_runs_store_id", table_name="extraction_runs")
        op.drop_constraint("fk_extraction_runs_store_id_stores", "extraction_runs", type_="foreignkey")
        op.drop_column("extraction_runs", "store_id")
