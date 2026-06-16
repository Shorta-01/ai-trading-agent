"""§CB.2 audit-cleanup: composite index op asset_action_drafts(account_id, status).

GAPS uit de §CB.2 storage-audit (2026-06-16): single-column index
op ``status`` (0080) dekt globale stage-filtering, maar de Stage-2
en Stage-3 widgets op het dashboard filtreren per IBKR-account
en dan op status. Een composiet index sluit beide kanten af.

Verder: 3 FK constraints die ontbraken op de action-draft
substages (submissions / events / order_conditions). De
storage-audit identificeerde deze als data-integriteits-risico —
bij een ``DELETE`` op een draft-rij konden er orphan substage-
rijen achterblijven. Postgres ondersteunt ``ADD CONSTRAINT``
direct; voor SQLite (test-omgeving) gebruiken we
``batch_alter_table`` zodat de migratie cross-platform werkt.

Doctrine-borging: alleen schema-integriteit + leesperformance.
Geen safe_for_* aanpassingen, geen kolommen toegevoegd / verwijderd.

Revision ID: 0081_action_draft_fks_and_index
Revises: 0080_dashboard_query_indexes
Create Date: 2026-06-16
"""

from alembic import op

revision = "0081_action_draft_fks_and_index"
down_revision = "0080_dashboard_query_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Composite index voor per-account stage-filtering — Stage-2 widget
    # (te-verzenden) en Stage-3 widget (verzonden) gebruiken beide
    # WHERE ibkr_account_id = ? AND status IN (...).
    op.create_index(
        "ix_asset_action_drafts_account_status",
        "asset_action_drafts",
        ["ibkr_account_id", "status"],
    )

    # FK constraints op de action-draft substages. Postgres laat
    # ADD CONSTRAINT direct toe; SQLite vereist batch-mode (table-
    # rebuild). Beide paden via ``batch_alter_table`` zodat de
    # migratie ook in de test-omgeving werkt.
    with op.batch_alter_table("asset_action_draft_submissions") as batch_op:
        batch_op.create_foreign_key(
            "fk_asset_action_draft_submissions_draft_id",
            "asset_action_drafts",
            ["draft_id"],
            ["draft_id"],
            ondelete="CASCADE",
        )
    with op.batch_alter_table("asset_action_draft_events") as batch_op:
        batch_op.create_foreign_key(
            "fk_asset_action_draft_events_draft_id",
            "asset_action_drafts",
            ["draft_id"],
            ["draft_id"],
            ondelete="CASCADE",
        )
    with op.batch_alter_table("action_draft_order_conditions") as batch_op:
        batch_op.create_foreign_key(
            "fk_action_draft_order_conditions_draft_id",
            "asset_action_drafts",
            ["draft_id"],
            ["draft_id"],
            ondelete="CASCADE",
        )


def downgrade() -> None:
    with op.batch_alter_table("action_draft_order_conditions") as batch_op:
        batch_op.drop_constraint(
            "fk_action_draft_order_conditions_draft_id", type_="foreignkey"
        )
    with op.batch_alter_table("asset_action_draft_events") as batch_op:
        batch_op.drop_constraint(
            "fk_asset_action_draft_events_draft_id", type_="foreignkey"
        )
    with op.batch_alter_table("asset_action_draft_submissions") as batch_op:
        batch_op.drop_constraint(
            "fk_asset_action_draft_submissions_draft_id", type_="foreignkey"
        )
    op.drop_index(
        "ix_asset_action_drafts_account_status",
        table_name="asset_action_drafts",
    )
