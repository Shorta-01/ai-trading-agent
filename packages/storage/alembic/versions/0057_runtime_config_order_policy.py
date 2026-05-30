"""Add order-policy + suggestion-filter columns to ``runtime_config``.

V1.1 Settings UI expansion (PR A): persists the six order-policy /
suggestion-filter values the operator now edits from the Settings page
into the existing runtime-overlay row, so the API picks them up at
startup and on every save without an env-var redeploy.

Revision ID: 0057_runtime_config_order_policy
Revises: 0056_runtime_config_universe_scan
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0057_runtime_config_order_policy"
down_revision = "0056_runtime_config_universe_scan"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        # Order-sizing defaults the action-draft composer reads. Numeric
        # (20,6) for parity with the rest of the money columns in the
        # database; Python decimals carry exact values both ways.
        batch_op.add_column(sa.Column("default_buy_value_eur", _MONEY, nullable=True))
        batch_op.add_column(sa.Column("default_top_up_pct", _MONEY, nullable=True))
        batch_op.add_column(sa.Column("default_reduce_pct", _MONEY, nullable=True))
        # Suggestion-filter knobs the morning chain reads.
        batch_op.add_column(sa.Column("max_sector_pct", _MONEY, nullable=True))
        batch_op.add_column(sa.Column("cost_dominates_ratio", _MONEY, nullable=True))
        batch_op.add_column(sa.Column("suggestion_valid_minutes", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("default_buy_value_eur")
        batch_op.drop_column("default_top_up_pct")
        batch_op.drop_column("default_reduce_pct")
        batch_op.drop_column("max_sector_pct")
        batch_op.drop_column("cost_dominates_ratio")
        batch_op.drop_column("suggestion_valid_minutes")
