"""Task 127: APScheduler skeleton for the worker process.

Owns the locked 06:00 pre-briefing + hourly 07:00-21:00 cron jobs.
Each fire routes through :func:`run_orchestrator` (one orchestrator
function per fire) which performs cold-start detection, writes an
audit row, and exits — no advice generation, no market data fetch,
no discovery (those are subsequent tasks).

The scheduler also heartbeats a ``scheduler_state`` row every
``heartbeat_interval_seconds`` so the API can surface next-fire
times to the dashboard badge.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4
from zoneinfo import ZoneInfo

from ai_trading_agent_storage import (
    SchedulerStateEntry,
    SqlAlchemyScheduledRunAuditRepository,
    SqlAlchemySchedulerStateRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.api_trigger import (
    trigger_ibkr_sync,
    trigger_morning_chain,
    trigger_morning_explanation_batch,
    trigger_sell_signal_sweep,
)
from portfolio_outlook_worker.config import (
    IbkrSettings,
    SchedulerSettings,
    StorageSettings,
)
from portfolio_outlook_worker.error_capture import record_worker_error
from portfolio_outlook_worker.orchestrator import (
    RunType,
    run_orchestrator,
)
from portfolio_outlook_worker.single_flight_lock import (
    InMemoryLock,
    PostgresAdvisoryLock,
    SingleFlightLockProtocol,
)

logger = logging.getLogger(__name__)


_PRE_BRIEFING_JOB_ID = "pre_briefing"
_SUBMISSION_SWEEP_JOB_ID = "submission_sweep"
_CANCEL_SWEEP_JOB_ID = "cancel_sweep"
_MORNING_CHAIN_JOB_ID = "morning_chain_trigger"
_MORNING_EXPLANATION_BATCH_JOB_ID = "morning_explanation_batch_trigger"
_IBKR_SYNC_JOB_ID = "ibkr_sync_trigger"
_SELL_SIGNAL_SWEEP_JOB_ID = "sell_signal_sweep_trigger"
# Market-aware fires (one per active market session, see market_hours).
# Job ids follow ``market_close_<EXCHANGE_CODE>`` so they're stable
# across restarts and visible in /scheduler/runs for audit.
_MARKET_CLOSE_JOB_PREFIX = "market_close_"
_MARKET_OPEN_JOB_PREFIX = "market_open_"

# Per-job APScheduler guards. ``max_instances=1`` and ``coalesce=True``
# stop a slow run from spawning a parallel one; ``misfire_grace_time``
# bounds how late a "missed" fire is still acceptable (cron fires only).
# A small ``jitter`` on the interval jobs decorrelates fires across
# multiple worker replicas so they don't thunder-herd Postgres/IBKR.
_INTERVAL_JITTER_SECONDS = 10
_CRON_MISFIRE_GRACE_SECONDS = 300
_HOURLY_MISFIRE_GRACE_SECONDS = 600
_INTERVAL_MISFIRE_GRACE_SECONDS = 60


class _PositionSnapshotCounts:
    """Concrete :class:`_SnapshotCountsProtocol` impl.

    Production-side wiring is deliberately thin in 126b/127a — the
    worker's sync loop isn't built yet, so position-snapshot rows
    are sparse and watchlist isn't yet IBKR-aware. The methods do
    real ``SELECT count(*)`` queries; if the table is empty the
    count is 0 and cold-start detection fires correctly.
    """

    def __init__(self, connection: Any) -> None:
        self._connection = connection

    def position_snapshot_count_for_account(
        self, ibkr_account_id: str
    ) -> int:
        from sqlalchemy import text

        result = self._connection.execute(
            text(
                "SELECT COUNT(*) FROM ibkr_position_snapshots "
                "WHERE ibkr_account_id = :a OR account_ref = :a"
            ),
            {"a": ibkr_account_id},
        ).scalar()
        return int(result or 0)

    def watchlist_item_count_for_account(
        self, ibkr_account_id: str  # noqa: ARG002 — pending account-aware watchlist
    ) -> int:
        from sqlalchemy import text

        # Per-account watchlist is pending; for now count global
        # active watchlist items. Once the watchlist gains
        # ibkr_account_id (follow-up task) this filter tightens.
        try:
            result = self._connection.execute(
                text(
                    "SELECT COUNT(*) FROM watchlist_items "
                    "WHERE status = 'active'"
                )
            ).scalar()
            return int(result or 0)
        except Exception:  # noqa: BLE001 — schema may not have watchlist yet
            return 0


class PortfolioScheduler:
    """APScheduler 3.x wrapper for the worker process.

    The constructor takes the IBKR gateway + storage/IBKR/scheduler
    settings; ``start()`` opens a Postgres-backed job store and
    registers the two cron jobs; ``stop()`` shuts down cleanly. Both
    methods are idempotent — calling them twice is a no-op the second
    time.
    """

    def __init__(
        self,
        *,
        gateway: Any,
        storage_settings: StorageSettings,
        ibkr_settings: IbkrSettings,
        scheduler_settings: SchedulerSettings,
        worker_id: str | None = None,
        scheduler_factory: Callable[..., Any] | None = None,
        order_adapter: Any | None = None,
        digest_runner: Any | None = None,
        morning_alerts_runner: Any | None = None,
    ) -> None:
        self._gateway = gateway
        self._storage_settings = storage_settings
        self._ibkr_settings = ibkr_settings
        self._scheduler_settings = scheduler_settings
        self._worker_id = worker_id or f"worker_{uuid4().hex[:12]}"
        self._scheduler_factory = scheduler_factory or _build_scheduler
        # Writable IBKR order session (opened by main() only when enabled +
        # paper). When None the order sweeps are never registered — the
        # default. This is the activation switch for T-045 §1-3.
        self._order_adapter = order_adapter
        # Concrete digest runner — fired on every ``market_close`` event.
        # Stays ``None`` until main() instantiates and injects one;
        # the orchestrator silently skips the digest step when ``None``.
        self._digest_runner: Any | None = digest_runner
        # Concrete morning-alerts runner — fired on every
        # ``morning_briefing`` event after decision packages are
        # composed. Same shape as digest_runner: ``None`` is a safe
        # no-op (the orchestrator's branch short-circuits).
        self._morning_alerts_runner: Any | None = morning_alerts_runner
        self._scheduler: Any | None = None
        self._started: bool = False
        # #8 — per-kind consecutive sweep-error counters. A single
        # error tick is normal IBKR noise (timeouts, transient
        # disconnects); N consecutive errors should reach the
        # operator. Reset to 0 on the next non-error tick.
        self._sweep_error_streak: dict[str, int] = {
            "submission": 0,
            "cancel": 0,
        }
        self._sweep_alert_fired: dict[str, bool] = {
            "submission": False,
            "cancel": False,
        }

    @property
    def worker_id(self) -> str:
        return self._worker_id

    def start(self) -> None:
        if self._started:
            return
        self._scheduler = self._scheduler_factory(
            database_url=self._storage_settings.database_url,
            timezone=self._scheduler_settings.timezone,
        )
        self._scheduler.add_job(
            self._on_pre_briefing,
            "cron",
            hour=6,
            minute=0,
            timezone=self._scheduler_settings.timezone,
            id=_PRE_BRIEFING_JOB_ID,
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=_CRON_MISFIRE_GRACE_SECONDS,
        )
        self._register_market_event_jobs()
        self._scheduler.add_job(
            self._heartbeat,
            "interval",
            seconds=self._scheduler_settings.heartbeat_interval_seconds,
            jitter=_INTERVAL_JITTER_SECONDS,
            id="heartbeat",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
            misfire_grace_time=_INTERVAL_MISFIRE_GRACE_SECONDS,
        )
        self._register_order_sweeps()
        self._register_api_triggers()
        # Auto-capture: any job that raises lands in the central error log.
        from apscheduler.events import EVENT_JOB_ERROR

        self._scheduler.add_listener(self._on_job_error, EVENT_JOB_ERROR)
        self._scheduler.start()
        self._started = True
        logger.info(
            "Scheduler gestart (worker_id=%s, timezone=%s)",
            self._worker_id,
            self._scheduler_settings.timezone,
        )
        # Write the initial heartbeat row so the API has something to
        # show before the first interval tick.
        self._heartbeat()

    def stop(self) -> None:
        if not self._started or self._scheduler is None:
            return
        try:
            self._scheduler.shutdown(wait=False)
        finally:
            self._started = False
            logger.info("Scheduler gestopt (worker_id=%s)", self._worker_id)

    def next_runs(self) -> list[datetime]:
        """Next scheduled fire times across pre-briefing + market events.

        Returns every registered job's ``next_run_time`` sorted earliest
        first. The market-event jobs are dynamic (one per active
        session), so a fixed lookup list isn't sufficient — we walk
        every job and collect the ones with a known next fire.
        """

        if self._scheduler is None:
            return []
        runs: list[datetime] = []
        for job in self._scheduler.get_jobs():
            next_time = getattr(job, "next_run_time", None)
            if next_time is not None:
                runs.append(next_time)
        runs.sort()
        return runs

    # ---- job callbacks --------------------------------------------

    def _on_job_error(self, event: Any) -> None:
        """APScheduler EVENT_JOB_ERROR listener — record any job exception."""

        exc = getattr(event, "exception", None)
        job_id = getattr(event, "job_id", "unknown")
        record_worker_error(
            storage_settings=self._storage_settings,
            source_component=f"scheduler:{job_id}",
            event_code="scheduler_job_error",
            message=(f"{type(exc).__name__}: {exc}" if exc else "Onbekende job-fout"),
            technical_summary=(f"{type(exc).__name__}: {exc}" if exc else None),
            stack_trace=getattr(event, "traceback", None),
        )

    def _on_pre_briefing(self) -> None:
        self._run("pre_briefing")
        # #2 — signal chaining: when configured, fire the morning chain
        # immediately after the 06:00 pre-briefing audit lands. This
        # replaces the old clock-based 30-minute gap with an explicit
        # ordering, so a slow pre-briefing can never let the morning
        # chain run against stale state.
        if (
            self._scheduler_settings.morning_chain_trigger_enabled
            and self._scheduler_settings.morning_chain_after_pre_briefing
        ):
            try:
                trigger_morning_chain(
                    base_url=self._scheduler_settings.api_base_url,
                    timeout_seconds=self._scheduler_settings.api_request_timeout_seconds,
                )
            except Exception:  # noqa: BLE001 — already best-effort
                logger.exception("post-pre-briefing morning chain trigger failed")

    def _on_market_close(self, exchange_code: str) -> None:
        """Fired a few minutes after a followed market's regular close.

        Routes through the orchestrator with ``run_type="market_close"``
        and the exchange code as ``market_code`` so the digest runner
        scopes its email subject + payload to the right market.
        """

        logger.info("Market close fire for %s", exchange_code)
        self._run("market_close", market_code=exchange_code)

    def _on_market_open(self, exchange_code: str) -> None:
        """Fired a few minutes after a followed market's regular open.

        Routes through the orchestrator with ``run_type="market_open"``.
        Lightweight: refresh IBKR position snapshots so any overnight
        gap-up/gap-down is visible in the dashboard. No full forecast
        regeneration — that happens once per day in the morning chain.
        """

        logger.info("Market open fire for %s", exchange_code)
        self._run("market_open", market_code=exchange_code)

    # ---- Market-aware cron registration ---------------------------

    def _register_market_event_jobs(self) -> None:
        """Register one cron job per active market session for close /
        open events. Replaces the legacy ``hour="7-21"`` dumb hourly
        cadence — fires only when a market the operator actually
        follows has an event.

        Reads the operator's ``universe_scan_index_codes`` and the two
        feature toggles (``per_market_close_digest_enabled`` /
        ``per_market_open_alerts_enabled``) from
        :class:`SchedulerSettings`. Best-effort: a malformed index code
        is silently skipped (the API validates before persisting, so
        bad codes shouldn't reach us).
        """

        from portfolio_outlook_worker.market_hours import (
            close_digest_minute,
            open_check_minute,
            resolve_active_market_sessions,
        )

        if self._scheduler is None:  # pragma: no cover — invariant
            return

        codes = [
            c.strip()
            for c in (
                self._scheduler_settings.universe_scan_index_codes or ""
            ).split(",")
            if c.strip()
        ]
        if not codes:
            logger.info(
                "Geen markten geselecteerd; skip market-event "
                "cron-registratie."
            )
            return

        sessions = resolve_active_market_sessions(codes)
        if not sessions:
            logger.info(
                "Geen actieve marktsessies herkend in %s; skip market-"
                "event cron-registratie.",
                codes,
            )
            return

        close_enabled = self._scheduler_settings.per_market_close_digest_enabled
        open_enabled = self._scheduler_settings.per_market_open_alerts_enabled

        for session in sessions:
            if close_enabled:
                close_hour, close_minute = close_digest_minute(session)
                self._scheduler.add_job(
                    self._on_market_close,
                    "cron",
                    day_of_week="mon-fri",
                    hour=close_hour,
                    minute=close_minute,
                    timezone=session.timezone,
                    id=f"{_MARKET_CLOSE_JOB_PREFIX}{session.code}",
                    args=(session.code,),
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True,
                    misfire_grace_time=_HOURLY_MISFIRE_GRACE_SECONDS,
                )
                logger.info(
                    "Market-close fire geregistreerd voor %s om "
                    "%02d:%02d %s (weekdagen).",
                    session.code,
                    close_hour,
                    close_minute,
                    session.timezone,
                )
            if open_enabled:
                open_hour, open_minute = open_check_minute(session)
                self._scheduler.add_job(
                    self._on_market_open,
                    "cron",
                    day_of_week="mon-fri",
                    hour=open_hour,
                    minute=open_minute,
                    timezone=session.timezone,
                    id=f"{_MARKET_OPEN_JOB_PREFIX}{session.code}",
                    args=(session.code,),
                    replace_existing=True,
                    max_instances=1,
                    coalesce=True,
                    misfire_grace_time=_HOURLY_MISFIRE_GRACE_SECONDS,
                )
                logger.info(
                    "Market-open fire geregistreerd voor %s om "
                    "%02d:%02d %s (weekdagen).",
                    session.code,
                    open_hour,
                    open_minute,
                    session.timezone,
                )

    # ---- API-trigger jobs (#1, #2) --------------------------------

    def _register_api_triggers(self) -> None:
        """Register the worker-side cron + interval that POST to the API.

        Both are off by default; turning them on is the deliberate
        migration switch from the legacy API-process cron to the new
        worker-owned scheduling.
        """

        if self._scheduler is None:
            return
        # Morning chain — opt-in via ``morning_chain_trigger_enabled``,
        # skipped when ``morning_chain_after_pre_briefing`` is set
        # (pre-briefing tail-call takes over to avoid double fires).
        if (
            self._scheduler_settings.morning_chain_trigger_enabled
            and not self._scheduler_settings.morning_chain_after_pre_briefing
        ):
            trigger = self._build_morning_chain_trigger()
            self._scheduler.add_job(
                self._on_morning_chain_trigger,
                trigger=trigger,
                id=_MORNING_CHAIN_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_CRON_MISFIRE_GRACE_SECONDS,
            )
        if self._scheduler_settings.ibkr_sync_trigger_enabled:
            self._scheduler.add_job(
                self._on_ibkr_sync_trigger,
                "interval",
                minutes=max(1, self._scheduler_settings.ibkr_sync_interval_minutes),
                jitter=_INTERVAL_JITTER_SECONDS,
                id=_IBKR_SYNC_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_INTERVAL_MISFIRE_GRACE_SECONDS,
            )
        # Morning explanation batch — fires ~15 min after the morning
        # chain so Claude's Dutch paraphrase is ready for every held-
        # position Decision Package before the operator opens the
        # dashboard. Opt-in via ``morning_explanation_batch_trigger_enabled``
        # (worker) AND ``ai_explanation_morning_batch_enabled`` (API).
        if self._scheduler_settings.morning_explanation_batch_trigger_enabled:
            self._scheduler.add_job(
                self._on_morning_explanation_batch_trigger,
                trigger=self._build_morning_explanation_batch_trigger(),
                id=_MORNING_EXPLANATION_BATCH_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_CRON_MISFIRE_GRACE_SECONDS,
            )
        # SELL-signal sweep — V1.2 §BI. CLAUDE.md §6.3 + §11 vraagt
        # dat de SELL-monitoring blijft draaien (ook tijdens pauze).
        # Default elke 10 min weekdagen 07:00-22:00 Europe/Brussels —
        # dekt US + Euronext market-hours. Sweep bypasst pauze-flag
        # bewust (sell_signal_sweep.py:431). Opt-in via
        # ``sell_signal_sweep_trigger_enabled``.
        if self._scheduler_settings.sell_signal_sweep_trigger_enabled:
            self._scheduler.add_job(
                self._on_sell_signal_sweep_trigger,
                trigger=self._build_sell_signal_sweep_trigger(),
                id=_SELL_SIGNAL_SWEEP_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_CRON_MISFIRE_GRACE_SECONDS,
            )

    def _build_morning_chain_trigger(self) -> Any:
        """Parse the configured 5-field cron into a CronTrigger."""

        from apscheduler.triggers.cron import CronTrigger

        parts = (self._scheduler_settings.morning_chain_cron or "").strip().split()
        if len(parts) != 5:
            raise ValueError(
                "scheduler.morning_chain_cron must be a 5-field cron, got "
                f"{self._scheduler_settings.morning_chain_cron!r}"
            )
        minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=self._scheduler_settings.timezone,
        )

    def _on_morning_chain_trigger(self) -> None:
        trigger_morning_chain(
            base_url=self._scheduler_settings.api_base_url,
            timeout_seconds=self._scheduler_settings.api_request_timeout_seconds,
        )

    def _on_ibkr_sync_trigger(self) -> None:
        trigger_ibkr_sync(
            base_url=self._scheduler_settings.api_base_url,
            timeout_seconds=self._scheduler_settings.api_request_timeout_seconds,
        )

    def _build_morning_explanation_batch_trigger(self) -> Any:
        """Parse the configured 5-field cron into a CronTrigger."""

        from apscheduler.triggers.cron import CronTrigger

        parts = (
            self._scheduler_settings.morning_explanation_batch_cron or ""
        ).strip().split()
        if len(parts) != 5:
            raise ValueError(
                "scheduler.morning_explanation_batch_cron must be a 5-field cron, got "
                f"{self._scheduler_settings.morning_explanation_batch_cron!r}"
            )
        minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=self._scheduler_settings.timezone,
        )

    def _on_morning_explanation_batch_trigger(self) -> None:
        trigger_morning_explanation_batch(
            base_url=self._scheduler_settings.api_base_url,
            timeout_seconds=self._scheduler_settings.api_request_timeout_seconds,
        )

    def _build_sell_signal_sweep_trigger(self) -> Any:
        """Parse de geconfigureerde 5-field cron voor de SELL-sweep
        (V1.2 §BI)."""

        from apscheduler.triggers.cron import CronTrigger

        parts = (
            self._scheduler_settings.sell_signal_sweep_cron or ""
        ).strip().split()
        if len(parts) != 5:
            raise ValueError(
                "scheduler.sell_signal_sweep_cron must be a 5-field cron, got "
                f"{self._scheduler_settings.sell_signal_sweep_cron!r}"
            )
        minute, hour, day, month, day_of_week = parts
        return CronTrigger(
            minute=minute,
            hour=hour,
            day=day,
            month=month,
            day_of_week=day_of_week,
            timezone=self._scheduler_settings.timezone,
        )

    def _on_sell_signal_sweep_trigger(self) -> None:
        trigger_sell_signal_sweep(
            base_url=self._scheduler_settings.api_base_url,
            timeout_seconds=self._scheduler_settings.api_request_timeout_seconds,
        )

    # ---- order sweeps (T-045 §1-3, gated + default-off) -----------

    def _register_order_sweeps(self) -> None:
        """Register the submission + cancel sweep jobs, gated.

        Only registers when a writable order session is present AND the
        per-sweep flag is on AND an account id is configured. Default-off:
        with no order adapter (the default) nothing is registered."""

        if self._scheduler is None or self._order_adapter is None:
            return
        if self._ibkr_settings.account_id is None:
            return
        sweep_seconds = max(1, self._ibkr_settings.sweep_interval_seconds)
        if self._ibkr_settings.submission_sweep_enabled:
            self._scheduler.add_job(
                self._on_submission_sweep,
                "interval",
                seconds=sweep_seconds,
                jitter=_INTERVAL_JITTER_SECONDS,
                id=_SUBMISSION_SWEEP_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_INTERVAL_MISFIRE_GRACE_SECONDS,
            )
        if self._ibkr_settings.cancel_sweep_enabled:
            self._scheduler.add_job(
                self._on_cancel_sweep,
                "interval",
                seconds=sweep_seconds,
                jitter=_INTERVAL_JITTER_SECONDS,
                id=_CANCEL_SWEEP_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_INTERVAL_MISFIRE_GRACE_SECONDS,
            )

    def _on_submission_sweep(self) -> None:
        self._run_order_sweep(kind="submission")

    def _on_cancel_sweep(self) -> None:
        self._run_order_sweep(kind="cancel")

    def _run_order_sweep(self, *, kind: str) -> None:
        if not self._storage_settings.enabled or not self._storage_settings.database_url:
            return
        account_id = self._ibkr_settings.account_id
        if self._order_adapter is None or account_id is None:
            return
        from portfolio_outlook_worker.ibkr_submission.ibkr_order_sweeps import (
            build_cancel_sweep,
            build_submission_sweep,
        )

        provider = StorageConnectionProvider(
            build_database_connection_settings(self._storage_settings.database_url)
        )
        # Bind narrowed locals before the closure — mypy doesn't carry
        # attribute narrowing into nested functions.
        order_adapter = self._order_adapter
        gateway = self._gateway
        try:
            with provider.checked_connection(require_writable=True) as checked:
                lock = _build_lock(checked.connection)

                # The sweep is rebuilt on every attempt (fresh queries
                # against the new connection-bound state) — that's the
                # whole point of an in-tick retry: each ``.tick()`` is
                # a clean re-evaluation, not a cached one.
                def _attempt() -> Any:
                    if kind == "submission":
                        return build_submission_sweep(
                            connection=checked.connection,
                            readiness=checked.readiness,
                            gateway=gateway,
                            order_adapter=order_adapter,
                            ibkr_account_id=account_id,
                            lock=lock,
                        ).tick()
                    return build_cancel_sweep(
                        connection=checked.connection,
                        readiness=checked.readiness,
                        order_adapter=order_adapter,
                        ibkr_account_id=account_id,
                        lock=lock,
                    ).tick()

                result = _run_sweep_with_backoff(
                    attempt=_attempt,
                    max_attempts=self._ibkr_settings.sweep_retry_max_attempts,
                    base_backoff_seconds=self._ibkr_settings.sweep_retry_backoff_seconds,
                )
                logger.info("%s sweep tick: mode=%s", kind, result.mode)
                self._track_sweep_outcome(
                    kind=kind,
                    mode=result.mode,
                    error_message=getattr(result, "error_message", None),
                )
        except StorageConnectionError as exc:
            logger.warning("%s sweep could not open storage: %s", kind, exc)

    def _track_sweep_outcome(
        self, *, kind: str, mode: str, error_message: str | None
    ) -> None:
        """#8 — surface persistent sweep failures to /systeemmeldingen.

        A single error tick is normal IBKR noise (timeouts, transient
        disconnects). N consecutive errors are not; once the streak
        reaches the configured threshold the worker writes a
        ``SystemEvent`` so the dashboard surfaces the problem. The
        alert is debounced — further consecutive errors don't keep
        firing it — and the streak + debounce both reset on the next
        non-error tick.
        """

        threshold = max(
            1, self._ibkr_settings.sweep_alert_after_consecutive_errors
        )
        if mode == "error":
            self._sweep_error_streak[kind] += 1
            if (
                self._sweep_error_streak[kind] >= threshold
                and not self._sweep_alert_fired[kind]
            ):
                record_worker_error(
                    storage_settings=self._storage_settings,
                    source_component=f"scheduler:{kind}_sweep",
                    event_code="sweep_persistent_error",
                    message=(
                        f"{kind} sweep is {self._sweep_error_streak[kind]} ticks in a "
                        f"row in mode=error"
                        + (f": {error_message}" if error_message else "")
                    ),
                    technical_summary=error_message,
                    stack_trace=None,
                )
                self._sweep_alert_fired[kind] = True
            return
        # Any non-error mode resets the streak + clears the debounce so a
        # future failure run can re-alert.
        self._sweep_error_streak[kind] = 0
        self._sweep_alert_fired[kind] = False

    def _run(
        self, run_type: RunType, *, market_code: str | None = None
    ) -> None:
        if not self._storage_settings.enabled or not self._storage_settings.database_url:
            logger.warning(
                "Scheduled fire skipped: storage uitgeschakeld of zonder URL."
            )
            return
        provider = StorageConnectionProvider(
            build_database_connection_settings(self._storage_settings.database_url)
        )
        try:
            with provider.checked_connection(require_writable=True) as checked:
                audit_repo = SqlAlchemyScheduledRunAuditRepository(
                    checked.connection, checked.readiness
                )
                snapshot_counts = _PositionSnapshotCounts(checked.connection)
                lock = _build_lock(checked.connection)
                next_times = self.next_runs()
                next_scheduled_at = next_times[0] if next_times else None
                brussels_now_hour = self._brussels_hour_now()
                run_orchestrator(
                    run_type=run_type,
                    ibkr_account_id=self._ibkr_settings.account_id,
                    gateway=self._gateway,
                    snapshot_counts=snapshot_counts,
                    audit_repo=audit_repo,
                    lock=lock,
                    brussels_hour_provider=lambda: brussels_now_hour,
                    next_scheduled_at=next_scheduled_at,
                    digest_runner=self._digest_runner,
                    morning_alerts_runner=self._morning_alerts_runner,
                    market_code=market_code,
                )
        except StorageConnectionError as exc:
            logger.warning("Scheduled fire could not open storage: %s", exc)

    def _heartbeat(self) -> None:
        if not self._storage_settings.enabled or not self._storage_settings.database_url:
            return
        provider = StorageConnectionProvider(
            build_database_connection_settings(self._storage_settings.database_url)
        )
        try:
            with provider.checked_connection(require_writable=True) as checked:
                state_repo = SqlAlchemySchedulerStateRepository(
                    checked.connection, checked.readiness
                )
                now = datetime.now(UTC)
                next_times = self.next_runs()
                next_pre = next(
                    (t for t in next_times if _is_pre_briefing_run(t)),
                    None,
                )
                next_hourly = next(
                    (t for t in next_times if not _is_pre_briefing_run(t)),
                    None,
                )
                state_repo.upsert(
                    SchedulerStateEntry(
                        worker_id=self._worker_id,
                        started_at=now,
                        last_heartbeat_at=now,
                        next_pre_briefing_at=next_pre,
                        next_hourly_at=next_hourly,
                    )
                )
        except StorageConnectionError as exc:
            logger.warning("Heartbeat skipped: storage niet bereikbaar (%s)", exc)

    def _brussels_hour_now(self) -> int:
        try:
            tz = ZoneInfo(self._scheduler_settings.timezone)
        except Exception:  # noqa: BLE001 — bad zone name
            tz = ZoneInfo("UTC")
        return datetime.now(tz).hour


def _build_scheduler(
    *,
    database_url: str | None,
    timezone: str,
) -> Any:
    """Production scheduler factory.

    Uses ``SQLAlchemyJobStore`` against the configured Postgres URL.
    Falls back to an in-memory store when no URL is set (e.g. during
    smoke tests).
    """

    from apscheduler.schedulers.background import BackgroundScheduler

    jobstores: dict[str, Any] = {}
    if database_url:
        from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore

        jobstores["default"] = SQLAlchemyJobStore(
            url=database_url, tablename="apscheduler_jobs"
        )
    return BackgroundScheduler(jobstores=jobstores, timezone=timezone)


def _build_lock(connection: Any) -> SingleFlightLockProtocol:
    """Production lock factory.

    Uses Postgres advisory locks. Tests inject their own lock via
    direct calls to ``run_orchestrator(...)`` and never reach this
    helper.
    """

    return PostgresAdvisoryLock(connection)


def _run_sweep_with_backoff(
    *,
    attempt: Callable[[], Any],
    max_attempts: int,
    base_backoff_seconds: float,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any:
    """Re-attempt ``attempt()`` (a sweep's ``.tick()`` call) until it
    returns a non-error result or ``max_attempts`` is reached.

    Sleeps ``base_backoff_seconds * 2 ** (attempt - 1)`` between tries
    (exponential backoff: 2s, 4s, 8s with the defaults). A transient
    IBKR hiccup that resolves in ~5s is recovered inside the same
    tick instead of waiting a full ``sweep_interval_seconds`` for the
    next scheduled fire. ``sleep_fn`` is injectable so tests don't
    actually sleep.
    """

    max_attempts = max(1, max_attempts)
    base_backoff_seconds = max(0.0, base_backoff_seconds)
    result = attempt()
    for n in range(1, max_attempts):
        if result.mode != "error":
            return result
        sleep_fn(base_backoff_seconds * (2 ** (n - 1)))
        result = attempt()
    return result


def _is_pre_briefing_run(fire_time: datetime) -> bool:
    """Distinguish the 06:00 fire from the 07:00-21:00 cron expression.

    Both APScheduler jobs report their ``next_run_time`` in the
    configured timezone (Europe/Brussels). The pre-briefing job
    fires at exactly minute 0 of hour 6; the hourly job at minute 0
    of every hour 7-21. So checking the hour value is the cleanest
    discriminator.
    """

    return fire_time.hour == 6


__all__ = [
    "InMemoryLock",
    "PortfolioScheduler",
    "PostgresAdvisoryLock",
    "_PRE_BRIEFING_JOB_ID",
    "_MARKET_CLOSE_JOB_PREFIX",
    "_MARKET_OPEN_JOB_PREFIX",
]
