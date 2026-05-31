"""Add email-notification columns to ``runtime_config``.

Backs the operator's email notification preferences + SMTP transport
config (PR K). The SMTP password is treated like the existing Claude AI
API key — the API never returns its value, only a ``smtp_password_set``
boolean, and PUT requests with an empty password preserve the stored
value.

Why all-in-one migration rather than splitting transport from prefs:
they ship together; an operator who configures SMTP but doesn't pick
which alerts to receive (or vice versa) gets nothing useful.

Revision ID: 0069_runtime_config_notifications
Revises: 0068_daily_digests
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0069_runtime_config_notifications"
down_revision = "0068_daily_digests"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        # SMTP transport config. All nullable so an operator can save
        # partial config + come back later (e.g. start with just
        # host/port, fill in credentials separately).
        batch_op.add_column(sa.Column("smtp_host", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("smtp_port", sa.Integer(), nullable=True))
        batch_op.add_column(
            sa.Column("smtp_username", sa.Text(), nullable=True)
        )
        # Password is write-only via API; stored encrypted at rest is a
        # follow-up. For V1 the column carries the raw value (matches
        # the existing ``claude_ai_api_key`` pattern).
        batch_op.add_column(
            sa.Column("smtp_password", sa.Text(), nullable=True)
        )
        batch_op.add_column(sa.Column("smtp_from", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("smtp_to", sa.Text(), nullable=True))
        batch_op.add_column(
            sa.Column("smtp_use_tls", sa.Boolean(), nullable=True)
        )
        # Notification master switch + per-trigger preferences. Null
        # means "use env-default"; the API endpoint clamps them all to
        # booleans on save.
        batch_op.add_column(
            sa.Column(
                "notifications_email_enabled", sa.Boolean(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "notification_send_on_nav_drop", sa.Boolean(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "notification_send_on_position_drop",
                sa.Boolean(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "notification_send_on_high_confidence_sell",
                sa.Boolean(),
                nullable=True,
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("notification_send_on_high_confidence_sell")
        batch_op.drop_column("notification_send_on_position_drop")
        batch_op.drop_column("notification_send_on_nav_drop")
        batch_op.drop_column("notifications_email_enabled")
        batch_op.drop_column("smtp_use_tls")
        batch_op.drop_column("smtp_to")
        batch_op.drop_column("smtp_from")
        batch_op.drop_column("smtp_password")
        batch_op.drop_column("smtp_username")
        batch_op.drop_column("smtp_port")
        batch_op.drop_column("smtp_host")
