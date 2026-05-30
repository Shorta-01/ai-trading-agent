"""Tests for worker-side central error capture + the scheduler job listener."""

from __future__ import annotations

from ai_trading_agent_storage import (
    MigrationReadinessReport,
    MigrationReadinessStatus,
    SqlAlchemySystemEventRepository,
)
from ai_trading_agent_storage.metadata import metadata
from sqlalchemy import create_engine, text

from portfolio_outlook_worker.config import (
    IbkrSettings,
    SchedulerSettings,
    StorageSettings,
)
from portfolio_outlook_worker.error_capture import record_worker_error


def _report() -> MigrationReadinessReport:
    return MigrationReadinessReport(
        status=MigrationReadinessStatus.MIGRATIONS_CURRENT,
        database_connected=True,
        migrations_checked_against_database=True,
        offline_inventory_valid=True,
        latest_expected_revision_id="0058_runtime_config_scheduler",
        database_revision_id="0058_runtime_config_scheduler",
        persistence_allowed=True,
        blocks_runtime_writes=False,
        explanation_nl="test",
    )


def _seed(tmp_path) -> StorageSettings:  # type: ignore[no-untyped-def]
    db_url = f"sqlite+pysqlite:///{tmp_path / 'worker_errors.sqlite'}"
    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0058_runtime_config_scheduler')"
            )
        )
    return StorageSettings(enabled=True, database_url=db_url, writes_enabled=True)


def _open_events(db_url: str):  # type: ignore[no-untyped-def]
    engine = create_engine(db_url)
    with engine.connect() as conn:
        repo = SqlAlchemySystemEventRepository(conn, _report())
        return repo.list_open_events().records


def test_record_worker_error_persists(tmp_path) -> None:  # type: ignore[no-untyped-def]
    storage = _seed(tmp_path)
    record_worker_error(
        storage_settings=storage,
        source_component="scheduler:hourly",
        event_code="scheduler_job_error",
        message="ValueError: boom",
        technical_summary="ValueError: boom",
        stack_trace="Traceback ... ValueError: boom",
    )
    events = _open_events(storage.database_url or "")
    assert len(events) == 1
    event = events[0]
    assert event.severity == "error"
    assert event.source_service == "worker"
    assert event.event_code == "scheduler_job_error"
    assert "boom" in (event.stack_trace_redacted or "")


def test_record_worker_error_noop_when_disabled() -> None:
    # Must not raise even with nowhere to persist.
    record_worker_error(
        storage_settings=StorageSettings(enabled=False),
        source_component="x",
        event_code="y",
        message="z",
    )


def test_scheduler_on_job_error_records(tmp_path) -> None:  # type: ignore[no-untyped-def]
    from apscheduler.schedulers.background import BackgroundScheduler

    from portfolio_outlook_worker.scheduler import PortfolioScheduler

    storage = _seed(tmp_path)

    class _StubGateway:
        def is_connected(self) -> bool:
            return False

    scheduler = PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=storage,
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=True, timezone="Europe/Brussels", heartbeat_interval_seconds=60
        ),
        worker_id="worker-test",
        scheduler_factory=lambda **_: BackgroundScheduler(),
    )

    class _Event:
        exception = ValueError("kaboom")
        traceback = "Traceback ... ValueError: kaboom"
        job_id = "hourly"

    scheduler._on_job_error(_Event())

    events = _open_events(storage.database_url or "")
    assert any(e.event_code == "scheduler_job_error" for e in events)
    assert any(e.source_component == "scheduler:hourly" for e in events)
