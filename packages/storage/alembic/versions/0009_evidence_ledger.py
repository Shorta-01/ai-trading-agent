"""Evidence ledger and event signal storage foundation."""

import sqlalchemy as sa
from alembic import op

revision = "0009_evidence_ledger"
down_revision = "0008_trading_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "evidence_items",
        sa.Column("evidence_id", sa.Text(), primary_key=True),
    )
    op.create_table(
        "evidence_source_links",
        sa.Column("link_id", sa.Text(), primary_key=True),
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
    )
    op.create_table(
        "event_signal_records",
        sa.Column("event_signal_id", sa.Text(), primary_key=True),
    )
    op.create_table(
        "event_signal_source_links",
        sa.Column("link_id", sa.Text(), primary_key=True),
        sa.Column("event_signal_id", sa.Text(), nullable=False),
    )
    op.create_table(
        "event_signal_asset_links",
        sa.Column("link_id", sa.Text(), primary_key=True),
        sa.Column("event_signal_id", sa.Text(), nullable=False),
        sa.Column("asset_symbol", sa.Text(), nullable=True),
    )
    op.create_table(
        "model_evidence_links",
        sa.Column("link_id", sa.Text(), primary_key=True),
        sa.Column("evidence_id", sa.Text(), nullable=False),
        sa.Column("model_result_id", sa.Text(), nullable=False),
    )
    op.create_table(
        "suggestion_evidence_links",
        sa.Column("link_id", sa.Text(), primary_key=True),
        sa.Column("suggestion_id", sa.Text(), nullable=False),
    )
    op.create_table(
        "source_conflict_records",
        sa.Column("source_conflict_id", sa.Text(), primary_key=True),
        sa.Column("asset_symbol", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("source_conflict_records")
    op.drop_table("suggestion_evidence_links")
    op.drop_table("model_evidence_links")
    op.drop_table("event_signal_asset_links")
    op.drop_table("event_signal_source_links")
    op.drop_table("event_signal_records")
    op.drop_table("evidence_source_links")
    op.drop_table("evidence_items")
