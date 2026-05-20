"""asset master identity foundation

Revision ID: 0018_asset_master_identity_foundation
Revises: 0017_research_source_conflict_findings
Create Date: 2026-05-20
"""
import sqlalchemy as sa
from alembic import op

revision = '0018_asset_master_identity_foundation'
down_revision = '0017_research_source_conflict_findings'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'asset_master_records',
        sa.Column('asset_id', sa.Text(), nullable=False),
        sa.Column('canonical_symbol', sa.Text(), nullable=False),
        sa.Column('asset_name', sa.Text(), nullable=False),
        sa.Column('asset_type', sa.Text(), nullable=False),
        sa.Column('primary_exchange', sa.Text(), nullable=True),
        sa.Column('primary_currency', sa.Text(), nullable=True),
        sa.Column('country', sa.Text(), nullable=True),
        sa.Column('isin', sa.Text(), nullable=True),
        sa.Column('figi', sa.Text(), nullable=True),
        sa.Column('cusip', sa.Text(), nullable=True),
        sa.Column('ibkr_contract_id', sa.Text(), nullable=True),
        sa.Column('sector', sa.Text(), nullable=True),
        sa.Column('industry', sa.Text(), nullable=True),
        sa.Column('status', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('identity_confidence', sa.Text(), nullable=False),
        sa.Column('identity_source', sa.Text(), nullable=False),
        sa.Column('source_reference_ids_json', sa.JSON(), nullable=True),
        sa.Column('audit_context_json', sa.JSON(), nullable=True),
        sa.Column(
            'safe_to_use_for_suggestions',
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        sa.Column('blocks_suggestions', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('explanation_nl', sa.Text(), nullable=False),
        sa.PrimaryKeyConstraint('asset_id'),
        sa.UniqueConstraint('canonical_symbol'),
    )
    op.create_table(
        'asset_identifier_aliases',
        sa.Column('alias_id', sa.Text(), nullable=False),
        sa.Column('asset_id', sa.Text(), nullable=False),
        sa.Column('identifier_type', sa.Text(), nullable=False),
        sa.Column('identifier_value', sa.Text(), nullable=False),
        sa.Column('source', sa.Text(), nullable=False),
        sa.Column('confidence_level', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('explanation_nl', sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(['asset_id'], ['asset_master_records.asset_id']),
        sa.PrimaryKeyConstraint('alias_id'),
    )

def downgrade() -> None:
    op.drop_table('asset_identifier_aliases')
    op.drop_table('asset_master_records')
