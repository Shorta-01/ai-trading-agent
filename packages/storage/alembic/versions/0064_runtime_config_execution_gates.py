"""Add execution-gate columns to ``runtime_config``.

V1.1 Settings UI expansion (PR H): persists four safety-critical
execution toggles. ``ibkr_paper_order_submission_enabled`` is read by
the API; the other three are worker-side and applied by
``apply_worker_runtime_config_overlay``.

Revision ID: 0064_runtime_config_execution_gates
Revises: 0063_runtime_config_forecast_market
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0064_runtime_config_execution_gates"
down_revision = "0063_runtime_config_forecast_market"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column(
                "ibkr_paper_order_submission_enabled",
                sa.Boolean(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "submission_sweep_enabled", sa.Boolean(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("cancel_sweep_enabled", sa.Boolean(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "morning_chain_after_pre_briefing",
                sa.Boolean(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("morning_chain_after_pre_briefing")
        batch_op.drop_column("cancel_sweep_enabled")
        batch_op.drop_column("submission_sweep_enabled")
        batch_op.drop_column("ibkr_paper_order_submission_enabled")
