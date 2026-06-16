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
    trigger_macro_feed_refresh,
    trigger_monthly_archive_auto_generate,
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
_MONTHLY_ARCHIVE_JOB_ID = "monthly_archive_auto_generate"
_MACRO_FEED_REFRESH_JOB_ID = "macro_feed_refresh"
_RECONCILIATION_SWEEP_JOB_ID = "reconciliation_sweep_trigger"
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
        reconciler_gateway: Any | None = None,
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
        # V1.2 §BM-2 / GAPS.md P0-3 — dedicated read-only TWS session
        # for the in-process reconciliation cron. Mirrors order_adapter:
        # ``None`` (default) means the reconciler tick falls through to
        # the disconnected stub gateway and skips with
        # ``IBKR gateway niet verbonden``. ``main._maybe_open_reconciler_session``
        # injects a live gateway when the reconciliation cron is on.
        self._reconciler_gateway = reconciler_gateway
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
        # Monthly report auto-archive — V1.2 §BN. CLAUDE.md §13.
        # Default cron: 00:15 op de 1e van elke maand (Europe/Brussels)
        # — vroeg genoeg dat de PDF beschikbaar is wanneer operator
        # 's ochtends het dashboard opent. API berekent zelf welke
        # maand er gearchiveerd moet worden (vorige kalendermaand).
        if self._scheduler_settings.monthly_archive_auto_generate_enabled:
            self._scheduler.add_job(
                self._on_monthly_archive_auto_generate_trigger,
                trigger=self._build_monthly_archive_auto_generate_trigger(),
                id=_MONTHLY_ARCHIVE_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_CRON_MISFIRE_GRACE_SECONDS,
            )
        # Macro feed refresh — V1.2 §BT / GAPS.md P1-10. CLAUDE.md
        # §7.2 macro-regime gate vereist verse VIX + S&P 500 bars.
        # Default cron: dagelijks 17:30 Europe/Brussels (~ post-
        # Euronext close, vóór 18:00 EU/US-overlap waar VIX nog
        # actief beweegt). Werkdag-only.
        if self._scheduler_settings.macro_feed_refresh_enabled:
            self._scheduler.add_job(
                self._on_macro_feed_refresh_trigger,
                trigger=self._build_macro_feed_refresh_trigger(),
                id=_MACRO_FEED_REFRESH_JOB_ID,
                replace_existing=True,
                max_instances=1,
                coalesce=True,
                misfire_grace_time=_CRON_MISFIRE_GRACE_SECONDS,
            )
        # Action-draft reconciliation sweep — V1.2 §BM / GAPS.md P0-3.
        # CLAUDE.md §2 audit-trail-doctrine vraagt dat filled orders
        # automatisch submitted → filled / cancelled / rejected zien
        # transitioneren. Tot deze cron werd reconcile alleen
        # handmatig getriggerd, en het dashboard toonde stale
        # "submitted" badges. Default cron: elke 30 minuten op
        # weekdagen (incl. off-hours zodat laat-afgevuurde executions
        # snel binnenkomen).
        if self._scheduler_settings.reconciliation_sweep_trigger_enabled:
            self._scheduler.add_job(
                self._on_reconciliation_sweep_trigger,
                trigger=self._build_reconciliation_sweep_trigger(),
                id=_RECONCILIATION_SWEEP_JOB_ID,
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

    def _build_monthly_archive_auto_generate_trigger(self) -> Any:
        """Parse de geconfigureerde 5-field cron voor auto-archief
        (V1.2 §BN)."""

        from apscheduler.triggers.cron import CronTrigger

        parts = (
            self._scheduler_settings.monthly_archive_auto_generate_cron or ""
        ).strip().split()
        if len(parts) != 5:
            raise ValueError(
                "scheduler.monthly_archive_auto_generate_cron must be a "
                f"5-field cron, got "
                f"{self._scheduler_settings.monthly_archive_auto_generate_cron!r}"
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

    def _on_monthly_archive_auto_generate_trigger(self) -> None:
        trigger_monthly_archive_auto_generate(
            base_url=self._scheduler_settings.api_base_url,
            timeout_seconds=self._scheduler_settings.api_request_timeout_seconds,
        )

    def _build_macro_feed_refresh_trigger(self) -> Any:
        """Parse de geconfigureerde 5-field cron voor macro-feed
        refresh (V1.2 §BT)."""

        from apscheduler.triggers.cron import CronTrigger

        parts = (
            self._scheduler_settings.macro_feed_refresh_cron or ""
        ).strip().split()
        if len(parts) != 5:
            raise ValueError(
                "scheduler.macro_feed_refresh_cron must be a 5-field cron, "
                f"got {self._scheduler_settings.macro_feed_refresh_cron!r}"
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

    def _on_macro_feed_refresh_trigger(self) -> None:
        trigger_macro_feed_refresh(
            base_url=self._scheduler_settings.api_base_url,
            timeout_seconds=self._scheduler_settings.api_request_timeout_seconds,
        )

    def _build_reconciliation_sweep_trigger(self) -> Any:
        """Parse de geconfigureerde 5-field cron voor de reconciliation
        sweep (V1.2 §BM / GAPS.md P0-3)."""

        from apscheduler.triggers.cron import CronTrigger

        parts = (
            self._scheduler_settings.reconciliation_sweep_cron or ""
        ).strip().split()
        if len(parts) != 5:
            raise ValueError(
                "scheduler.reconciliation_sweep_cron must be a 5-field cron, "
                f"got {self._scheduler_settings.reconciliation_sweep_cron!r}"
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

    def _on_reconciliation_sweep_trigger(self) -> None:
        """V1.2 §BM / GAPS.md P0-3 — in-process call to
        ``IbkrReconciler.tick()``.

        Earlier iterations of this PR called the legacy
        ``POST /action-drafts/reconcile`` endpoint, which only does
        snapshot-based action_draft.status transitions and never writes
        the audit queues the ``/admin/reconciliation`` dashboard reads.
        The in-process runner builds the full 3-pass reconciler from
        the worker's read-only TWS session, so Pass A / Pass B / Pass C
        rows now appear in ``reconciliation_run_audit``,
        ``unmatched_execution_audit`` and ``manual_review_queue``.
        """

        if (
            not self._storage_settings.enabled
            or not self._storage_settings.database_url
        ):
            return
        ibkr_account_id = self._ibkr_settings.account_id
        if ibkr_account_id is None:
            logger.info(
                "reconciler tick skipped: geen IBKR account_id geconfigureerd"
            )
            return
        # V1.2 §BM-2 / GAPS.md P0-3 — gebruik de dedicated reconciler
        # gateway (eigen client_id, ge-opened door
        # ``main._maybe_open_reconciler_session``). Backwards-compat:
        # wanneer geen reconciler_gateway is geinjecteerd (legacy code-
        # paths of tests die de gateway direct injecten) valt het terug
        # op de hoofdgateway zodat de bestaande wiring blijft werken.
        reconciler_gateway = self._reconciler_gateway or self._gateway
        get_client = getattr(reconciler_gateway, "get_read_ib_client", None)
        if get_client is None:
            logger.info(
                "reconciler tick skipped: gateway expose't geen ib_client"
            )
            return
        ib_client = get_client()
        if ib_client is None:
            logger.info(
                "reconciler tick skipped: IBKR gateway niet verbonden"
            )
            return

        from datetime import timedelta as _timedelta

        from portfolio_outlook_worker.ibkr_reconciliation.reconciler_runner import (
            build_storage_provider,
            run_reconciler_tick,
        )

        storage_provider = build_storage_provider(
            self._storage_settings.database_url
        )
        pass_c_timeout_cutoff = _timedelta(
            hours=max(
                1, self._ibkr_settings.reconciler_pass_c_timeout_hours
            )
        )
        # Cast keeps mypy honest about the gateway → ReadCapable bridge:
        # the SDK's IB and the worker test fakes structurally satisfy
        # ReadCapableIbClientProtocol (reqExecutions + trades), but the
        # IbClientProtocol the gateway exposes is a permissive subset.
        from typing import cast as _cast

        from portfolio_outlook_worker.ibkr_reconciliation.ibkr_reconciliation_adapter import (
            ReadCapableIbClientProtocol as _ReadCapable,
        )

        result = run_reconciler_tick(
            storage_provider=storage_provider,
            ib_client=_cast(_ReadCapable, ib_client),
            gateway=reconciler_gateway,
            lock_factory=_build_lock,
            ibkr_account_id=ibkr_account_id,
            pass_c_timeout_cutoff=pass_c_timeout_cutoff,
        )
        if result is None:
            return
        logger.info(
            "reconciler tick: mode=%s pass_a=%d pass_b=%d pass_c=%d",
            result.mode_detected,
            result.pass_a_orphaned_count,
            result.pass_b_stale_count,
            result.pass_c_timeout_count,
        )
        self._track_sweep_outcome(
            kind="reconciliation",
            mode=(
                "error" if result.mode_detected == "error" else "ok"
            ),
            error_message=(
                str(result.error_details_json)
                if result.error_details_json
                else None
            ),
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
        # GAPS.md P2-1 / V1.2 §BY — TWS reset's elke nacht (~23:45),
        # netwerk-hick-ups droppen de sessie. Tot deze hook bleef de
        # gateway gewoon ``is_connected()=False`` voor altijd; nu
        # probeert de heartbeat te reconnecten zodat de in-process
        # reconciliation tick + andere consumers de volgende cyclus
        # weer een echte client zien. Default-off zodat bestaande
        # deploys onveranderd blijven; opt-in via ``ibkr_auto_reconnect_enabled``.
        self._maybe_reconnect_ibkr_gateway()
        # V1.2 §BZ follow-up: zelfde heartbeat-pattern voor de order-
        # sessie zodat een gedropte order_adapter ook wordt heropend.
        self._maybe_reconnect_order_adapter()
        # V1.2 §BZ vervolg: SIGHUP heeft mogelijk gevraagd om een
        # runtime_config reload. Het signaal-pad mag geen storage I/O
        # doen; dat gebeurt safely hier op de heartbeat-thread.
        self._maybe_reload_runtime_config()

    def _maybe_reload_runtime_config(self) -> None:
        """V1.2 §BZ vervolg — runtime_config reload met twee triggers.

        Trigger A (SIGHUP): ``main._sighup`` zet
        ``_runtime_config_reload_requested=True`` zodat operators
        ``docker exec worker kill -SIGHUP 1`` kunnen gebruiken.

        Trigger B (auto-poll): elke heartbeat polled
        ``runtime_config.updated_at`` van de DB en triggert een reload
        wanneer die tijdstempel nieuwer is dan de laatst geziene. Dit
        is het cross-container vriendelijke pad — operator slaat op
        via ``/instellingen`` en hoeft niks meer manueel te doen.

        Best-effort: alle exceptions worden gelogd maar nooit
        gepropageerd; een heartbeat-tick mag nooit crashen."""

        should_reload = bool(
            getattr(self, "_runtime_config_reload_requested", False)
        )
        # Direct resetten zodat een herhaalde fout niet elke heartbeat
        # opnieuw probeert.
        self._runtime_config_reload_requested = False

        # Trigger B: poll runtime_config.updated_at.
        if not should_reload:
            should_reload = self._poll_runtime_config_changed()

        if not should_reload:
            return

        try:
            from portfolio_outlook_worker.config import settings
            from portfolio_outlook_worker.runtime_config_overlay import (
                apply_worker_runtime_config_overlay,
            )

            previous_account_id = self._ibkr_settings.account_id
            apply_worker_runtime_config_overlay(settings)
            new_account_id = settings.ibkr.account_id
            # Sync de scheduler's eigen reference zodat de
            # reconnect-heartbeats de nieuwe waarde zien.
            self._ibkr_settings = settings.ibkr
            logger.info(
                "Runtime-config reload: account_id %s → %s",
                previous_account_id,
                new_account_id,
            )
            # V1.2 §BZ vervolg — schrijf een SystemEvent zodat de
            # operator visueel feedback krijgt dat de auto-reload
            # werkt (banner verschijnt op /portefeuille).
            if previous_account_id != new_account_id:
                from portfolio_outlook_worker.error_capture import (
                    record_worker_event,
                )

                record_worker_event(
                    storage_settings=self._storage_settings,
                    source_component="scheduler",
                    event_code="runtime_config_reloaded",
                    severity="info",
                    category="ibkr_config_change",
                    title_nl="Worker config opnieuw geladen",
                    message_nl=(
                        f"De worker heeft het nieuwe IBKR account-id "
                        f"opgepikt: {previous_account_id} → "
                        f"{new_account_id}. Sweeps + reconciler "
                        f"gebruiken vanaf nu het nieuwe account."
                    ),
                    help_nl=(
                        "Geen actie vereist. Deze melding is een "
                        "bevestiging dat /instellingen wijzigingen "
                        "binnen zijn gekomen."
                    ),
                    technical_summary=(
                        f"previous={previous_account_id} "
                        f"new={new_account_id}"
                    ),
                )
                # V1.2 §BZ vervolg — proactive disconnect van bestaande
                # TWS-sessies zodat ze NIET tegen het oude account-id
                # blijven hangen. De §BY reconnect-heartbeat pikt het
                # op de volgende tick weer op en re-establishet ze met
                # het nieuwe account-id. Best-effort: een disconnect-
                # fout mag de reload-loop niet kapot maken.
                self._disconnect_sessions_for_account_change()
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "Runtime-config reload mislukt; oude waarden blijven actief."
            )
            # V1.2 §BZ vervolg — schrijf een SystemEvent (severity
            # ``error``) zodat de operator OP /portefeuille ziet dat
            # de auto-reload faalde. Tot deze toevoeging werd de
            # fout alleen gelogd; de operator wist niet beter dan
            # dat zijn /instellingen save was opgepikt.
            from contextlib import suppress as _suppress

            with _suppress(Exception):
                from portfolio_outlook_worker.error_capture import (
                    record_worker_event,
                )

                record_worker_event(
                    storage_settings=self._storage_settings,
                    source_component="scheduler",
                    event_code="runtime_config_reload_failed",
                    severity="error",
                    category="ibkr_config_change",
                    title_nl="Worker config-reload mislukt",
                    message_nl=(
                        f"De worker kon de nieuwe IBKR-instellingen "
                        f"niet toepassen. Oude waarden blijven actief. "
                        f"Technische details: {type(exc).__name__}."
                    ),
                    help_nl=(
                        "Controleer de worker-log voor de stack trace. "
                        "Als de fout aanhoudt, herstart de worker met "
                        "``docker compose restart worker``."
                    ),
                    technical_summary=str(exc)[:500],
                )

    def _disconnect_sessions_for_account_change(self) -> None:
        """V1.2 §BZ vervolg — disconnect ``_reconciler_gateway`` en
        ``_order_adapter`` zodat de §BY reconnect-heartbeat ze
        re-establishet met het nieuwe ``account_id``.

        Roept bewust GEEN reconnect logic zelf aan — dat is de
        verantwoordelijkheid van ``_maybe_reconnect_ibkr_gateway`` en
        ``_maybe_reconnect_order_adapter``, die op de volgende
        heartbeat al de juiste account-id zien (we syncten
        ``self._ibkr_settings = settings.ibkr`` net hierboven).
        """

        from contextlib import suppress

        if self._reconciler_gateway is not None:
            disconnect = getattr(self._reconciler_gateway, "disconnect", None)
            if disconnect is not None:
                with suppress(Exception):
                    disconnect()
                    logger.info(
                        "Reconciler gateway disconnected na account-id "
                        "wijziging; volgende heartbeat reconnect."
                    )
        if self._order_adapter is not None:
            # ``IbkrOrderAdapter.reconnect()`` doet zelf disconnect +
            # reconnect. Wij willen alleen disconnect; check eerst of er
            # een ``disconnect``/``_ib.disconnect`` is, anders skip.
            ib_attr = getattr(self._order_adapter, "_ib", None)
            if ib_attr is not None:
                disconnect = getattr(ib_attr, "disconnect", None)
                if disconnect is not None:
                    with suppress(Exception):
                        disconnect()
                        logger.info(
                            "Order adapter disconnected na account-id "
                            "wijziging; volgende heartbeat reconnect."
                        )

    def _fetch_runtime_config_record(self) -> Any | None:
        """Storage-side helper voor :meth:`_poll_runtime_config_changed`.

        Geseparated zodat tests dit makkelijk kunnen patchen zonder
        storage-internals te moeten faken. Returns ``None`` bij
        elke fout of ontbrekende DB-rij."""

        storage = self._storage_settings
        if not storage.enabled or not storage.database_url:
            return None
        try:
            from ai_trading_agent_storage import (
                SqlAlchemyRuntimeConfigRepository,
                StorageConnectionProvider,
                build_database_connection_settings,
            )

            provider = StorageConnectionProvider(
                build_database_connection_settings(storage.database_url)
            )
            with provider.checked_connection(
                require_writable=False
            ) as checked:
                repo = SqlAlchemyRuntimeConfigRepository(
                    checked.connection, checked.readiness
                )
                return repo.get()
        except Exception:  # noqa: BLE001 — boundary
            return None

    def _poll_runtime_config_changed(self) -> bool:
        """Returns True wanneer ``runtime_config.updated_at`` nieuwer is
        dan de laatst geziene waarde, OF wanneer dit de eerste poll na
        boot is en er al een DB-rij bestaat (cold-start case).

        Best-effort: storage-fouten geven False terug zonder log-spam
        op elke heartbeat (één warn-log per session)."""

        record = self._fetch_runtime_config_record()
        if record is None:
            return False
        last_seen = getattr(self, "_last_runtime_config_updated_at", None)
        if last_seen is None:
            # Eerste poll: markeer als gezien (cold-start = geen reload
            # nodig; we hebben net apply_worker_runtime_config_overlay
            # bij boot al gedraaid).
            self._last_runtime_config_updated_at = record.updated_at
            return False
        if record.updated_at > last_seen:
            self._last_runtime_config_updated_at = record.updated_at
            return True
        return False

    def _maybe_reconnect_ibkr_gateway(self) -> None:
        """Re-open de TWS-sessie wanneer de heartbeat detecteert dat
        de dedicated reconciler-gateway niet meer verbonden is.

        Na V1.2 §BM-2 is de hoofdgateway (``self._gateway``) een
        disconnected boot-stub; alleen ``self._reconciler_gateway``
        houdt een long-lived TWS-sessie. De heartbeat target't die
        sessie en gebruikt ``reconciler_session_client_id`` voor de
        reconnect.

        Doctrine-locks:
        * Default ``ibkr_auto_reconnect_enabled=False`` zodat enkel
          operators die de persistent-session expliciet gebruiken
          (b.v. reconciliation cron) hiervoor opt-in.
        * Geen reconnect zonder configured account_id of zonder
          ``ibkr.enabled``.
        * Reconnect-fout wordt gelogd maar gooit niet — een gevallen
          heartbeat mag nooit de scheduler-loop crashen.
        """

        if not self._ibkr_settings.ibkr_auto_reconnect_enabled:
            return
        if not self._ibkr_settings.enabled:
            return
        if self._ibkr_settings.account_id is None:
            return
        gateway = self._reconciler_gateway
        if gateway is None:
            return
        # The scheduler's gateway is typed ``Any`` (a test stub may not
        # implement ``connect``); duck-type the check so the heartbeat
        # never raises.
        try:
            if gateway.is_connected():
                return
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("IBKR is_connected check raised; skip reconnect.")
            return
        connect = getattr(gateway, "connect", None)
        if connect is None:
            return
        try:
            result = connect(
                host=self._ibkr_settings.host,
                port=self._ibkr_settings.port,
                client_id=self._ibkr_settings.reconciler_session_client_id,
                account_id=self._ibkr_settings.account_id,
            )
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("IBKR auto-reconnect attempt raised.")
            return
        if getattr(result, "connected", False):
            logger.info("IBKR auto-reconnect: opnieuw verbonden.")
        else:
            logger.warning(
                "IBKR auto-reconnect: connect geweigerd (%s).",
                getattr(result, "error_nl", "onbekende reden"),
            )

    def _maybe_reconnect_order_adapter(self) -> None:
        """V1.2 §BZ follow-up: zelfde heartbeat-pattern voor de
        order_adapter sessie.

        Wanneer de order-sessie 's nachts dropt (TWS reset, netwerk),
        blijven de submission + cancel sweeps stilletjes skip'en tot
        de operator de worker herstart. De heartbeat detecteert dat
        en heropent de sessie via ``adapter.reconnect()``.
        """

        if not self._ibkr_settings.ibkr_auto_reconnect_enabled:
            return
        if self._order_adapter is None:
            return
        is_connected = getattr(self._order_adapter, "is_connected", None)
        if is_connected is None:
            return
        try:
            if is_connected():
                return
        except Exception:  # noqa: BLE001 — boundary
            logger.exception(
                "Order-adapter is_connected check raised; skip reconnect."
            )
            return
        reconnect = getattr(self._order_adapter, "reconnect", None)
        if reconnect is None:
            return
        try:
            reconnected = bool(reconnect())
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("Order-adapter reconnect attempt raised.")
            return
        if reconnected:
            logger.info("Order-adapter auto-reconnect: opnieuw verbonden.")
        else:
            logger.warning(
                "Order-adapter auto-reconnect: heropenen mislukt; sweeps "
                "blijven skip'en tot volgende heartbeat."
            )

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
