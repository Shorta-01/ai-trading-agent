"""Task 127 — scheduler API route tests."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

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
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


_BASE = datetime(2026, 5, 25, 7, 0, tzinfo=UTC)


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


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


# ---- status route ------------------------------------------------


def test_status_returns_disabled_when_storage_off() -> None:
    response = client.get("/scheduler/v127/status")
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is False
    assert body["last_run_at"] is None
    assert body["next_runs"] == []
    assert body["safe_for_orders"] is False


def test_runs_returns_503_with_dutch_body_when_storage_off() -> None:
    response = client.get("/scheduler/v127/runs")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


def test_status_aggregates_state_and_audit_when_storage_live(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    db_path = tmp_path / "scheduler.sqlite"
    db_url = f"sqlite+pysqlite:///{db_path}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True

    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        state_repo = SqlAlchemySchedulerStateRepository(conn, _report(True))
        state_repo.upsert(
            SchedulerStateEntry(
                worker_id="worker-A",
                started_at=_BASE,
                last_heartbeat_at=_BASE,
                next_pre_briefing_at=_BASE + timedelta(hours=23),
                next_hourly_at=_BASE + timedelta(hours=1),
            )
        )
        audit_repo = SqlAlchemyScheduledRunAuditRepository(conn, _report(True))
        audit_repo.append(
            ScheduledRunAuditEntry(
                run_id="srun-1",
                run_at=_BASE,
                run_type="hourly_delta",
                ibkr_account_id="DU1234567",
                mode_detected="cold_start",
                duration_ms=12,
                outcome="completed",
                error_details_json=None,
                next_scheduled_at=_BASE + timedelta(hours=1),
            )
        )

    response = client.get("/scheduler/v127/status")
    body = response.json()
    assert response.status_code == 200
    assert body["enabled"] is True
    assert body["last_run_type"] == "hourly_delta"
    assert body["last_mode_detected"] == "cold_start"
    assert body["last_outcome"] == "completed"
    assert len(body["next_runs"]) == 2
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False


def test_runs_returns_paged_audit_rows_when_storage_live(
    tmp_path,  # type: ignore[no-untyped-def]
) -> None:
    db_path = tmp_path / "scheduler.sqlite"
    db_url = f"sqlite+pysqlite:///{db_path}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True

    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        audit_repo = SqlAlchemyScheduledRunAuditRepository(conn, _report(True))
        for index in range(3):
            audit_repo.append(
                ScheduledRunAuditEntry(
                    run_id=f"srun-{index}",
                    run_at=_BASE + timedelta(hours=index),
                    run_type="hourly_delta",
                    ibkr_account_id="DU1234567",
                    mode_detected="normal",
                    duration_ms=5,
                    outcome="completed",
                    error_details_json=None,
                    next_scheduled_at=None,
                )
            )

    response = client.get("/scheduler/v127/runs?limit=2")
    body = response.json()
    assert response.status_code == 200
    assert len(body["items"]) == 2
    # Newest first.
    assert body["items"][0]["run_id"] == "srun-2"
    assert body["items"][1]["run_id"] == "srun-1"


def test_runs_rejects_limit_below_one() -> None:
    response = client.get("/scheduler/v127/runs?limit=0")
    assert response.status_code == 422


def test_runs_rejects_limit_above_max() -> None:
    response = client.get("/scheduler/v127/runs?limit=999")
    assert response.status_code == 422
