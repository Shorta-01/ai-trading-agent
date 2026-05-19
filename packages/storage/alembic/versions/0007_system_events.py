"""System event storage foundation.

Centrale systeemmeldingen/foutenlogboek opslagbasis.
Alleen storage-contracten en migratie; geen runtime wiring.
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_system_events"
down_revision = "0006_external_broker_activities"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "system_events",
        sa.Column("system_event_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("severity", sa.Text(), nullable=False),
        sa.Column("category", sa.Text(), nullable=False),
        sa.Column("source_service", sa.Text(), nullable=False),
        sa.Column("source_component", sa.Text(), nullable=False),
        sa.Column("event_code", sa.Text(), nullable=False),
        sa.Column("title_nl", sa.Text(), nullable=False),
        sa.Column("message_nl", sa.Text(), nullable=False),
        sa.Column("help_nl", sa.Text(), nullable=False),
        sa.Column("technical_summary", sa.Text(), nullable=True),
        sa.Column("redacted_details_json", sa.JSON(), nullable=True),
        sa.Column("stack_trace_redacted", sa.Text(), nullable=True),
        sa.Column("related_entity_type", sa.Text(), nullable=True),
        sa.Column("related_entity_id", sa.Text(), nullable=True),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("blocks_writes", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "blocks_ai_explanation", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("status", sa.Text(), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("copied_for_codex_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("severity <> ''", name="ck_system_events_severity_not_empty"),
        sa.CheckConstraint("category <> ''", name="ck_system_events_category_not_empty"),
        sa.CheckConstraint(
            "source_service <> ''", name="ck_system_events_source_service_not_empty"
        ),
        sa.CheckConstraint(
            "source_component <> ''", name="ck_system_events_source_component_not_empty"
        ),
        sa.CheckConstraint("event_code <> ''", name="ck_system_events_event_code_not_empty"),
        sa.CheckConstraint("title_nl <> ''", name="ck_system_events_title_nl_not_empty"),
        sa.CheckConstraint("message_nl <> ''", name="ck_system_events_message_nl_not_empty"),
        sa.CheckConstraint("help_nl <> ''", name="ck_system_events_help_nl_not_empty"),
        sa.CheckConstraint("status <> ''", name="ck_system_events_status_not_empty"),
        sa.CheckConstraint(
            "explanation_nl <> ''", name="ck_system_events_explanation_nl_not_empty"
        ),
        sa.PrimaryKeyConstraint("system_event_id"),
    )


def downgrade() -> None:
    op.drop_table("system_events")
