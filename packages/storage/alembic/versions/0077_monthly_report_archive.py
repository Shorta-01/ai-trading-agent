"""Add ``monthly_report_archive`` table — auto-PDF maandarchief
(V1.2 §BC / CLAUDE.md §13 follow-up).

CLAUDE.md §13 voorziet een auto-PDF die elke 1e van de maand
gegenereerd wordt en blijvend beschikbaar is in ``/rapporten/archief``.
We slaan de PDF-bytes direct in de DB op zodat de operator zonder
filesystem-mount kan downloaden. PDFs zijn typisch klein (50-200 KB)
voor één maand; bij groei kunnen we naar S3/blob-storage migreren
zonder API-breaking change.

Eén row per ``(account_ref, year, month)``. Re-genereren upsert het
binary blob. Audit-stabiel: ``generated_at`` legt het tijdstip vast.

Revision ID: 0077_monthly_report_archive
Revises: 0076_dividend_events
Create Date: 2026-06-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0077_monthly_report_archive"
down_revision = "0076_dividend_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "monthly_report_archive",
        sa.Column("archive_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_account_ref", sa.Text(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("pdf_bytes", sa.LargeBinary(), nullable=False),
        sa.Column("pdf_size_bytes", sa.Integer(), nullable=False),
        sa.Column("generated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("source", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "month >= 1 AND month <= 12",
            name="ck_monthly_report_archive_month_range",
        ),
        sa.CheckConstraint(
            "year >= 2000 AND year <= 2100",
            name="ck_monthly_report_archive_year_range",
        ),
        sa.UniqueConstraint(
            "ibkr_account_ref", "year", "month",
            name="uq_monthly_report_archive_account_year_month",
        ),
    )
    op.create_index(
        "ix_monthly_report_archive_account_date",
        "monthly_report_archive",
        ["ibkr_account_ref", "year", "month"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_monthly_report_archive_account_date",
        table_name="monthly_report_archive",
    )
    op.drop_table("monthly_report_archive")
