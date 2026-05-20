"""Task 72 source-to-asset linking foundation."""

import sqlalchemy as sa
from alembic import op

revision = "0019_source_to_asset_linking_foundation"
down_revision = "0018_asset_master_identity_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "source_to_asset_links",
        sa.Column("link_id", sa.Text(), nullable=False),
        sa.Column("asset_id", sa.Text(), nullable=False),
        sa.Column("target_type", sa.Text(), nullable=False),
        sa.Column("target_id", sa.Text(), nullable=False),
        sa.Column("link_reason_nl", sa.Text(), nullable=False),
        sa.Column("audit_context_json", sa.Text(), nullable=True),
        sa.Column(
            "safe_to_use_for_suggestions",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column("blocks_suggestions", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["asset_master_records.asset_id"]),
        sa.PrimaryKeyConstraint("link_id"),
    )


def downgrade() -> None:
    op.drop_table("source_to_asset_links")
