"""Trading settings storage foundation.

Opslagbasis voor Toegestane beleggingen en Mijn strategie.
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_trading_settings"
down_revision = "0007_system_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "trading_settings",
        sa.Column("settings_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("allowed_universe_json", sa.JSON(), nullable=False),
        sa.Column("user_strategy_json", sa.JSON(), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("settings_id <> ''", name="ck_trading_settings_settings_id_not_empty"),
        sa.CheckConstraint("version > 0", name="ck_trading_settings_version_gt_0"),
        sa.CheckConstraint("source <> ''", name="ck_trading_settings_source_not_empty"),
        sa.CheckConstraint("status <> ''", name="ck_trading_settings_status_not_empty"),
        sa.CheckConstraint(
            "explanation_nl <> ''",
            name="ck_trading_settings_explanation_nl_not_empty",
        ),
        sa.PrimaryKeyConstraint("settings_id"),
    )


def downgrade() -> None:
    op.drop_table("trading_settings")
