"""Worker entrypoint.

Task 126: when ``WORKER_IBKR__ENABLED=true`` and storage is reachable,
the worker opens a long-lived TWS session via :class:`IbkrGateway`
on startup.

Task 127: when ``WORKER_SCHEDULER__ENABLED=true``, the worker also
starts the :class:`PortfolioScheduler` (locked 06:00 + hourly
07:00-21:00 Europe/Brussels schedule). Both subsystems gate on the
storage layer being reachable; with storage off the worker still
boots, just without persistence-backed audit rows.
"""

from __future__ import annotations

import logging
import signal
from contextlib import suppress
from typing import Any

from ai_trading_agent_storage import (
    SqlAlchemyIbkrConnectionAuditRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.config import settings
from portfolio_outlook_worker.ibkr_gateway import IbkrGateway
from portfolio_outlook_worker.runtime_config_overlay import (
    apply_worker_runtime_config_overlay,
)
from portfolio_outlook_worker.scheduler import PortfolioScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_active_scheduler: PortfolioScheduler | None = None


def _try_connect_ibkr() -> None:
    """Boot-time IBKR-connectie-test (Task 126).

    Opent een tijdelijke read-only TWS-sessie, schrijft de
    ``connect_attempt`` / ``connect_success`` / ``connect_refused``
    audit-rijen die het ``/admin/ibkr/connection-audit`` dashboard
    leest, en disconnect's direct. Bedoeld als sanity-check zodat
    een config-fout opvalt bij worker-boot in plaats van pas bij de
    eerste tick.

    De long-lived sessies voor consumers (orders → ``_maybe_open_order_adapter``,
    reconciler → ``_maybe_open_reconciler_session``) gebruiken hun
    eigen client_id zodat ze niet botsen met deze boot-test.
    """

    if not settings.ibkr.enabled:
        logger.info(
            "IBKR-verbinding overgeslagen (WORKER_IBKR__ENABLED=false)."
        )
        return
    if not settings.ibkr.account_id:
        logger.warning(
            "IBKR is ingeschakeld maar WORKER_IBKR__ACCOUNT_ID ontbreekt; "
            "verbinding wordt niet gestart."
        )
        return
    if (
        not settings.storage.enabled
        or not settings.storage.database_url
    ):
        logger.warning(
            "Opslag is uitgeschakeld of zonder URL; IBKR connect-audit "
            "kan niet worden opgeslagen. Verbinding wordt niet gestart."
        )
        return

    connection_settings = build_database_connection_settings(
        settings.storage.database_url
    )
    provider = StorageConnectionProvider(connection_settings)
    try:
        with provider.checked_connection(require_writable=True) as checked:
            audit_repo = SqlAlchemyIbkrConnectionAuditRepository(
                checked.connection, checked.readiness
            )
            gateway = IbkrGateway(audit_repo=audit_repo)
            result = gateway.connect(
                host=settings.ibkr.host,
                port=settings.ibkr.port,
                client_id=settings.ibkr.client_id,
                account_id=settings.ibkr.account_id,
            )
            if result.connected:
                logger.info(
                    "IBKR boot-test verbonden: account=%s mode=%s connection_id=%s",
                    result.account_id,
                    result.account_mode,
                    result.connection_id,
                )
            else:
                logger.warning(
                    "IBKR boot-test geweigerd: %s", result.error_nl
                )
            with suppress(Exception):
                gateway.disconnect()
    except StorageConnectionError as exc:
        logger.warning(
            "Opslag niet bereikbaar tijdens IBKR-boot: %s; "
            "verbinding overgeslagen.",
            exc,
        )


def _maybe_open_reconciler_session() -> IbkrGateway | None:
    """V1.2 §BM-2 / GAPS.md P0-3 — open een aparte read-only TWS-sessie
    voor de in-process reconciliation cron.

    Gespiegelde architectuur van :func:`_maybe_open_order_adapter`:
    eigen ``client_id`` (``reconciler_session_client_id``) zodat er
    geen client-id collision is met de read-only sync (client_id=1)
    of de order session (client_id=2). De sessie blijft open voor de
    levenstijd van de worker en wordt afgesloten in de SIGTERM
    handler. Default-off: alleen wanneer
    ``scheduler.reconciliation_sweep_trigger_enabled`` AAN staat
    opent de worker deze sessie.
    """

    if not settings.scheduler.reconciliation_sweep_trigger_enabled:
        return None
    ibkr = settings.ibkr
    if not ibkr.enabled or ibkr.account_id is None:
        return None
    if (
        not settings.storage.enabled
        or not settings.storage.database_url
    ):
        return None

    provider = StorageConnectionProvider(
        build_database_connection_settings(settings.storage.database_url)
    )
    try:
        with provider.checked_connection(require_writable=True) as checked:
            audit_repo = SqlAlchemyIbkrConnectionAuditRepository(
                checked.connection, checked.readiness
            )
            gateway = IbkrGateway(audit_repo=audit_repo)
            result = gateway.connect(
                host=ibkr.host,
                port=ibkr.port,
                client_id=ibkr.reconciler_session_client_id,
                account_id=ibkr.account_id,
            )
            if result.connected:
                logger.info(
                    "Reconciler read-only TWS-sessie geopend "
                    "(client_id=%d).",
                    ibkr.reconciler_session_client_id,
                )
                return gateway
            logger.warning(
                "Reconciler-sessie geweigerd: %s", result.error_nl
            )
            with suppress(Exception):
                gateway.disconnect()
            return None
    except StorageConnectionError as exc:
        logger.warning(
            "Opslag niet bereikbaar bij openen reconciler-sessie: %s; "
            "sessie niet gestart.",
            exc,
        )
        return None


def _maybe_open_order_adapter() -> Any | None:
    """Open the writable IBKR order session iff a sweep is enabled (T-045).

    Fails closed: returns None (so no order sweeps register) unless IBKR is
    enabled, an account id is configured, a sweep flag is on, AND
    ``open_order_adapter`` accepts the account under ``paper_only_mode``. Any
    failure returns None — the worker still runs, just without order sweeps.
    """

    ibkr = settings.ibkr
    if not ibkr.enabled or ibkr.account_id is None:
        return None
    if not (ibkr.submission_sweep_enabled or ibkr.cancel_sweep_enabled):
        return None
    from portfolio_outlook_worker.ibkr_submission.ibkr_order_adapter import (
        OrderSessionRefusedError,
        open_order_adapter,
    )

    try:
        adapter = open_order_adapter(
            host=ibkr.host,
            port=ibkr.port,
            client_id=ibkr.order_session_client_id,
            account_id=ibkr.account_id,
            session_id=f"order-{ibkr.account_id}",
            paper_only_mode=settings.paper_only_mode,
        )
    except OrderSessionRefusedError as exc:
        logger.error("Order-sessie geweigerd; sweeps blijven uit: %s", exc)
        return None
    except Exception:  # noqa: BLE001 — boundary
        logger.exception("Order-sessie kon niet openen; sweeps blijven uit.")
        return None
    logger.info("Writable IBKR order-sessie geopend (paper-gated).")
    return adapter


def _start_scheduler() -> None:
    """Start the worker scheduler.

    The scheduler owns three IBKR-related slots:
    * ``gateway`` — a stub IbkrGateway (existing behaviour); existing
      cron jobs (order sweeps, morning chain, …) don't depend on it.
    * ``order_adapter`` — writable order session, opened by
      :func:`_maybe_open_order_adapter` when an order sweep is enabled.
    * ``reconciler_gateway`` — V1.2 §BM-2 / GAPS.md P0-3 dedicated
      read-only TWS session, opened by
      :func:`_maybe_open_reconciler_session` only when
      ``reconciliation_sweep_trigger_enabled`` is True. Mirrors the
      order_adapter pattern so the reconciler's TWS slot is fully
      independent of the boot-time IBKR connection-audit and of the
      order sweeps.
    """

    global _active_scheduler

    if not settings.scheduler.enabled:
        logger.info("Scheduler is uitgeschakeld.")
        return
    gateway = IbkrGateway()
    order_adapter = _maybe_open_order_adapter()
    reconciler_gateway = _maybe_open_reconciler_session()
    # End-of-day digest runner — fired by the orchestrator on every
    # market_close event. Reads positions/suggestions/drafts/NAV from
    # storage, computes the digest, persists it, and (when the
    # operator has enabled email notifications + filled SMTP creds)
    # sends the digest email.
    from portfolio_outlook_worker.digest_runner import DailyDigestRunner
    from portfolio_outlook_worker.morning_alerts_runner import (
        MorningAlertsRunner,
    )

    digest_runner = DailyDigestRunner(
        storage_settings=settings.storage,
        notifications=settings.notifications,
        api_base_url=settings.scheduler.api_base_url,
        api_request_timeout_seconds=settings.scheduler.api_request_timeout_seconds,
    )
    # Morning-chain alerts runner — fired on morning_briefing AFTER
    # the decision-package step so it sees today's suggestions. Same
    # email transport as the digest; uses the same notification
    # preferences (send_on_high_confidence_sell).
    morning_alerts_runner = MorningAlertsRunner(
        storage_settings=settings.storage,
        notifications=settings.notifications,
        api_base_url=settings.scheduler.api_base_url,
        api_request_timeout_seconds=settings.scheduler.api_request_timeout_seconds,
    )
    scheduler = PortfolioScheduler(
        gateway=gateway,
        storage_settings=settings.storage,
        ibkr_settings=settings.ibkr,
        scheduler_settings=settings.scheduler,
        order_adapter=order_adapter,
        reconciler_gateway=reconciler_gateway,
        digest_runner=digest_runner,
        morning_alerts_runner=morning_alerts_runner,
    )
    try:
        scheduler.start()
    except Exception:  # noqa: BLE001 — boundary
        logger.exception("Scheduler kon niet starten.")
        if reconciler_gateway is not None:
            with suppress(Exception):
                reconciler_gateway.disconnect()
        return
    _active_scheduler = scheduler

    def _shutdown(signum: int, _frame: Any) -> None:
        logger.info("Signal %s ontvangen; scheduler wordt afgesloten.", signum)
        if _active_scheduler is not None:
            with suppress(Exception):
                _active_scheduler.stop()
        # V1.2 §BM-2 — sluit de reconciler-sessie zodat de TWS-slot
        # vrij komt.
        if reconciler_gateway is not None:
            with suppress(Exception):
                reconciler_gateway.disconnect()

    with suppress(ValueError):
        signal.signal(signal.SIGTERM, _shutdown)
    with suppress(ValueError):
        signal.signal(signal.SIGINT, _shutdown)


def start_worker() -> None:
    # Settings UI PR D — pull operator-edited sweep/EODHD values from
    # runtime_config BEFORE the scheduler registers interval jobs so
    # the cadence picked up matches what the operator saved on the
    # Settings page.
    apply_worker_runtime_config_overlay(settings)
    logger.info(
        "Worker gestart (env=%s, paper_only_mode=%s, ibkr_enabled=%s, "
        "scheduler_enabled=%s).",
        settings.environment,
        settings.paper_only_mode,
        settings.ibkr.enabled,
        settings.scheduler.enabled,
    )
    _try_connect_ibkr()
    _start_scheduler()


# GAPS.md P4-3 — externe orchestrators (en de smoke-test prompt)
# verwachten een ``main`` symbol; geef ze de bestaande start_worker
# onder die naam zonder de huidige Dockerfile entry te breken.
main = start_worker


if __name__ == "__main__":
    start_worker()
