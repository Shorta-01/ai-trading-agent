"""Add ``orchestrator_scoring_verdicts`` table — parallel-scored profit-
harvest doctrine verdicts (V1.2 §W).

Backs the orchestrator scoring path the worker will write alongside
the existing suggestion pipeline. The doctrine orchestrator
(V1.2 §M, packages/portfolio/.../profit_harvest_orchestrator.py)
produces one verdict per candidate during the morning chain; this
table stores those verdicts so the operator UI can compare doctrine
output against the live suggestion engine before the doctrine takes
over the primary path.

Decoupling rationale:
- The existing ``asset_suggestions`` table is shaped for the live
  suggestion engine (action_label, drivers_json, etc.). Forcing
  the orchestrator output into that shape would conflate two
  decision sources.
- A separate table lets us turn the scoring path on/off without
  worrying about polluting the live suggestion stream.
- JSON-blob ``details_json`` is intentional: the diagnostics shape
  evolves with each gate added; per-field columns would migrate on
  every doctrine change.

Revision ID: 0071_orchestrator_scoring_verdicts
Revises: 0070_runtime_config_ai_features
Create Date: 2026-06-12
"""

import sqlalchemy as sa
from alembic import op

revision = "0071_orchestrator_scoring_verdicts"
down_revision = "0070_runtime_config_ai_features"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "orchestrator_scoring_verdicts",
        sa.Column("verdict_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_account_ref", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("ibkr_conid", sa.Integer(), nullable=True),
        # Pointer back to the forecast row the orchestrator scored
        # against — lets the UI cross-reference the same forecast
        # the live suggestion engine consumed.
        sa.Column("forecast_id", sa.Text(), nullable=True),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        # Locked decision codes from
        # profit_harvest_orchestrator.DECISION_*.
        sa.Column("decision", sa.Text(), nullable=False),
        sa.Column("blocking_reason", sa.Text(), nullable=True),
        # Free-form diagnostics — macro / risk-universe / earnings /
        # confidence / sector / news-sentiment / pair-build details,
        # plus the boosted_confidence_pct and proposed_position_eur.
        sa.Column("details_json", sa.JSON(), nullable=False),
        # Dutch one-liner ready for display (from
        # orchestrator_explanation.explain_decision).
        sa.Column("summary_nl", sa.Text(), nullable=False),
        # One verdict per (account, symbol, forecast_id) — re-runs
        # against the same forecast row overwrite rather than
        # accumulate.
        sa.UniqueConstraint(
            "ibkr_account_ref",
            "symbol",
            "forecast_id",
            name="uq_orch_verdict_per_account_symbol_forecast",
        ),
    )


def downgrade() -> None:
    op.drop_table("orchestrator_scoring_verdicts")
