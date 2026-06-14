"""SQL roundtrip tests for the V1.2 §W orchestrator scoring verdict
repository.

Verifies the upsert / read / list contract for the new
``orchestrator_scoring_verdicts`` table the worker writes parallel
to the live suggestion engine.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    OrchestratorScoringVerdictRecord,
    SaveOrchestratorScoringVerdictRequest,
    SqlAlchemyOrchestratorScoringVerdictRepository,
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
        latest_expected_revision_id="0079_macro_index_snapshots",
        database_revision_id=(
            "0079_macro_index_snapshots" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_BASE_TS = datetime(2026, 6, 12, 9, 0, tzinfo=UTC)


def _request(
    *,
    verdict_id: str = "v1",
    symbol: str = "AAPL",
    forecast_id: str | None = "fc-001",
    decision: str = "suggest",
    blocking_reason: str | None = None,
    generated_at: datetime = _BASE_TS,
) -> SaveOrchestratorScoringVerdictRequest:
    return SaveOrchestratorScoringVerdictRequest(
        verdict_id=verdict_id,
        ibkr_account_ref="DU1234567",
        symbol=symbol,
        ibkr_conid=265598,
        forecast_id=forecast_id,
        generated_at=generated_at,
        decision=decision,
        blocking_reason=blocking_reason,
        details_json={
            "macro": {"favorable": True, "vix": "15.0"},
            "risk_universe": {"allowed": True},
            "proposed_position_eur": "62500",
        },
        summary_nl="Koop 249 stuks AAPL op €100,00 — verkoop bij €104,73.",
    )


def _make_repo() -> tuple[
    SqlAlchemyOrchestratorScoringVerdictRepository, object
]:
    engine = create_engine("sqlite:///:memory:", future=True)
    metadata.create_all(engine)
    conn = engine.connect()
    return SqlAlchemyOrchestratorScoringVerdictRepository(
        conn, _report(True)
    ), conn


# ---- decision vocabulary validation ----------------------------------


def test_record_rejects_unknown_decision() -> None:
    with pytest.raises(ValueError, match="not in locked"):
        OrchestratorScoringVerdictRecord(
            verdict_id="v1",
            ibkr_account_ref="DU1",
            symbol="AAPL",
            ibkr_conid=1,
            forecast_id="fc1",
            generated_at=_BASE_TS,
            decision="not_a_real_code",
            blocking_reason=None,
            details_json={},
            summary_nl="x",
        )


def test_record_accepts_every_locked_decision() -> None:
    locked = [
        "suggest",
        "skip_macro_regime",
        "skip_risk_universe",
        "skip_earnings_window",
        "skip_confidence_gate",
        "skip_below_conviction_floor",
        "skip_sector_concentration",
        "skip_pair_build",
    ]
    for code in locked:
        OrchestratorScoringVerdictRecord(
            verdict_id="v",
            ibkr_account_ref="DU1",
            symbol="AAPL",
            ibkr_conid=1,
            forecast_id=None,
            generated_at=_BASE_TS,
            decision=code,
            blocking_reason=None,
            details_json={},
            summary_nl="x",
        )


# ---- upsert + read ---------------------------------------------------


def test_upsert_then_get_latest() -> None:
    repo, conn = _make_repo()
    write = repo.upsert_verdict(_request())
    assert write.accepted is True
    assert write.record_id == "v1"
    got = repo.get_latest_verdict_for_account("DU1234567")
    assert got.found is True
    assert got.record is not None
    assert got.record.symbol == "AAPL"
    assert got.record.decision == "suggest"
    conn.close()


def test_no_records_returns_not_found() -> None:
    repo, conn = _make_repo()
    got = repo.get_latest_verdict_for_account("DU1234567")
    assert got.found is False
    assert got.record is None
    conn.close()


def test_upsert_overwrites_existing_verdict_for_same_forecast() -> None:
    repo, conn = _make_repo()
    repo.upsert_verdict(_request(verdict_id="v1", decision="suggest"))
    repo.upsert_verdict(
        _request(
            verdict_id="v2",
            decision="skip_confidence_gate",
            blocking_reason="below_confidence_threshold",
        )
    )
    # Only the second remains for this (account, symbol, forecast_id).
    listed = repo.list_verdicts_for_account(
        ibkr_account_ref="DU1234567", limit=10
    )
    assert len(listed.records) == 1
    assert listed.records[0].decision == "skip_confidence_gate"
    conn.close()


def test_different_forecast_creates_separate_row() -> None:
    repo, conn = _make_repo()
    repo.upsert_verdict(
        _request(verdict_id="v1", forecast_id="fc-001")
    )
    repo.upsert_verdict(
        _request(
            verdict_id="v2",
            forecast_id="fc-002",
            generated_at=_BASE_TS.replace(hour=10),
        )
    )
    listed = repo.list_verdicts_for_account(
        ibkr_account_ref="DU1234567", limit=10
    )
    assert len(listed.records) == 2
    conn.close()


def test_list_orders_newest_first() -> None:
    repo, conn = _make_repo()
    repo.upsert_verdict(
        _request(verdict_id="v1", symbol="AAPL", generated_at=_BASE_TS)
    )
    repo.upsert_verdict(
        _request(
            verdict_id="v2",
            symbol="MSFT",
            forecast_id="fc-002",
            generated_at=_BASE_TS.replace(hour=10),
        )
    )
    listed = repo.list_verdicts_for_account(
        ibkr_account_ref="DU1234567", limit=10
    )
    assert [r.symbol for r in listed.records] == ["MSFT", "AAPL"]
    conn.close()


def test_list_respects_limit() -> None:
    repo, conn = _make_repo()
    for i in range(5):
        repo.upsert_verdict(
            _request(
                verdict_id=f"v{i}",
                symbol=f"TICK{i}",
                forecast_id=f"fc-{i:03d}",
                generated_at=_BASE_TS.replace(minute=i),
            )
        )
    listed = repo.list_verdicts_for_account(
        ibkr_account_ref="DU1234567", limit=3
    )
    assert len(listed.records) == 3
    conn.close()


def test_list_rejects_non_positive_limit() -> None:
    repo, conn = _make_repo()
    with pytest.raises(ValueError):
        repo.list_verdicts_for_account(
            ibkr_account_ref="DU1234567", limit=0
        )
    conn.close()


def test_account_isolation() -> None:
    repo, conn = _make_repo()
    repo.upsert_verdict(_request(verdict_id="v1"))
    # Different account → empty.
    listed = repo.list_verdicts_for_account(
        ibkr_account_ref="DU9999999", limit=10
    )
    assert len(listed.records) == 0
    conn.close()
