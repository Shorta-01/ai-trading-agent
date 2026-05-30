"""Add ``universe_scan_index_codes`` to ``runtime_config``.

V1.1 follow-up to the suggestion-engine improvements: replaces the
single-string ``universe_set`` selector with an operator-pickable
multi-select. The new column stores a comma-separated list of locked
index codes (see ``portfolio_outlook_api.universe_registry``); when
non-null at startup the API overlay pushes it onto
``settings.universe_scan_index_codes`` which the universe scanner reads.

Revision ID: 0056_runtime_config_universe_scan
Revises: 0055_runtime_config
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0056_runtime_config_universe_scan"
down_revision = "0055_runtime_config"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column(
                "universe_scan_index_codes",
                sa.Text(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("universe_scan_index_codes")
