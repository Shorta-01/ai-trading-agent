"""Add AI feature-toggle columns to ``runtime_config``.

Surfaces three flags shipped by PRs #557 / #558 / #559 on the Settings
UI so the operator can toggle them without editing env-vars:

* ``ai_explanation_morning_batch_enabled`` — pre-compute Claude
  paraphrases for every held-position Decision Package overnight.
* ``ai_email_summary_enabled`` — prepend an AI-composed Dutch
  summary header to the digest + morning-alerts emails.
* ``research_ai_extraction_enabled`` — surface AI-extracted facts /
  quotes from research source documents (guarded by the substring
  hallucination check, never auto-promoted to suggestions).

All three are nullable booleans so ``NULL`` means "use the env-var
default" — same overlay shape the rest of ``runtime_config`` uses.

Revision ID: 0070_runtime_config_ai_features
Revises: 0069_runtime_config_notifications
Create Date: 2026-05-31
"""

import sqlalchemy as sa
from alembic import op

revision = "0070_runtime_config_ai_features"
down_revision = "0069_runtime_config_notifications"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.add_column(
            sa.Column(
                "ai_explanation_morning_batch_enabled",
                sa.Boolean(),
                nullable=True,
            )
        )
        batch_op.add_column(
            sa.Column(
                "ai_email_summary_enabled", sa.Boolean(), nullable=True
            )
        )
        batch_op.add_column(
            sa.Column(
                "research_ai_extraction_enabled", sa.Boolean(), nullable=True
            )
        )


def downgrade() -> None:
    with op.batch_alter_table("runtime_config") as batch_op:
        batch_op.drop_column("research_ai_extraction_enabled")
        batch_op.drop_column("ai_email_summary_enabled")
        batch_op.drop_column("ai_explanation_morning_batch_enabled")
