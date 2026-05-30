"""Add Tier-2 "advanced settings" columns to ``runtime_config``.

V1.1 Settings UI expansion (PR E): persists four power-user knobs
that until now were env-var-only. UI surfaces them under a collapsed
"Geavanceerde instellingen" accordion so they don't clutter the page
for the typical operator.

Revision ID: 0061_runtime_config_advanced
Revises: 0060_runtime_config_worker_sweeps
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0061_runtime_config_advanced"
down_revision = "0060_runtime_config_worker_sweeps"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column("ensemble_weight_strategy", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("gbm_drift_window_days", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "action_draft_approval_valid_minutes", sa.Integer(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("ai_explanation_provider_code", sa.Text(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("ensemble_weight_strategy")
        batch_op.drop_column("gbm_drift_window_days")
        batch_op.drop_column("action_draft_approval_valid_minutes")
        batch_op.drop_column("ai_explanation_provider_code")
