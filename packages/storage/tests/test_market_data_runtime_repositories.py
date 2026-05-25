"""Task 129 — EOD market-data + FX + provider-audit repository tests."""

from __future__ import annotations

import json
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage import (
    FxRateRecord,
    MarketDataEodSnapshotEntry,
    ProviderCallAuditEntry,
    SqlAlchemyFxRateRepository,
    SqlAlchemyMarketDataEodSnapshotRepository,
    SqlAlchemyProviderCallAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)


def _report(allowed: bool) -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=(
            MigrationReadinessStatus.MIGRATIONS_CURRENT
            if allowed
            else MigrationReadinessStatus.NOT_CONNECTED
        ),
        database_connected=allowed,
        migrations_checked_against_database=allowed,
        offline_inventory_valid=True,
        latest_expected_revision_id="0048_market_data_eod_and_fx_runtime",
        database_revision_id=(
            "0048_market_data_eod_and_fx_runtime" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_BASE_DATE = date(2026, 5, 24)
_BASE_TS = datetime(2026, 5, 24, 17, 0, tzinfo=UTC)


def _snapshot(
    *,
    snapshot_id: str = "snap-1",
    ibkr_conid: str = "12345",
    as_of_date: date = _BASE_DATE,
    close: Decimal = Decimal("640.123456"),
    provider: str = "eodhd",
) -> MarketDataEodSnapshotEntry:
    return MarketDataEodSnapshotEntry(
        snapshot_id=snapshot_id,
        ibkr_conid=ibkr_conid,
        symbol="ASML",
        exchange="AEB",
        currency_local="EUR",
        as_of_date=as_of_date,
        as_of_close_ts=_BASE_TS,
        ingested_ts=_BASE_TS,
        open_local=Decimal("635.0"),
        high_local=Decimal("642.5"),
        low_local=Decimal("634.0"),
        close_local=close,
        adj_close_local=close,
        volume=123456,
        provider=provider,
        provider_response_hash="deadbeef" * 8,
    )


# ---- market_data_eod_snapshots ----------------------------------


def test_eod_append_then_get_for_date_preserves_decimal() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        repo.append(_snapshot(close=Decimal("640.123456")))

        found = repo.get_for_date(
            ibkr_conid="12345", as_of_date=_BASE_DATE
        )
        assert found is not None
        assert found.close_local == Decimal("640.123456")


def test_eod_unique_constraint_blocks_duplicate_conid_date_provider() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        repo.append(_snapshot(snapshot_id="snap-A"))
        with pytest.raises(IntegrityError):
            repo.append(_snapshot(snapshot_id="snap-B"))  # same conid+date+provider


def test_eod_get_latest_by_conid_returns_newest_date() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        repo.append(
            _snapshot(snapshot_id="snap-1", as_of_date=_BASE_DATE - timedelta(days=2))
        )
        repo.append(
            _snapshot(snapshot_id="snap-2", as_of_date=_BASE_DATE - timedelta(days=1))
        )
        repo.append(
            _snapshot(snapshot_id="snap-3", as_of_date=_BASE_DATE)
        )

        latest = repo.get_latest_by_conid(ibkr_conid="12345")
        assert latest is not None
        assert latest.snapshot_id == "snap-3"


def test_eod_list_latest_per_conid_fans_out() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyMarketDataEodSnapshotRepository(conn, _report(True))
        repo.append(_snapshot(snapshot_id="A", ibkr_conid="111"))
        repo.append(_snapshot(snapshot_id="B", ibkr_conid="222"))
        repo.append(_snapshot(snapshot_id="C", ibkr_conid="333"))

        rows = repo.list_latest_per_conid(
            ibkr_conids=("111", "222", "missing")
        )
        assert {r.snapshot_id for r in rows.records} == {"A", "B"}


def test_eod_rejects_negative_close() -> None:
    with pytest.raises(ValueError, match="close_local"):
        _snapshot(close=Decimal("-1"))


def test_eod_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="provider"):
        MarketDataEodSnapshotEntry(
            snapshot_id="x",
            ibkr_conid="1",
            symbol="X",
            exchange=None,
            currency_local="EUR",
            as_of_date=_BASE_DATE,
            as_of_close_ts=_BASE_TS,
            ingested_ts=_BASE_TS,
            open_local=None,
            high_local=None,
            low_local=None,
            close_local=Decimal("1"),
            adj_close_local=None,
            volume=None,
            provider="freaky",
            provider_response_hash="x",
        )


# ---- fx_rates ----------------------------------------------------


def test_fx_upsert_inserts_then_updates() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyFxRateRepository(conn, _report(True))

        repo.upsert(
            FxRateRecord(
                base_currency="USD",
                quote_currency="EUR",
                as_of_date=_BASE_DATE,
                rate=Decimal("0.91"),
                ingested_ts=_BASE_TS,
                provider="eodhd",
            )
        )
        repo.upsert(
            FxRateRecord(
                base_currency="USD",
                quote_currency="EUR",
                as_of_date=_BASE_DATE,
                rate=Decimal("0.92"),
                ingested_ts=_BASE_TS + timedelta(hours=1),
                provider="eodhd",
            )
        )
        found = repo.get_rate(
            base_currency="USD",
            quote_currency="EUR",
            as_of_date=_BASE_DATE,
        )
        assert found is not None
        assert found.rate == Decimal("0.92")


