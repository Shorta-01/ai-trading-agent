"""Task 135a — reconciliation_run_audit repository tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError

from ai_trading_agent_storage import (
    ReconciliationRunAuditEntry,
    SqlAlchemyReconciliationRunAuditRepository,
)
from ai_trading_agent_storage.metadata import metadata
from ai_trading_agent_storage.migration_readiness import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
)

_LATEST = "0053_reconciliation_audit_and_manual_review"
_BASE_TS = datetime(2026, 5, 26, 9, 0, tzinfo=UTC)


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id=_LATEST,
        database_revision_id=_LATEST,
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _conn():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    conn = engine.connect()
    metadata.create_all(conn)
    return conn


def _entry(
    *,
    run_id: str = "run-1",
    started_at: datetime | None = None,
    completed_at: datetime | None = None,
    account_id: str = "DU1234567",
    pass_a: int = 0,
    pass_b: int = 0,
    pass_c: int = 0,
    divergences: int = 0,
    mode_detected: str = "completed",
    error_json: dict[str, object] | None = None,
) -> ReconciliationRunAuditEntry:
    return ReconciliationRunAuditEntry(
        reconciliation_run_id=run_id,
        started_at=started_at or _BASE_TS,
        completed_at=completed_at,
        account_id=account_id,
        pass_a_orphaned_count=pass_a,
        pass_b_stale_count=pass_b,
        pass_c_timeout_count=pass_c,
        divergences_found=divergences,
        mode_detected=mode_detected,
        error_details_json=error_json,
    )


def test_append_returns_entry_with_autoincrement_id() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        stored = repo.append(_entry())
        assert stored.id is not None
        assert stored.reconciliation_run_id == "run-1"
        assert stored.completed_at is None
        assert stored.mode_detected == "completed"


def test_unique_run_id_rejects_duplicate() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        repo.append(_entry(run_id="dup"))
        with pytest.raises(IntegrityError):
            repo.append(_entry(run_id="dup"))


def test_complete_run_updates_counts_and_timestamp() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        repo.append(_entry(run_id="r-tick-1"))
        completed_at = _BASE_TS + timedelta(seconds=30)
        updated = repo.complete_run(
            reconciliation_run_id="r-tick-1",
            completed_at=completed_at,
            pass_a_orphaned_count=1,
            pass_b_stale_count=2,
            pass_c_timeout_count=3,
            divergences_found=6,
            mode_detected="completed",
        )
        # SQLite strips tzinfo on the round-trip; compare naive components.
        assert updated.completed_at is not None
        assert updated.completed_at.replace(
            tzinfo=None
        ) == completed_at.replace(tzinfo=None)
        assert updated.pass_a_orphaned_count == 1
        assert updated.pass_b_stale_count == 2
        assert updated.pass_c_timeout_count == 3
        assert updated.divergences_found == 6


def test_complete_run_records_error_mode_with_details() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        repo.append(_entry(run_id="r-err"))
        updated = repo.complete_run(
            reconciliation_run_id="r-err",
            completed_at=_BASE_TS + timedelta(seconds=1),
            pass_a_orphaned_count=0,
            pass_b_stale_count=0,
            pass_c_timeout_count=0,
            divergences_found=0,
            mode_detected="error",
            error_details_json={"class": "TimeoutError", "msg": "boom"},
        )
        assert updated.mode_detected == "error"
        assert updated.error_details_json == {
            "class": "TimeoutError",
            "msg": "boom",
        }


def test_complete_run_unknown_id_raises_lookup_error() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        with pytest.raises(LookupError):
            repo.complete_run(
                reconciliation_run_id="ghost",
                completed_at=_BASE_TS,
                pass_a_orphaned_count=0,
                pass_b_stale_count=0,
                pass_c_timeout_count=0,
                divergences_found=0,
                mode_detected="completed",
            )


def test_get_latest_for_account_returns_most_recent() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        repo.append(_entry(run_id="r-old", started_at=_BASE_TS))
        repo.append(
            _entry(
                run_id="r-new",
                started_at=_BASE_TS + timedelta(seconds=60),
            )
        )
        latest = repo.get_latest_for_account("DU1234567")
        assert latest is not None
        assert latest.reconciliation_run_id == "r-new"


def test_get_latest_for_account_returns_none_when_no_runs() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        assert repo.get_latest_for_account("DU0000000") is None


def test_list_for_account_orders_newest_first_and_limits() -> None:
    with _conn() as conn:
        repo = SqlAlchemyReconciliationRunAuditRepository(conn, _report())
        for index in range(3):
            repo.append(
                _entry(
                    run_id=f"r-{index}",
                    started_at=_BASE_TS + timedelta(seconds=index),
                )
            )
        rows = repo.list_for_account(account_id="DU1234567", limit=2)
        assert len(rows) == 2
        assert rows[0].reconciliation_run_id == "r-2"
        assert rows[1].reconciliation_run_id == "r-1"


def test_invalid_mode_detected_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(mode_detected="green")


def test_negative_counts_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(pass_a=-1)
    with pytest.raises(ValueError):
        _entry(divergences=-1)


def test_empty_run_id_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(run_id="")


def test_empty_account_id_rejected_at_dataclass_layer() -> None:
    with pytest.raises(ValueError):
        _entry(account_id="")
