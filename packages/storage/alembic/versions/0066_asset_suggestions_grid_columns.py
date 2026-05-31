"""Add suggestion-grid display columns to ``asset_suggestions``.

Adds the operator-facing fields the V1 suggestion grid needs to render
without round-tripping through the decision-package fetch:

- ``branch_reason_nl`` — which branch of the decision tree fired
  (e.g. "strong_up but Gebalanceerd → Houden instead of Langzaam bijkopen")
- ``downgrade_reason_nl`` — populated when a portfolio gate downgrades
  Kopen/Bijkopen to Bekijken (e.g. "sector cap bereikt")
- ``top_driver_nl`` — single-line "why" rendered inline in the grid
- ``blocking_reason_nl`` — Dutch version of the existing
  ``blocking_reason`` so the operator never sees an English token
- ``expected_return_pct`` / ``prob_gain_pct`` — mirrored from the
  forecast so the grid renders without a forecast join

Revision ID: 0066_asset_suggestions_grid_columns
Revises: 0065_runtime_config_predictor_tuning
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0066_asset_suggestions_grid_columns"
down_revision = "0065_runtime_config_predictor_tuning"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("asset_suggestions") as batch_op:
        batch_op.add_column(
            sa.Column("branch_reason_nl", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("downgrade_reason_nl", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("top_driver_nl", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("blocking_reason_nl", sa.Text(), nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "expected_return_pct", sa.Numeric(10, 4), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("prob_gain_pct", sa.Numeric(10, 4), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("asset_suggestions") as batch_op:
        batch_op.drop_column("prob_gain_pct")
        batch_op.drop_column("expected_return_pct")
        batch_op.drop_column("blocking_reason_nl")
        batch_op.drop_column("top_driver_nl")
        batch_op.drop_column("downgrade_reason_nl")
        batch_op.drop_column("branch_reason_nl")