def test_fx_get_latest_returns_newest_date() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyFxRateRepository(conn, _report(True))
        repo.upsert(
            FxRateRecord(
                base_currency="GBP",
                quote_currency="EUR",
                as_of_date=_BASE_DATE - timedelta(days=2),
                rate=Decimal("1.16"),
                ingested_ts=_BASE_TS,
                provider="eodhd",
            )
        )
        repo.upsert(
            FxRateRecord(
                base_currency="GBP",
                quote_currency="EUR",
                as_of_date=_BASE_DATE,
                rate=Decimal("1.18"),
                ingested_ts=_BASE_TS,
                provider="eodhd",
            )
        )
        latest = repo.get_latest(
            base_currency="GBP", quote_currency="EUR"
        )
        assert latest is not None
        assert latest.as_of_date == _BASE_DATE
        assert latest.rate == Decimal("1.18")


def test_fx_rejects_unknown_provider() -> None:
    with pytest.raises(ValueError, match="provider"):
        FxRateRecord(
            base_currency="USD",
            quote_currency="EUR",
            as_of_date=_BASE_DATE,
            rate=Decimal("0.91"),
            ingested_ts=_BASE_TS,
            provider="bloomberg",
        )


def test_fx_rejects_bad_currency_code_length() -> None:
    with pytest.raises(ValueError, match="ISO"):
        FxRateRecord(
            base_currency="DOLLAR",
            quote_currency="EUR",
            as_of_date=_BASE_DATE,
            rate=Decimal("0.91"),
            ingested_ts=_BASE_TS,
            provider="eodhd",
        )


# ---- provider_call_audit -----------------------------------------


def test_audit_append_then_list_recent_newest_first() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyProviderCallAuditRepository(conn, _report(True))

        repo.append(
            ProviderCallAuditEntry(
                audit_id="aud-1",
                called_at=_BASE_TS,
                provider="eodhd",
                endpoint="/api/eod/ASML.AEB",
                request_params_json=json.dumps({"from": "2026-05-24"}),
                response_status=200,
                response_size_bytes=512,
                duration_ms=150,
                error_class=None,
                error_details_json=None,
                account_id="DU1234567",
                triggered_by_run_id="srun-1",
            )
        )
        repo.append(
            ProviderCallAuditEntry(
                audit_id="aud-2",
                called_at=_BASE_TS + timedelta(seconds=2),
                provider="eodhd",
                endpoint="/api/eod/VWCE.XETRA",
                request_params_json=None,
                response_status=503,
                response_size_bytes=None,
                duration_ms=2000,
                error_class="HTTPStatusError",
                error_details_json=json.dumps({"reason": "upstream 503"}),
                account_id="DU1234567",
                triggered_by_run_id="srun-1",
            )
        )

        rows = repo.list_recent(limit=10)
        assert [r.audit_id for r in rows.records] == ["aud-2", "aud-1"]


def test_audit_list_for_run_filters_correctly() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyProviderCallAuditRepository(conn, _report(True))
        for index, run_id in enumerate(("run-A", "run-A", "run-B")):
            repo.append(
                ProviderCallAuditEntry(
                    audit_id=f"aud-{index}",
                    called_at=_BASE_TS + timedelta(seconds=index),
                    provider="eodhd",
                    endpoint="/api/eod/X",
                    request_params_json=None,
                    response_status=200,
                    response_size_bytes=100,
                    duration_ms=50,
                    error_class=None,
                    error_details_json=None,
                    account_id="DU1234567",
                    triggered_by_run_id=run_id,
                )
            )
        rows = repo.list_for_run(run_id="run-A")
        assert len(rows.records) == 2
        assert all(r.triggered_by_run_id == "run-A" for r in rows.records)


def test_audit_repository_exposes_no_update_or_delete_methods() -> None:
    forbidden = {"update", "delete", "save_or_update", "upsert"}
    public_methods = {
        name
        for name in dir(SqlAlchemyProviderCallAuditRepository)
        if not name.startswith("_")
    }
    assert forbidden.isdisjoint(public_methods)


def test_audit_rejects_invalid_status_code() -> None:
    with pytest.raises(ValueError, match="response_status"):
        ProviderCallAuditEntry(
            audit_id="x",
            called_at=_BASE_TS,
            provider="eodhd",
            endpoint="/api/eod/X",
            request_params_json=None,
            response_status=999,
            response_size_bytes=None,
            duration_ms=None,
            error_class=None,
            error_details_json=None,
            account_id=None,
            triggered_by_run_id=None,
        )
