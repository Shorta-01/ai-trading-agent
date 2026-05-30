"""Tests for the APScheduler integration (Slice 13)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from ai_trading_agent_storage import SchedulerRunRecord

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.scheduler import (
    DAILY_BRIEFING_JOB_NAME,
    IBKR_SYNC_JOB_NAME,
    STATUS_FAILED,
    STATUS_SUCCEEDED,
    build_scheduler,
    install_default_jobs,
    list_jobs,
    run_daily_briefing_job,
    run_ibkr_sync_once,
)


def _settings(**overrides: object) -> Settings:
    base = Settings()
    # The new default is "worker owns cron, API skips registration"; the
    # existing tests in this file exercise the legacy in-process path that
    # still ships behind the flag, so flip it on here. Tests for the new
    # default override this explicitly.
    base.scheduler_api_legacy_cron = True
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


def test_ibkr_sync_job_not_registered_when_sync_disabled() -> None:
    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    install_default_jobs(scheduler, _settings(scheduler_enabled=True))
    assert {job.job_name for job in list_jobs(scheduler)} == {DAILY_BRIEFING_JOB_NAME}


def test_ibkr_sync_job_registered_when_sync_enabled() -> None:
    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    fired: list[bool] = []
    install_default_jobs(
        scheduler,
        _settings(
            scheduler_enabled=True,
            ibkr_sync_enabled=True,
            ibkr_sync_interval_minutes=5,
        ),
        ibkr_sync_callable=lambda: fired.append(True),
    )
    job = scheduler.get_job(IBKR_SYNC_JOB_NAME)
    assert job is not None
    job.func()  # the registered callable fires the injected sync
    assert fired == [True]


def test_run_ibkr_sync_once_is_safe_noop_when_unconfigured() -> None:
    # Sync not enabled -> adapter is None + run_sync gates; must not raise.
    run_ibkr_sync_once(_settings())


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


# ---- Default job uses morning-chain (Slice 21) -------------------------


def test_install_default_jobs_wires_morning_chain_when_no_callable_provided() -> None:
    """When no explicit callable is supplied, the scheduler must wire the
    morning-chain runner — not the no-op skeleton. The chain respects
    each per-leg `<x>_sync_enabled` flag, so with everything off it
    still completes (every leg returns ``skipped``)."""

    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    repo = FakeRepo()
    install_default_jobs(
        scheduler,
        _settings(scheduler_enabled=True),
        repo_factory=lambda: repo,
    )
    # Manually fire the registered job to prove it routes through
    # run_daily_briefing_job → morning-chain callable → succeed.
    jobs = list_jobs(scheduler)
    assert len(jobs) == 1
    job = scheduler.get_job(DAILY_BRIEFING_JOB_NAME)
    assert job is not None
    job.func()  # the closure built by install_default_jobs

    # One audit row written + updated to succeeded.
    assert len(repo.saved) == 1
    assert len(repo.updated) == 1
    assert repo.updated[0].status == STATUS_SUCCEEDED


def test_install_default_jobs_captures_morning_chain_failure() -> None:
    """A morning-chain leg failure surfaces on the scheduler audit row
    as ``failed`` with the failure summary in ``error_text``."""

    from portfolio_outlook_api import morning_chain as mc
    from portfolio_outlook_api import scheduler as sched_module

    def _failing_runner(runtime_settings):
        legs = (
            lambda: mc.MorningChainLegOutcome(
                leg_name=mc.LEG_MARKET_DATA_SYNC,
                status=mc.LEG_STATUS_FAILED,
                failure_code="market_data_unavailable",
                detail_nl="market data unavailable",
            ),
        )
        return mc.build_scheduler_chain_callable(legs_factory=lambda: legs)

    original = sched_module._build_default_morning_chain_callable
    sched_module._build_default_morning_chain_callable = _failing_runner
    try:
        scheduler = build_scheduler(_settings(scheduler_enabled=True))
        assert scheduler is not None
        repo = FakeRepo()
        install_default_jobs(
            scheduler,
            _settings(scheduler_enabled=True),
            repo_factory=lambda: repo,
        )
        job = scheduler.get_job(DAILY_BRIEFING_JOB_NAME)
        assert job is not None
        job.func()
    finally:
        sched_module._build_default_morning_chain_callable = original

    assert repo.updated[0].status == STATUS_FAILED
    assert repo.updated[0].error_text is not None
    assert "market_data_sync" in repo.updated[0].error_text


# ---- job-option hardening + cron-collision validation -------------------


def test_daily_briefing_cron_default_passes_collision_check() -> None:
    """The locked default (30 6 * * *) doesn't collide with the worker's
    06:00 pre-briefing slot — operators picked 06:30 for exactly that
    reason."""

    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    install_default_jobs(scheduler, _settings(scheduler_enabled=True))
    job = scheduler.get_job(DAILY_BRIEFING_JOB_NAME)
    assert job is not None


@pytest.mark.parametrize(
    "colliding_cron",
    [
        "0 6 * * *",  # the obvious operator footgun
        "0 */2 * * *",  # every even hour — includes 06:00
        "0 6 * * 1",  # Monday at 06:00 — still hour=6 minute=0
    ],
)
def test_daily_briefing_cron_rejects_06_00_collision(colliding_cron: str) -> None:
    """The API daily-briefing must not land on the same minute as the
    worker's locked 06:00 pre-briefing — that would double-fire the
    morning chain."""

    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    with pytest.raises(ValueError, match="06:00 pre-briefing slot"):
        install_default_jobs(
            scheduler,
            _settings(
                scheduler_enabled=True,
                scheduler_daily_briefing_cron=colliding_cron,
            ),
        )


def test_daily_briefing_cron_accepts_safe_neighbour_minutes() -> None:
    """Crons that fire near 06:00 but never exactly on it must be
    accepted — operators legitimately want 05:55, 06:01, 06:30…"""

    for safe in ("55 5 * * *", "1 6 * * *", "30 6 * * *", "0 7 * * *"):
        scheduler = build_scheduler(_settings(scheduler_enabled=True))
        assert scheduler is not None
        install_default_jobs(
            scheduler,
            _settings(scheduler_enabled=True, scheduler_daily_briefing_cron=safe),
        )


def test_daily_briefing_job_has_explicit_max_instances_and_coalesce() -> None:
    """A slow morning chain must never queue a parallel run; APScheduler
    defaults are explicit-wired so the behaviour is obvious from the code."""

    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    install_default_jobs(scheduler, _settings(scheduler_enabled=True))
    job = scheduler.get_job(DAILY_BRIEFING_JOB_NAME)
    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time is not None and job.misfire_grace_time > 0


def test_ibkr_sync_job_has_jitter_and_guards_when_enabled() -> None:
    """Interval jobs get jitter so multi-replica deploys don't fire
    in lockstep on the same second."""

    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    install_default_jobs(
        scheduler,
        _settings(
            scheduler_enabled=True,
            ibkr_sync_enabled=True,
            ibkr_sync_interval_minutes=5,
        ),
        ibkr_sync_callable=lambda: None,
    )
    job = scheduler.get_job(IBKR_SYNC_JOB_NAME)
    assert job is not None
    assert job.max_instances == 1
    assert job.coalesce is True
    assert job.misfire_grace_time is not None and job.misfire_grace_time > 0
    # IntervalTrigger exposes the jitter as a public attribute.
    assert getattr(job.trigger, "jitter", None) is not None


# ---- new default: API skips cron registration (worker owns it) ----------


def test_install_default_jobs_skips_registration_under_new_default() -> None:
    """With the new default ``scheduler_api_legacy_cron=False`` the API
    no longer owns the daily-briefing cron — the worker triggers it via
    HTTP POST instead. The cron string is still parsed so a malformed
    env var still fails startup, but no jobs land on the scheduler."""

    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    # Default Settings() has scheduler_api_legacy_cron=False; override the
    # test helper's flip with an explicit fresh Settings.
    base = Settings()
    base.scheduler_enabled = True  # type: ignore[misc]
    install_default_jobs(scheduler, base)
    assert list_jobs(scheduler) == ()


def test_install_default_jobs_still_validates_cron_under_new_default() -> None:
    """Even when the API skips registration, the cron string is parsed
    so a malformed env var still raises at startup — operators get the
    same error as before instead of a silently-broken deployment."""

    scheduler = build_scheduler(_settings(scheduler_enabled=True))
    assert scheduler is not None
    base = Settings()
    base.scheduler_enabled = True  # type: ignore[misc]
    base.scheduler_daily_briefing_cron = "bogus"  # type: ignore[misc]
    with pytest.raises(ValueError, match="5-field cron"):
        install_default_jobs(scheduler, base)
