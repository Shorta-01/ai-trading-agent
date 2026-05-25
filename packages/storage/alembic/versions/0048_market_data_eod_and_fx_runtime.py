"""Task 129: EOD market-data runtime + FX rates + provider audit.

Three additive tables:

* ``market_data_eod_snapshots`` — point-in-time OHLCV per
  ``(ibkr_conid, as_of_date, provider)``. UNIQUE enforces fetch
  idempotency. The existing ``market_data_snapshots`` envelope from
  Tasks 85-92 stays untouched (it serves the readiness gate; the
  new table holds the real price data).
* ``fx_rates`` — composite PK on ``(base, quote, as_of_date,
  provider)``. The API joins this at display time; storage never
  co-mingles local + EUR.
* ``provider_call_audit`` — one row per outbound provider HTTP call.
  Append-only.

Revision ID: 0048_market_data_eod_and_fx_runtime
Revises: 0047_cold_start_and_watchlist_confirmation
Create Date: 2026-05-25
"""

import sqlalchemy as sa
from alembic import op

revision = "0048_market_data_eod_and_fx_runtime"
down_revision = "0047_cold_start_and_watchlist_confirmation"
branch_labels = None
depends_on = None

_MONEY = sa.Numeric(precision=20, scale=6)
_FX = sa.Numeric(precision=20, scale=8)


def upgrade() -> None:
    op.create_table(
        "market_data_eod_snapshots",
        sa.Column("snapshot_id", sa.Text(), primary_key=True),
        sa.Column("ibkr_conid", sa.Text(), nullable=False),
        sa.Column("symbol", sa.Text(), nullable=False),
        sa.Column("exchange", sa.Text(), nullable=True),
        sa.Column("currency_local", sa.Text(), nullable=False),
        sa.Column("as_of_date", sa.Date(), nullable=False),
        sa.Column(
            "as_of_close_ts", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column(
            "ingested_ts", sa.DateTime(timezone=True), nullable=False
        ),
        sa.Column("open_local", _MONEY, nullable=True),
        sa.Column("high_local", _MONEY, nullable=True),
        sa.Column("low_local", _MONEY, nullable=True),
        sa.Column("close_local", _MONEY, nullable=False),
        sa.Column("adj_close_local", _MONEY, nullable=True),
        sa.Column("volume", sa.BigInteger(), nullable=True),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("provider_response_hash", sa.Text(), nullable=False),
        sa.UniqueConstraint(
            "ibkr_conid",
            "as_of_date",
            "provider",
            name="uq_market_data_eod_snapshots_conid_date_provider",
        ),
        sa.CheckConstraint(
            "provider IN ('eodhd', 'manual', 'unknown')",
            name="ck_market_data_eod_snapshots_provider",
        ),
    )
    op.create_index(
        "ix_market_data_eod_snapshots_conid_date",
        "market_data_eod_snapshots",
        ["ibkr_conid", sa.text("as_of_date DESC")],
    )

    op.create_table(
        "fx_rates",
        sa.Column("base_currency", sa.Text(), primary_key=True),
        sa.Column("quote_currency", sa.Text(), primary_key=True),
        sa.Column("as_of_date", sa.Date(), primary_key=True),
        sa.Column("provider", sa.Text(), primary_key=True),
        sa.Column("rate", _FX, nullable=False),
        sa.Column(
            "ingested_ts", sa.DateTime(timezone=True), nullable=False
        ),
        sa.CheckConstraint(
            "provider IN ('eodhd', 'ecb', 'manual')",
            name="ck_fx_rates_provider",
        ),
    )

    op.create_table(
        "provider_call_audit",
        sa.Column("audit_id", sa.Text(), primary_key=True),
        sa.Column("called_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("provider", sa.Text(), nullable=False),
        sa.Column("endpoint", sa.Text(), nullable=False),
        sa.Column("request_params_json", sa.JSON(), nullable=True),
        sa.Column("response_status", sa.Integer(), nullable=True),
        sa.Column("response_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("error_class", sa.Text(), nullable=True),
        sa.Column("error_details_json", sa.JSON(), nullable=True),
        sa.Column("account_id", sa.Text(), nullable=True),
        sa.Column("triggered_by_run_id", sa.Text(), nullable=True),
    )
    op.create_index(
        "ix_provider_call_audit_called_at",
        "provider_call_audit",
        [sa.text("called_at DESC")],
    )
    op.create_index(
        "ix_provider_call_audit_run_id",
        "provider_call_audit",
        ["triggered_by_run_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_provider_call_audit_run_id",
        table_name="provider_call_audit",
    )
    op.drop_index(
        "ix_provider_call_audit_called_at",
        table_name="provider_call_audit",
    )
    op.drop_table("provider_call_audit")
    op.drop_table("fx_rates")
    op.drop_index(
        "ix_market_data_eod_snapshots_conid_date",
        table_name="market_data_eod_snapshots",
    )
    op.drop_table("market_data_eod_snapshots")
