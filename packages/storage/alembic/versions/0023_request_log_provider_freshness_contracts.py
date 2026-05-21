"""Request-log/provider-source/freshness-audit opslagcontracten (non-runtime skeleton)."""

from alembic import op
import sqlalchemy as sa

revision = "0023_request_log_provider_freshness_contracts"
down_revision = "0022_asset_listing_identity_foundation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "request_logs",
        sa.Column("request_log_id", sa.Text(), primary_key=True),
        sa.Column("correlation_id", sa.Text(), nullable=False),
        sa.Column("request_family", sa.Text(), nullable=False),
        sa.Column("request_purpose", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("provider_account_mode", sa.Text(), nullable=False),
        sa.Column("provider_environment", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("data_domain", sa.Text(), nullable=False),
        sa.Column("request_kind", sa.Text(), nullable=False),
        sa.Column("request_target", sa.Text(), nullable=False),
        sa.Column("request_status", sa.Text(), nullable=False),
        sa.Column("initiated_by", sa.Text(), nullable=False),
        sa.Column("pacing_weight", sa.Integer(), nullable=True),
        sa.Column("provider_request_budget_remaining", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True),
        sa.Column("received_record_count", sa.Integer(), nullable=True),
        sa.Column("stored_record_count", sa.Integer(), nullable=True),
        sa.Column("rejected_record_count", sa.Integer(), nullable=True),
        sa.Column("safe_for_analysis", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_for_suggestions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_for_action_drafts", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("completed_at IS NULL OR completed_at >= created_at", name="ck_request_logs_completed_after_created"),
        sa.CheckConstraint("pacing_weight IS NULL OR pacing_weight >= 0", name="ck_request_logs_pacing_weight_non_negative"),
        sa.CheckConstraint("provider_request_budget_remaining IS NULL OR provider_request_budget_remaining >= 0", name="ck_request_logs_budget_non_negative"),
        sa.CheckConstraint("retry_count IS NULL OR retry_count >= 0", name="ck_request_logs_retry_count_non_negative"),
        sa.CheckConstraint("received_record_count IS NULL OR received_record_count >= 0", name="ck_request_logs_received_non_negative"),
        sa.CheckConstraint("stored_record_count IS NULL OR stored_record_count >= 0", name="ck_request_logs_stored_non_negative"),
        sa.CheckConstraint("rejected_record_count IS NULL OR rejected_record_count >= 0", name="ck_request_logs_rejected_non_negative"),
        sa.CheckConstraint("safe_for_analysis IS FALSE", name="ck_request_logs_safe_for_analysis_false"),
        sa.CheckConstraint("safe_for_suggestions IS FALSE", name="ck_request_logs_safe_for_suggestions_false"),
        sa.CheckConstraint("safe_for_action_drafts IS FALSE", name="ck_request_logs_safe_for_action_drafts_false"),
    )
    op.create_table(
        "provider_sources",
        sa.Column("provider_source_id", sa.Text(), primary_key=True),
        sa.Column("provider_code", sa.Text(), nullable=False),
        sa.Column("provider_kind", sa.Text(), nullable=False),
        sa.Column("data_domain", sa.Text(), nullable=False),
        sa.Column("source_type", sa.Text(), nullable=False),
        sa.Column("provider_environment", sa.Text(), nullable=False),
        sa.Column("provider_account_mode", sa.Text(), nullable=False),
        sa.Column("source_effective_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("source_effective_to", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("updated_at >= created_at", name="ck_provider_sources_updated_after_created"),
        sa.CheckConstraint("source_effective_to IS NULL OR source_effective_from IS NULL OR source_effective_to >= source_effective_from", name="ck_provider_sources_effective_order"),
    )
    op.create_table(
        "freshness_audit_records",
        sa.Column("freshness_audit_id", sa.Text(), primary_key=True),
        sa.Column("evaluated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("data_domain", sa.Text(), nullable=False),
        sa.Column("freshness_policy_code", sa.Text(), nullable=False),
        sa.Column("freshness_status", sa.Text(), nullable=False),
        sa.Column("snapshot_as_of", sa.DateTime(timezone=True), nullable=True),
        sa.Column("observed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("stored_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("age_seconds", sa.Integer(), nullable=True),
        sa.Column("freshness_window_seconds", sa.Integer(), nullable=True),
        sa.Column("stale_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("safe_for_analysis", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_for_suggestions", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("safe_for_action_drafts", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("explanation_nl", sa.Text(), nullable=False),
        sa.CheckConstraint("age_seconds IS NULL OR age_seconds >= 0", name="ck_freshness_audit_age_non_negative"),
        sa.CheckConstraint("freshness_window_seconds IS NULL OR freshness_window_seconds >= 0", name="ck_freshness_audit_window_non_negative"),
        sa.CheckConstraint("stale_after IS NULL OR snapshot_as_of IS NULL OR stale_after >= snapshot_as_of", name="ck_freshness_audit_stale_after_order"),
        sa.CheckConstraint("expires_at IS NULL OR stale_after IS NULL OR expires_at >= stale_after", name="ck_freshness_audit_expires_after_stale"),
        sa.CheckConstraint("safe_for_analysis IS FALSE", name="ck_freshness_audit_safe_for_analysis_false"),
        sa.CheckConstraint("safe_for_suggestions IS FALSE", name="ck_freshness_audit_safe_for_suggestions_false"),
        sa.CheckConstraint("safe_for_action_drafts IS FALSE", name="ck_freshness_audit_safe_for_action_drafts_false"),
    )


def downgrade() -> None:
    op.drop_table("freshness_audit_records")
    op.drop_table("provider_sources")
    op.drop_table("request_logs")
