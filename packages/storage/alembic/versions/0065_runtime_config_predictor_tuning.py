"""Add predictor-tuning columns to ``runtime_config``.

V1.1 Settings UI expansion (PR I): persists five power-user
predictor-tuning knobs behind the "Voorspeller-tuning" accordion.

Revision ID: 0065_runtime_config_predictor_tuning
Revises: 0064_runtime_config_execution_gates
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0065_runtime_config_predictor_tuning"
down_revision = "0064_runtime_config_execution_gates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column("forecast_valid_minutes", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "decision_packages_valid_minutes",
                sa.Integer(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "prediction_diary_inconclusive_tolerance_pct",
                sa.Numeric(8, 4),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "gbm_regime_shift_enabled", sa.Boolean(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "gbm_regime_shift_threshold_pct",
                sa.Numeric(8, 4),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("gbm_regime_shift_threshold_pct")
        batch_op.drop_column("gbm_regime_shift_enabled")
        batch_op.drop_column("prediction_diary_inconclusive_tolerance_pct")
        batch_op.drop_column("decision_packages_valid_minutes")
        batch_op.drop_column("forecast_valid_minutes")
