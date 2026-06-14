"""APScheduler integration (Slice 13).

Locked in `version-1-product-experience-locks.md §21.7`:

* APScheduler runs in-process inside the FastAPI runtime.
* Disabled by default; the operator opts in with ``SCHEDULER_ENABLED=true``.
* Each job invocation writes a ``SchedulerRunRecord`` so the audit
  chain captures what was triggered, when, and why.

The job in this slice is just a skeleton that records a successful
"would have run" event — it does NOT yet invoke the daily-briefing
orchestrator. Slice 21 wires the full morning chain into this job;
this slice merely proves the lifecycle and storage work.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Protocol
from uuid import uuid4
from zoneinfo import ZoneInfo

from ai_trading_agent_storage import SchedulerRunRecord
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from portfolio_outlook_api.config import Settings

logger = logging.getLogger(__name__)

DAILY_BRIEFING_JOB_NAME = "daily_briefing"
IBKR_SYNC_JOB_NAME = "ibkr_sync"

# Per-job APScheduler guards. ``max_instances=1`` + ``coalesce=True``
# prevent a slow run from queueing a parallel one; ``misfire_grace_time``
# bounds how late a "missed" fire is still acceptable. Jitter on the
# interval job decorrelates fires across replicas.
_DAILY_BRIEFING_MISFIRE_GRACE_SECONDS = 900
_IBKR_SYNC_MISFIRE_GRACE_SECONDS = 300
_IBKR_SYNC_JITTER_SECONDS = 30

# The worker process owns the locked 06:00 pre-briefing slot. Letting
# the API daily-briefing land on the same minute would create a
# double-fire of the morning chain. Validation lives in :func:`_parse_cron`.
_WORKER_PRE_BRIEFING_HOUR = 6
_WORKER_PRE_BRIEFING_MINUTE = 0

STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"


class _SchedulerRunRepoProtocol(Protocol):
    def save_scheduler_run(
        self, record: SchedulerRunRecord
    ) -> object: ...

    def update_scheduler_run(
        self, record: SchedulerRunRecord
    ) -> object: ...


@dataclass(frozen=True)
class JobInfo:
    job_id: str
    job_name: str
    next_run_at: datetime | None
    cron_expression: str


def _parse_cron(expression: str, timezone: str) -> CronTrigger:
    """Parse a 5-field cron (``minute hour day month day_of_week``) into a CronTrigger.

    Also rejects expressions whose next fire collides with the worker
    process's locked 06:00 pre-briefing slot — running the morning
    chain twice in the same minute is never what the operator wanted.
    """

    parts = (expression or "").strip().split()
    if len(parts) != 5:
        raise ValueError(
            f"scheduler_daily_briefing_cron must be a 5-field cron, got {expression!r}"
        )
    minute, hour, day, month, day_of_week = parts
    trigger = CronTrigger(
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        day_of_week=day_of_week,
        timezone=timezone,
    )
    _reject_worker_pre_briefing_collision(trigger, expression, timezone)
    return trigger


def _reject_worker_pre_briefing_collision(
    trigger: CronTrigger, expression: str, timezone: str
) -> None:
    """Raise ``ValueError`` if ``trigger`` ever fires at the worker's
    locked 06:00 slot in the configured timezone.

    The check picks a deterministic reference one minute before
    06:00 on a fixed date and asks the trigger when its next fire
    is. Any cron whose hour pattern includes 6 and whose minute
    pattern includes 0 will land on 06:00 from that reference,
    catching the obvious operator footgun (``"0 6 * * *"``) and
    less obvious ones (``"0 */2 * * *"``, ``"0 6 * * 1"``).
    """

    try:
        tz = ZoneInfo(timezone)
    except Exception as exc:  # pragma: no cover — caught by CronTrigger first
        raise ValueError(f"scheduler_timezone {timezone!r} is not a known zone") from exc
    reference = datetime(2026, 1, 1, 5, 59, tzinfo=tz)
    next_fire = trigger.get_next_fire_time(None, reference)
    if (
        next_fire is not None
        and next_fire.hour == _WORKER_PRE_BRIEFING_HOUR
        and next_fire.minute == _WORKER_PRE_BRIEFING_MINUTE
    ):
        raise ValueError(
            f"scheduler_daily_briefing_cron {expression!r} collides with the "
            f"worker's locked 06:00 pre-briefing slot; pick a different minute."
        )


def _record_job_run(
    *,
    job_name: str,
    scheduled_at: datetime,
    started_at: datetime,
    finished_at: datetime | None,
    status: str,
    error_text: str | None,
    triggered_by: str,
    repo_or_none: _SchedulerRunRepoProtocol | None,
) -> SchedulerRunRecord:
    record = SchedulerRunRecord(
        run_id=f"sch_{uuid4().hex}",
        job_name=job_name,
        scheduled_at=scheduled_at,
        started_at=started_at,
        finished_at=finished_at,
        status=status,
        error_text=error_text,
        triggered_by=triggered_by,
    )
    if repo_or_none is not None:
        try:
            repo_or_none.save_scheduler_run(record)
        except Exception:
            logger.exception("scheduler run could not be persisted")
    return record


def run_daily_briefing_job(
    *,
    job_callable: Callable[[], Any],
    repo_or_none: _SchedulerRunRepoProtocol | None,
    triggered_by: str = "scheduler",
) -> SchedulerRunRecord:
    """Run the daily-briefing skeleton job once and persist an audit row.

    ``job_callable`` is the actual work (currently a no-op closure
    returning ``None``; Slice 21 will pass the morning-chain
    orchestrator). Exceptions are captured and surfaced as a failed
    audit row rather than crashing the scheduler.
    """

    started_at = datetime.now(UTC)
    initial = _record_job_run(
        job_name=DAILY_BRIEFING_JOB_NAME,
        scheduled_at=started_at,
        started_at=started_at,
        finished_at=None,
        status=STATUS_RUNNING,
        error_text=None,
        triggered_by=triggered_by,
        repo_or_none=repo_or_none,
    )

    try:
        job_callable()
    except Exception as exc:  # noqa: BLE001 — boundary catch
        finished_at = datetime.now(UTC)
        failed = SchedulerRunRecord(
            run_id=initial.run_id,
            job_name=initial.job_name,
            scheduled_at=initial.scheduled_at,
            started_at=initial.started_at,
            finished_at=finished_at,
            status=STATUS_FAILED,
            error_text=str(exc),
            triggered_by=triggered_by,
        )
        if repo_or_none is not None:
            try:
                repo_or_none.update_scheduler_run(failed)
            except Exception:
                logger.exception("scheduler run failure could not be persisted")
        return failed

    finished_at = datetime.now(UTC)
    succeeded = SchedulerRunRecord(
        run_id=initial.run_id,
        job_name=initial.job_name,
        scheduled_at=initial.scheduled_at,
        started_at=initial.started_at,
        finished_at=finished_at,
        status=STATUS_SUCCEEDED,
        error_text=None,
        triggered_by=triggered_by,
    )
    if repo_or_none is not None:
        try:
            repo_or_none.update_scheduler_run(succeeded)
        except Exception:
            logger.exception("scheduler run success could not be persisted")
    return succeeded


def _skeleton_job_callable() -> None:
    """Slice-13 fallback: log the scheduler tick when no morning-chain
    runner is injected. Slice 21 replaced this as the default — the
    factory in :func:`install_default_jobs` now defaults to the
    :mod:`portfolio_outlook_api.morning_chain` runner. This callable
    survives as a deterministic no-op for tests that need a job that
    always succeeds without exercising the chain.
    """

    logger.info("daily_briefing scheduler tick (skeleton no-op)")
    return None


def _build_default_morning_chain_callable(
    runtime_settings: Settings,
) -> Callable[[], Any]:
    """Build the morning-chain callable that backs the scheduler job.

    Imported lazily so the scheduler module stays free of the
    chain-orchestrator's imports until the job is wired.

    V1.2 §BG — wiring is now centralised in
    :func:`build_morning_chain_legs_with_real_overrides` zodat de
    HTTP-trigger en de legacy in-process cron identiek gedragen.
    """

    from portfolio_outlook_api.morning_chain import (
        build_scheduler_chain_callable,
    )
    from portfolio_outlook_api.morning_chain_legs_wiring import (
        build_morning_chain_legs_with_real_overrides,
    )

    legs = build_morning_chain_legs_with_real_overrides(runtime_settings)
    return build_scheduler_chain_callable(legs_factory=lambda: legs)


def build_scheduler(
    runtime_settings: Settings,
) -> BackgroundScheduler | None:
    """Build an APScheduler instance if the operator opted in.

    Returns ``None`` when ``scheduler_enabled`` is False. The caller
    (FastAPI lifespan) is responsible for ``start()`` and
    ``shutdown()``. The scheduler is created stopped; jobs are wired
    in :func:`install_default_jobs`.
    """

    if not runtime_settings.scheduler_enabled:
        return None
    scheduler = BackgroundScheduler(timezone=runtime_settings.scheduler_timezone)
    return scheduler


def run_ibkr_sync_once(runtime_settings: Settings) -> None:
    """One scheduled IBKR read-only sync tick — best-effort, never raises.

    Reuses the exact path behind ``POST /ibkr/sync/run``. The adapter factory
    returns ``None`` unless the sync is fully configured (enabled + real client
    + paper + read-only + host/port), and ``run_sync`` gates on readiness, so
    this is a safe no-op until an IBKR paper connection is configured. Once it
    is, this populates the latest sync run that the dashboard reads from."""

    from portfolio_outlook_api.ibkr_ibapi_sync_client import (
        real_sync_client_session,
    )
    from portfolio_outlook_api.ibkr_sync import run_sync
    from portfolio_outlook_api.ibkr_sync_adapter_factory import (
        build_real_sync_adapter,
    )

    try:
        adapter = build_real_sync_adapter(runtime_settings)
        with real_sync_client_session(adapter) as active_adapter:
            run_sync(runtime_settings, adapter=active_adapter)
    except Exception:  # noqa: BLE001 — a scheduled tick must never crash
        logger.exception("Scheduled IBKR sync failed.")


def install_default_jobs(
    scheduler: BackgroundScheduler,
    runtime_settings: Settings,
    *,
    job_callable: Callable[[], Any] | None = None,
    repo_factory: Callable[[], _SchedulerRunRepoProtocol | None] | None = None,
    ibkr_sync_callable: Callable[[], Any] | None = None,
) -> None:
    """Wire the default daily-briefing job onto the scheduler.

    ``job_callable`` defaults to the skeleton callable; tests inject
    their own. ``repo_factory`` is invoked each fire to obtain a fresh
    repository (since DB sessions are short-lived); if it returns
    ``None`` the run is logged in memory but not persisted.

    When ``scheduler_api_legacy_cron`` is False (the new default) this
    function still validates the cron string (so a malformed env var is
    caught at startup just like before) but registers no jobs — the
    worker process owns the cron and POSTs to the API endpoints. Set
    the flag to True to restore the in-process API cron behavior.
    """

    trigger = _parse_cron(
        runtime_settings.scheduler_daily_briefing_cron,
        runtime_settings.scheduler_timezone,
    )
    # New default: the worker owns scheduling. The cron above is still
    # parsed (so a malformed env var fails startup the same way it
    # always did), but no job lands on the in-process scheduler. The
    # POST endpoints remain available for the worker (and manual fires).
    if not getattr(runtime_settings, "scheduler_api_legacy_cron", False):
        return
    if job_callable is not None:
        effective_callable = job_callable
    else:
        # Slice 21: default to the morning-chain runner. The chain
        # respects each per-leg `<x>_sync_enabled` flag — a fresh
        # install with no flags set short-circuits all legs to
        # ``skipped`` and the audit row records ``succeeded`` cleanly.
        effective_callable = _build_default_morning_chain_callable(runtime_settings)

    def _fire() -> None:
        repo = None if repo_factory is None else repo_factory()
        run_daily_briefing_job(
            job_callable=effective_callable,
            repo_or_none=repo,
            triggered_by="scheduler",
        )

    scheduler.add_job(
        _fire,
        trigger=trigger,
        id=DAILY_BRIEFING_JOB_NAME,
        name=DAILY_BRIEFING_JOB_NAME,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        misfire_grace_time=_DAILY_BRIEFING_MISFIRE_GRACE_SECONDS,
    )

    # Scheduled IBKR read-only sync — registered only when sync is enabled, so
    # the dashboard's positions/cash/valuation refresh automatically instead of
    # needing a manual POST /ibkr/sync/run. No-ops safely until a paper
    # connection is configured (see run_ibkr_sync_once).
    if runtime_settings.ibkr_sync_enabled:
        sync_fire = ibkr_sync_callable or (
            lambda: run_ibkr_sync_once(runtime_settings)
        )
        scheduler.add_job(
            sync_fire,
            trigger=IntervalTrigger(
                minutes=max(1, runtime_settings.ibkr_sync_interval_minutes),
                jitter=_IBKR_SYNC_JITTER_SECONDS,
            ),
            id=IBKR_SYNC_JOB_NAME,
            name=IBKR_SYNC_JOB_NAME,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=_IBKR_SYNC_MISFIRE_GRACE_SECONDS,
        )


def list_jobs(scheduler: BackgroundScheduler | None) -> tuple[JobInfo, ...]:
    if scheduler is None:
        return ()
    info: list[JobInfo] = []
    for job in scheduler.get_jobs():
        # `next_run_time` is only populated once the scheduler has been
        # started; before start (and in tests) the attribute is absent.
        next_run = getattr(job, "next_run_time", None)
        info.append(
            JobInfo(
                job_id=job.id,
                job_name=job.name,
                next_run_at=next_run,
                cron_expression=str(job.trigger),
            )
        )
    return tuple(info)


__all__ = [
    "DAILY_BRIEFING_JOB_NAME",
    "STATUS_RUNNING",
    "STATUS_SUCCEEDED",
    "STATUS_FAILED",
    "STATUS_SKIPPED",
    "JobInfo",
    "build_scheduler",
    "install_default_jobs",
    "list_jobs",
    "run_daily_briefing_job",
]
