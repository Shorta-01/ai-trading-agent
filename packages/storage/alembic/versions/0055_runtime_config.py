"""Editable IBKR connection + Claude AI settings from the dashboard.

Adds ``runtime_config`` — a single-row config table (PK ``config_id`` text,
value ``"default"``) that lets the operator edit the IBKR connection and the
Claude AI explanation settings from the Settings page instead of only via
environment variables. The API reads it at startup and overlays the non-null
values onto the settings singleton; the worker-side IBKR host/port/client_id
overlay is a follow-up tied to the durable worker session.

Revision ID: 0055_runtime_config
Revises: 0054_ibkr_nav_snapshots
Create Date: 2026-05-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0055_runtime_config"
down_revision = "0054_ibkr_nav_snapshots"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    op.create_table(
        "runtime_config",
        sa.Column("config_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_enabled", sa.Boolean(), nullable=False),
        sa.Column("ibkr_account_id", sa.Text(), nullable=True),
        sa.Column("ibkr_host", sa.Text(), nullable=True),
        sa.Column("ibkr_port", sa.Integer(), nullable=True),
        sa.Column("ibkr_client_id", sa.Integer(), nullable=True),
        sa.Column("ai_explanation_enabled", sa.Boolean(), nullable=False),
        sa.Column("claude_ai_explanation_model", sa.Text(), nullable=True),
        sa.Column("claude_ai_budget_monthly_eur", _MONEY, nullable=True),
        sa.Column("claude_ai_api_key", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("runtime_config")
