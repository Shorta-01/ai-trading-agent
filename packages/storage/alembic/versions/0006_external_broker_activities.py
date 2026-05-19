"""External broker activity schema foundation.

IBKR mirror/reconciliation foundation slice 5.
External broker activity storage only.
No runtime IBKR integration wired yet.
No reconciliation engine wired yet.
No order transmission wired yet.
"""

import sqlalchemy as sa
from alembic import op

revision = "0006_external_broker_activities"
down_revision = "0005_broker_reconciliation_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "external_broker_activities",
        sa.Column("external_broker_activity_id", sa.Text(), nullable=False),
        sa.Column("broker_account_id", sa.Text(), nullable=False),
        sa.Column("broker_system", sa.Text(), nullable=False),
        sa.Column("detected_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("origin", sa.Text(), nullable=False),
        sa.Column("data_kind", sa.Text(), nullable=False),
        sa.Column("related_execution_id", sa.Text(), nullable=True),
        sa.Column("related_asset_identifier", sa.Text(), nullable=True),
        sa.Column("summary_nl", sa.Text(), nullable=False),
        sa.Column("help_nl", sa.Text(), nullable=False),
        sa.Column("source_reference_ids_json", sa.JSON(), nullable=True),
        sa.Column("audit_event_ids_json", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "broker_system = 'ibkr'",
            name="ck_external_broker_activities_broker_system_ibkr",
        ),
        sa.CheckConstraint("origin <> ''", name="ck_external_broker_activities_origin_not_empty"),
        sa.CheckConstraint(
            "data_kind <> ''",
            name="ck_external_broker_activities_data_kind_not_empty",
        ),
        sa.CheckConstraint(
            "summary_nl <> ''",
            name="ck_external_broker_activities_summary_nl_not_empty",
        ),
        sa.CheckConstraint("help_nl <> ''", name="ck_external_broker_activities_help_nl_not_empty"),
        sa.ForeignKeyConstraint(
            ["broker_account_id"],
            ["broker_accounts.broker_account_id"],
        ),
        sa.PrimaryKeyConstraint("external_broker_activity_id"),
    )


def downgrade() -> None:
    op.drop_table("external_broker_activities")
