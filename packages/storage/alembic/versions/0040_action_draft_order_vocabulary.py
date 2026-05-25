"""asset_action_drafts widened to the full IBKR order vocabulary.

Revision ID: 0040_action_draft_order_vocabulary
Revises: 0039_universe_scan_runs
Create Date: 2026-06-04

Locked in `version-1-product-experience-locks.md §21.3`. The
`order_type` column previously held only ``LMT``; this migration adds
the columns the other locked types need:

* ``stop_price`` — STP and STP_LMT trigger price
* ``trail_amount`` — TRAIL / TRAIL_LMT absolute trailing offset
* ``trail_percent`` — TRAIL / TRAIL_LMT percent trailing offset
* ``bracket_take_profit_limit_price`` — BRACKET take-profit child
* ``bracket_stop_loss_price`` — BRACKET stop-loss child

All five columns are nullable; only the columns relevant to the chosen
``order_type`` get populated. Per-type invariants are enforced by the
``AssetActionDraftRecord`` dataclass + the dry-run safety pass.
"""

import sqlalchemy as sa
from alembic import op

revision = "0040_action_draft_order_vocabulary"
down_revision = "0039_universe_scan_runs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "asset_action_drafts",
        sa.Column("stop_price", sa.Numeric(20, 6), nullable=True),
    )
    op.add_column(
        "asset_action_drafts",
        sa.Column("trail_amount", sa.Numeric(20, 6), nullable=True),
    )
    op.add_column(
        "asset_action_drafts",
        sa.Column("trail_percent", sa.Numeric(20, 6), nullable=True),
    )
    op.add_column(
        "asset_action_drafts",
        sa.Column(
            "bracket_take_profit_limit_price",
            sa.Numeric(20, 6),
            nullable=True,
        ),
    )
    op.add_column(
        "asset_action_drafts",
        sa.Column(
            "bracket_stop_loss_price",
            sa.Numeric(20, 6),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("asset_action_drafts", "bracket_stop_loss_price")
    op.drop_column("asset_action_drafts", "bracket_take_profit_limit_price")
    op.drop_column("asset_action_drafts", "trail_percent")
    op.drop_column("asset_action_drafts", "trail_amount")
    op.drop_column("asset_action_drafts", "stop_price")
