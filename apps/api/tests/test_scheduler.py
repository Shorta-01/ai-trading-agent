"""Tests for the APScheduler integration (Slice 13)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ai_trading_agent_storage import SchedulerRunRecord

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.scheduler import (
    DAILY_BRIEFING_JOB_NAME,
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    build_scheduler,
    install_default_jobs,
    list_jobs,
    run_daily_briefing_job,
)


def _settings(**overrides: object) -> Settings:
    base = Settings()
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


class FakeRepo:
    def __init__(self, *, raise_on_save: bool = False) -> None:
        self.saved: list[SchedulerRunRecord] = []
        self.updated: list[SchedulerRunRecord] = []
        self._raise = raise_on_save

    def save_scheduler_run(self, record: SchedulerRunRecord) -> object:
        if self._raise:
            raise RuntimeError("storage-fail")
        self.saved.append(record)
        return None

    def update_scheduler_run(self, record: SchedulerRunRecord) -> object:
        self.updated.append(record)
        return None


# ---- factory + lifecycle ----------------------------------------------


def test_build_scheduler_returns_none_when_disabled() -> None:
    scheduler = build_scheduler(_settings())
    assert scheduler is None


def test_build_scheduler_returns_instance_when_enabled() -> None:
    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    assert not scheduler.running


def test_install_default_jobs_registers_daily_briefing_job() -> None:
    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    install_default_jobs(scheduler, _settings(scheduler_enabled=True))
    jobs = list_jobs(scheduler)
    assert len(jobs) == 1
    assert jobs[0].job_name == DAILY_BRIEFING_JOB_NAME


def test_list_jobs_returns_empty_tuple_when_scheduler_is_none() -> None:
    assert list_jobs(None) == ()


def test_install_jobs_rejects_invalid_cron() -> None:
    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    with pytest.raises(ValueError, match="5-field cron"):
        install_default_jobs(
            scheduler,
            _settings(
                scheduler_enabled=True,
                scheduler_daily_briefing_cron="bogus",
            ),
        )


# ---- run_daily_briefing_job behaviour ---------------------------------


def test_job_records_succeeded_run_when_callable_passes() -> None:
    repo = FakeRepo()
    record = run_daily_briefing_job(
        job_callable=lambda: None,
        repo_or_none=repo,
    )
    assert record.status == STATUS_SUCCEEDED
    assert record.triggered_by == "scheduler"
    assert record.finished_at is not None
    assert len(repo.saved) == 1
    assert repo.saved[0].status == "running"
    assert len(repo.updated) == 1
    assert repo.updated[0].status == STATUS_SUCCEEDED


def test_job_records_failed_run_when_callable_raises() -> None:
    repo = FakeRepo()

    def _boom() -> None:
        raise RuntimeError("model timeout")

    record = run_daily_briefing_job(
        job_callable=_boom,
        repo_or_none=repo,
    )
    assert record.status == STATUS_FAILED
    assert "model timeout" in (record.error_text or "")
    assert len(repo.updated) == 1
    assert repo.updated[0].status == STATUS_FAILED


def test_job_runs_even_when_repo_is_none() -> None:
    record = run_daily_briefing_job(
        job_callable=lambda: None,
        repo_or_none=None,
    )
    assert record.status == STATUS_SUCCEEDED


def test_job_runs_even_when_repo_save_raises() -> None:
    repo = FakeRepo(raise_on_save=True)
    record = run_daily_briefing_job(
        job_callable=lambda: None,
        repo_or_none=repo,
    )
    # Persistence failed, but the job result is still surfaced.
    assert record.status == STATUS_SUCCEEDED


def test_job_record_invariants_locked() -> None:
    """The persisted record must always be safety-False."""

    repo = FakeRepo()
    run_daily_briefing_job(job_callable=lambda: None, repo_or_none=repo)
    for record in repo.saved + repo.updated:
        assert record.safe_for_action_drafts is False
        assert record.safe_for_orders is False


def test_run_carries_scheduled_at_and_started_at() -> None:
    record = run_daily_briefing_job(
        job_callable=lambda: None, repo_or_none=None
    )
    assert isinstance(record.scheduled_at, datetime)
    assert isinstance(record.started_at, datetime)
    assert record.scheduled_at.tzinfo == UTC
