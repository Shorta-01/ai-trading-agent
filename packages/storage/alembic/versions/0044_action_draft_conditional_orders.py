"""action draft conditional-order conditions child table.

V1.1 §22.3 Slice 32 (conditional orders + GTC/OPG/IOC). Adds the
child table that stores the per-condition rows attached to a
``asset_action_drafts`` row when ``order_type="CONDITIONAL"``.

Single child table with a discriminator column (``condition_kind``)
+ nullable kind-specific columns covers the five locked condition
kinds (``price``, ``time``, ``margin``, ``volume``, ``execution``)
without forcing five separate tables. Safety booleans hard-False;
a condition row never authorises an order.

Revision ID: 0044_action_draft_conditional_orders
Revises: 0043_claude_ai_budget_usage
Create Date: 2026-05-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0044_action_draft_conditional_orders"
down_revision = "0043_claude_ai_budget_usage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # V1.1 §22.3: parent base type pinned on the draft when
    # order_type=CONDITIONAL. Nullable so existing rows stay valid;
    # the dataclass invariant requires non-null when order_type is
    # CONDITIONAL.
    op.add_column(
        "asset_action_drafts",
        sa.Column("conditional_parent_order_type", sa.Text(), nullable=True),
    )
    op.create_table(
        "action_draft_order_conditions",
        sa.Column("condition_id", sa.Text(), primary_key=True),
        sa.Column("draft_id", sa.Text(), nullable=False),
        sa.Column("condition_index", sa.Integer(), nullable=False),
        sa.Column("condition_kind", sa.Text(), nullable=False),
        sa.Column("comparator", sa.Text(), nullable=False),
        sa.Column("conjunction", sa.Text(), nullable=False),
        # Price/volume conditions reference an asset.
        sa.Column("trigger_symbol", sa.Text(), nullable=True),
        sa.Column("trigger_conid", sa.Text(), nullable=True),
        sa.Column("trigger_exchange", sa.Text(), nullable=True),
        # Price-kind trigger.
        sa.Column("trigger_price", sa.Numeric(20, 6), nullable=True),
        # Time-kind trigger.
        sa.Column("trigger_at_utc", sa.DateTime(timezone=True), nullable=True),
        # Margin-kind trigger (percent of account margin).
        sa.Column("margin_percent", sa.Numeric(10, 6), nullable=True),
        # Volume-kind trigger (cumulative daily volume threshold).
        sa.Column("trigger_volume", sa.BigInteger(), nullable=True),
        # Execution-kind trigger: another fill on the same / a related
        # contract.
        sa.Column("execution_symbol", sa.Text(), nullable=True),
        sa.Column("execution_sec_type", sa.Text(), nullable=True),
        sa.Column("execution_exchange", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "safe_for_action_drafts",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column(
            "safe_for_orders",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index(
        "ix_action_draft_order_conditions_draft",
        "action_draft_order_conditions",
        ["draft_id", "condition_index"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_action_draft_order_conditions_draft",
        table_name="action_draft_order_conditions",
    )
    op.drop_table("action_draft_order_conditions")
    op.drop_column("asset_action_drafts", "conditional_parent_order_type")
