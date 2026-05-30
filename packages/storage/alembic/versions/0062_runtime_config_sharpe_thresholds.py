"""Add Sharpe direction-label thresholds to ``runtime_config``.

V1.1 Settings UI expansion (PR F): persists the risk-adjusted (Sharpe)
direction-label thresholds the GBM path uses. The Settings UI surfaces
them in the existing "Geavanceerde instellingen" accordion next to the
other Tier-2 power-user knobs.

Revision ID: 0062_runtime_config_sharpe_thresholds
Revises: 0061_runtime_config_advanced
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0062_runtime_config_sharpe_thresholds"
down_revision = "0061_runtime_config_advanced"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column(
                "sharpe_strong_threshold",
                sa.Numeric(8, 4),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "sharpe_slight_threshold",
                sa.Numeric(8, 4),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("sharpe_slight_threshold")
        batch_op.drop_column("sharpe_strong_threshold")
