"""Add ``profit_target_net_pct`` to ``runtime_config`` (V1.2 §AZ).

CLAUDE.md §6.1 vergrendelt de +4 % bruto winstdoel, maar deze
follow-up vraagt om operator-aanpasbaarheid: sommige operators
willen 5 % of 6 % als minimum-winst voor SELL-suggesties. We slaan
het percentage op in runtime_config zodat één edit op de
``/instellingen`` pagina de hele stack beïnvloedt.

Nullable: ``None`` (default) betekent "doctrine-default 4 %". Dat
laat de bestaande tests onaangepast.

Revision ID: 0075_runtime_config_profit_target
Revises: 0074_runtime_config_software_pause
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0075_runtime_config_profit_target"
down_revision = "0074_runtime_config_software_pause"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "runtime_config",
        sa.Column(
            "profit_target_net_pct",
            sa.Numeric(precision=20, scale=8),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("runtime_config", "profit_target_net_pct")
