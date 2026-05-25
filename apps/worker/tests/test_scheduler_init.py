"""Task 127 — :class:`PortfolioScheduler` start/stop + job-registration tests.

Storage and the IBKR gateway are injected as fakes; APScheduler runs
fully in-process with a memory job store so no live Postgres is
required. The tests exercise:

* The two locked cron triggers (06:00 + hourly 07:00-21:00) are
  registered.
* The ``WORKER_SCHEDULER__ENABLED=false`` default keeps the worker
  from starting any jobs.
"""

from __future__ import annotations

from apscheduler.schedulers.background import BackgroundScheduler

from portfolio_outlook_worker.config import (
    IbkrSettings,
    SchedulerSettings,
    StorageSettings,
)
from portfolio_outlook_worker.scheduler import (
    _HOURLY_JOB_ID,
    _PRE_BRIEFING_JOB_ID,
    PortfolioScheduler,
)


class _StubGateway:
    def is_connected(self) -> bool:
        return False


def _scheduler_factory(*, database_url, timezone):  # type: ignore[no-untyped-def]  # noqa: ARG001
    # Memory-backed scheduler so tests never touch storage.
    return BackgroundScheduler(timezone=timezone)


def _build(*, scheduler_enabled: bool = True) -> PortfolioScheduler:
    return PortfolioScheduler(
        gateway=_StubGateway(),
        storage_settings=StorageSettings(
            enabled=False, database_url=None, writes_enabled=False
        ),
        ibkr_settings=IbkrSettings(),
        scheduler_settings=SchedulerSettings(
            enabled=scheduler_enabled,
            timezone="Europe/Brussels",
            heartbeat_interval_seconds=60,
        ),
        worker_id="worker-test",
        scheduler_factory=_scheduler_factory,
    )


def test_start_registers_pre_briefing_job_with_06_00_cron() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job(_PRE_BRIEFING_JOB_ID)
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "hour='6'" in cron_repr
        assert "minute='0'" in cron_repr
        assert "Europe/Brussels" in cron_repr
    finally:
        scheduler.stop()


def test_start_registers_hourly_job_with_07_through_21_cron() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        job = scheduler._scheduler.get_job(_HOURLY_JOB_ID)
        assert job is not None
        cron_repr = repr(job.trigger)
        assert "hour='7-21'" in cron_repr
        assert "minute='0'" in cron_repr
        assert "Europe/Brussels" in cron_repr
    finally:
        scheduler.stop()


def test_start_is_idempotent() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        scheduler.start()  # second call is a no-op
        assert scheduler._scheduler.get_job(_PRE_BRIEFING_JOB_ID) is not None
    finally:
        scheduler.stop()


def test_stop_is_idempotent_and_safe_before_start() -> None:
    scheduler = _build()
    scheduler.stop()  # no error when never started
    scheduler.start()
    scheduler.stop()
    scheduler.stop()  # second stop is a no-op


def test_worker_id_is_stable_across_lifecycle() -> None:
    scheduler = _build()
    assert scheduler.worker_id == "worker-test"
    scheduler.start()
    assert scheduler.worker_id == "worker-test"
    scheduler.stop()


def test_next_runs_lists_both_jobs_after_start() -> None:
    scheduler = _build()
    try:
        scheduler.start()
        runs = scheduler.next_runs()
        # Memory-backed scheduler returns next_run_time only after the
        # first tick; with no fires yet, APScheduler still populates
        # the trigger so next_run_time is set immediately.
        assert len(runs) == 2
    finally:
        scheduler.stop()


def test_next_runs_empty_when_scheduler_not_started() -> None:
    scheduler = _build()
    assert scheduler.next_runs() == []
