"""Task 127 — scheduler audit + state repository tests."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import create_engine

from ai_trading_agent_storage import (
    ScheduledRunAuditEntry,
    SchedulerStateEntry,
    SqlAlchemyScheduledRunAuditRepository,
    SqlAlchemySchedulerStateRepository,
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
        latest_expected_revision_id="0046_scheduled_run_audit_and_scheduler_state",
        database_revision_id=(
            "0046_scheduled_run_audit_and_scheduler_state" if allowed else None
        ),
        persistence_allowed=allowed,
        blocks_runtime_writes=(not allowed),
        explanation_nl="test",
    )


_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


def _entry(
    *,
    run_id: str = "run-1",
    offset_sec: int = 0,
    run_type: str = "hourly_delta",
    mode_detected: str = "normal",
    outcome: str = "completed",
    ibkr_account_id: str | None = "DU1234567",
    duration_ms: int | None = 12,
    next_scheduled_at: datetime | None = None,
    error_details_json: str | None = None,
) -> ScheduledRunAuditEntry:
    return ScheduledRunAuditEntry(
        run_id=run_id,
        run_at=_BASE + timedelta(seconds=offset_sec),
        run_type=run_type,
        ibkr_account_id=ibkr_account_id,
        mode_detected=mode_detected,
        duration_ms=duration_ms,
        outcome=outcome,
        error_details_json=error_details_json,
        next_scheduled_at=next_scheduled_at,
    )


# ---- audit roundtrip + ordering ----------------------------------


def test_append_and_list_recent_newest_first() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyScheduledRunAuditRepository(conn, _report(True))

        repo.append(_entry(run_id="run-old", offset_sec=0))
        repo.append(_entry(run_id="run-new", offset_sec=3600))

        rows = repo.list_recent(limit=10)
        assert len(rows.records) == 2
        assert rows.records[0].run_id == "run-new"
        assert rows.records[1].run_id == "run-old"


def test_list_by_run_type_filters_correctly() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyScheduledRunAuditRepository(conn, _report(True))

        repo.append(_entry(run_id="r1", run_type="hourly_delta"))
        repo.append(_entry(run_id="r2", offset_sec=3600, run_type="morning_briefing"))
        repo.append(_entry(run_id="r3", offset_sec=7200, run_type="pre_briefing"))

        morning = repo.list_by_run_type(run_type="morning_briefing")
        assert len(morning.records) == 1
        assert morning.records[0].run_id == "r2"

        pre = repo.list_by_run_type(run_type="pre_briefing")
        assert len(pre.records) == 1
        assert pre.records[0].run_id == "r3"


def test_repository_exposes_no_update_or_delete_methods() -> None:
    """Task 127 product lock §5: scheduled-run audit is append-only."""

    forbidden = {"update", "delete", "upsert", "save_or_update"}
    public_methods = {
        name
        for name in dir(SqlAlchemyScheduledRunAuditRepository)
        if not name.startswith("_")
    }
    assert forbidden.isdisjoint(public_methods)


def test_entry_persists_error_details_json_roundtrip() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemyScheduledRunAuditRepository(conn, _report(True))
        repo.append(
            _entry(
                run_id="r-err",
                outcome="error",
                mode_detected="disconnected",
                error_details_json=json.dumps(
                    {"reason": "ibkr_session_not_connected"}
                ),
            )
        )
        rows = repo.list_recent(limit=1)
        assert rows.records[0].outcome == "error"
        assert rows.records[0].error_details_json is not None
        assert "ibkr_session_not_connected" in rows.records[0].error_details_json


# ---- record invariants -------------------------------------------


def test_entry_rejects_unknown_run_type() -> None:
    with pytest.raises(ValueError, match="run_type"):
        _entry(run_type="freaky")


def test_entry_rejects_unknown_mode_detected() -> None:
    with pytest.raises(ValueError, match="mode_detected"):
        _entry(mode_detected="freaky")


def test_entry_rejects_unknown_outcome() -> None:
    with pytest.raises(ValueError, match="outcome"):
        _entry(outcome="freaky")


def test_entry_rejects_negative_duration() -> None:
    with pytest.raises(ValueError, match="duration_ms"):
        _entry(duration_ms=-1)


# ---- scheduler_state upsert --------------------------------------


def test_scheduler_state_upsert_inserts_then_updates() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemySchedulerStateRepository(conn, _report(True))

        first = SchedulerStateEntry(
            worker_id="worker-a",
            started_at=_BASE,
            last_heartbeat_at=_BASE,
            next_pre_briefing_at=_BASE + timedelta(hours=23),
            next_hourly_at=_BASE + timedelta(hours=1),
        )
        repo.upsert(first)
        assert len(repo.list_all().records) == 1

        # Heartbeat update — should not insert a second row.
        repo.upsert(
            SchedulerStateEntry(
                worker_id="worker-a",
                started_at=_BASE,
                last_heartbeat_at=_BASE + timedelta(minutes=1),
                next_pre_briefing_at=_BASE + timedelta(hours=23),
                next_hourly_at=_BASE + timedelta(hours=1),
            )
        )
        rows = repo.list_all()
        assert len(rows.records) == 1
        # SQLite strips tzinfo on the round-trip; compare naive components.
        actual = rows.records[0].last_heartbeat_at
        expected = (_BASE + timedelta(minutes=1)).replace(tzinfo=None)
        assert actual.replace(tzinfo=None) == expected


def test_scheduler_state_multiple_workers_coexist() -> None:
    engine = create_engine("sqlite+pysqlite:///:memory:")
    with engine.connect() as conn:
        metadata.create_all(conn)
        repo = SqlAlchemySchedulerStateRepository(conn, _report(True))
        for worker_id in ("worker-a", "worker-b"):
            repo.upsert(
                SchedulerStateEntry(
                    worker_id=worker_id,
                    started_at=_BASE,
                    last_heartbeat_at=_BASE,
                    next_pre_briefing_at=None,
                    next_hourly_at=None,
                )
            )
        ids = {r.worker_id for r in repo.list_all().records}
        assert ids == {"worker-a", "worker-b"}
