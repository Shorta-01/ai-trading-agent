"""Task 128: cold-start onboarding schema.

Widens two CHECK constraints + adds three onboarding columns to
``watchlist_items`` + creates three new tables for the cold-start
seed + confirmation state machine + state-transition audit.

* ``scheduled_run_audit.mode_detected`` widens to allow
  ``'awaiting_watchlist_confirmation'``.
* ``watchlist_items.source`` widens to allow ``'cold_start_seed'``.
* ``watchlist_items`` gains ``ibkr_account_id`` (nullable —
  per-account filtering rolls out across the app in follow-up
  tasks), ``is_starter_seed`` (default ``FALSE``), and
  ``seed_version``.
* New ``cold_start_seed_audit`` (UNIQUE on ``ibkr_account_id``
  enforces one-time seeding).
* New ``watchlist_confirmation_state`` (per-account upsert target).
* New ``watchlist_confirmation_audit`` (append-only state-transition
  log; index on ``(ibkr_account_id, event_at)``).

Revision ID: 0047_cold_start_and_watchlist_confirmation
Revises: 0046_scheduled_run_audit_and_scheduler_state
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0047_cold_start_and_watchlist_confirmation"
down_revision = "0046_scheduled_run_audit_and_scheduler_state"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ---- Widen scheduled_run_audit.mode_detected ---------------
    op.drop_constraint(
        "ck_scheduled_run_audit_mode_detected",
        "scheduled_run_audit",
        type_="check",
    )
    op.create_check_constraint(
        "ck_scheduled_run_audit_mode_detected",
        "scheduled_run_audit",
        "mode_detected IN ('cold_start','normal','disconnected',"
        "'skipped_locked','skipped_disabled',"
        "'awaiting_watchlist_confirmation')",
    )

    # ---- Widen watchlist_items.source --------------------------
    op.drop_constraint(
        "ck_watchlist_items_source_manual",
        "watchlist_items",
        type_="check",
    )
    op.add_column(
        "watchlist_items",
        sa.Column("ibkr_account_id", sa.Text(), nullable=True),
    )
    op.add_column(
        "watchlist_items",
        sa.Column(
            "is_starter_seed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "watchlist_items",
        sa.Column("seed_version", sa.Text(), nullable=True),
    )
    op.create_check_constraint(
        "ck_watchlist_items_source_valid",
        "watchlist_items",
        "source IN ('manual', 'cold_start_seed')",
    )

    # ---- cold_start_seed_audit ---------------------------------
    op.create_table(
        "cold_start_seed_audit",
        sa.Column("ibkr_account_id", sa.Text(), primary_key=True),
        sa.Column("seeded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("seeded_count", sa.Integer(), nullable=False),
        sa.Column("failed_conids_json", sa.JSON(), nullable=True),
        sa.Column("seed_version", sa.Text(), nullable=False),
    )

    # ---- watchlist_confirmation_state --------------------------
    op.create_table(
        "watchlist_confirmation_state",
        sa.Column("ibkr_account_id", sa.Text(), primary_key=True),
        sa.Column("state", sa.Text(), nullable=False),
        sa.Column(
            "last_updated_at", sa.DateTime(timezone=True), nullable=False
        ),
        sa.CheckConstraint(
            "state IN ('unconfirmed', 'confirmed')",
            name="ck_watchlist_confirmation_state_valid",
        ),
    )

    # ---- watchlist_confirmation_audit --------------------------
    op.create_table(
        "watchlist_confirmation_audit",
        sa.Column("audit_id", sa.Text(), primary_key=True),
        sa.Column("event_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ibkr_account_id", sa.Text(), nullable=False),
        sa.Column("from_state", sa.Text(), nullable=False),
        sa.Column("to_state", sa.Text(), nullable=False),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("row_count_at_event", sa.Integer(), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "from_state IN ('absent', 'unconfirmed', 'confirmed')",
            name="ck_watchlist_confirmation_audit_from_state",
        ),
        sa.CheckConstraint(
            "to_state IN ('unconfirmed', 'confirmed')",
            name="ck_watchlist_confirmation_audit_to_state",
        ),
        sa.CheckConstraint(
            "actor IN ('system', 'user')",
            name="ck_watchlist_confirmation_audit_actor",
        ),
    )
    op.create_index(
        "ix_watchlist_confirmation_audit_account_event",
        "watchlist_confirmation_audit",
        ["ibkr_account_id", "event_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_watchlist_confirmation_audit_account_event",
        table_name="watchlist_confirmation_audit",
    )
    op.drop_table("watchlist_confirmation_audit")
    op.drop_table("watchlist_confirmation_state")
    op.drop_table("cold_start_seed_audit")

    op.drop_constraint(
        "ck_watchlist_items_source_valid",
        "watchlist_items",
        type_="check",
    )
    op.drop_column("watchlist_items", "seed_version")
    op.drop_column("watchlist_items", "is_starter_seed")
    op.drop_column("watchlist_items", "ibkr_account_id")
    op.create_check_constraint(
        "ck_watchlist_items_source_manual",
        "watchlist_items",
        "source = 'manual'",
    )

    op.drop_constraint(
        "ck_scheduled_run_audit_mode_detected",
        "scheduled_run_audit",
        type_="check",
    )
    op.create_check_constraint(
        "ck_scheduled_run_audit_mode_detected",
        "scheduled_run_audit",
        "mode_detected IN ('cold_start','normal','disconnected',"
        "'skipped_locked','skipped_disabled')",
    )
