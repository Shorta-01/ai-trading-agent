"""Add worker-side sweep + EODHD columns to ``runtime_config``.

V1.1 Settings UI expansion (PR D): persists the operator's
worker-side sweep cadence/retry/alert + EODHD rate-limit so they're
editable from the Settings page. The worker reads ``runtime_config``
at startup (new ``apply_worker_runtime_config_overlay``) before the
scheduler registers jobs, so changes take effect from the next
worker restart for interval-job registration and immediately for
per-tick reads.

Revision ID: 0060_runtime_config_worker_sweeps
Revises: 0059_runtime_config_data_windows
Create Date: 2026-05-30
"""

import sqlalchemy as sa
from alembic import op

revision = "0060_runtime_config_worker_sweeps"
down_revision = "0059_runtime_config_data_windows"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(precision=20, scale=6)


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column("sweep_interval_seconds", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("sweep_retry_max_attempts", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("sweep_retry_backoff_seconds", _MONEY, nullable=True)
        )
        batch_op.add_column(
            sa.Column(
                "sweep_alert_after_consecutive_errors", sa.Integer(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column("eodhd_rate_limit_per_second", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("sweep_interval_seconds")
        batch_op.drop_column("sweep_retry_max_attempts")
        batch_op.drop_column("sweep_retry_backoff_seconds")
        batch_op.drop_column("sweep_alert_after_consecutive_errors")
        batch_op.drop_column("eodhd_rate_limit_per_second")
