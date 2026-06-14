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


def _try_connect_ibkr() -> IbkrGateway | None:
    """Open the worker's read-only TWS session.

    Returns the connected gateway so the scheduler can reuse it for
    in-process consumers (V1.2 §BM-2 reconciliation cron). Returns
    ``None`` when the connection wasn't attempted (IBKR disabled,
    no account_id, storage unavailable) or failed.

    NOTE: keeping the session alive (no auto-reconnect heartbeat) is
    GAPS.md P2-1 §BY follow-up territory. Today a dropped session
    surfaces via ``is_connected()=False`` in downstream consumers,
    which then skip their tick gracefully.
    """

    if not settings.ibkr.enabled:
        logger.info(
            "IBKR-verbinding overgeslagen (WORKER_IBKR__ENABLED=false)."
        )
        return None
    if not settings.ibkr.account_id:
        logger.warning(
            "IBKR is ingeschakeld maar WORKER_IBKR__ACCOUNT_ID ontbreekt; "
            "verbinding wordt niet gestart."
        )
        return None
    if (
        not settings.storage.enabled
        or not settings.storage.database_url
    ):
        logger.warning(
            "Opslag is uitgeschakeld of zonder URL; IBKR connect-audit "
            "kan niet worden opgeslagen. Verbinding wordt niet gestart."
        )
        return None

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
                    "IBKR verbonden: account=%s mode=%s connection_id=%s",
                    result.account_id,
                    result.account_mode,
                    result.connection_id,
                )
                # V1.2 §BM-2 / GAPS.md P0-3 — houd de sessie open zodat
                # de in-process reconciliation tick een echte
                # ``IbkrReconcilerGatewayProtocol`` heeft. De gateway
                # wordt netjes afgesloten in de SIGTERM handler.
                return gateway
            logger.warning(
                "IBKR-verbinding geweigerd: %s", result.error_nl
            )
            with suppress(Exception):
                gateway.disconnect()
            return None
    except StorageConnectionError as exc:
        logger.warning(
            "Opslag niet bereikbaar tijdens IBKR-boot: %s; "
            "verbinding overgeslagen.",
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


def _start_scheduler(connected_gateway: IbkrGateway | None = None) -> None:
    """Start the worker scheduler.

    ``connected_gateway`` is the result of :func:`_try_connect_ibkr` —
    when supplied the scheduler reuses that live read-only TWS session,
    so the in-process reconciliation cron (V1.2 §BM-2) sees a real
    ``ib_client`` instead of always skipping with
    ``IBKR gateway niet verbonden``. When ``None`` (IBKR disabled, or
    connect failed) the scheduler falls back to an unconnected stub
    gateway — existing cron jobs (order sweeps, morning chain, …)
    don't depend on the read session.
    """

    global _active_scheduler

    if not settings.scheduler.enabled:
        logger.info("Scheduler is uitgeschakeld.")
        # If we did open an IBKR session purely for the scheduler we
        # never started, close it cleanly here.
        if connected_gateway is not None:
            with suppress(Exception):
                connected_gateway.disconnect()
        return
    gateway = connected_gateway if connected_gateway is not None else IbkrGateway()
    order_adapter = _maybe_open_order_adapter()
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
        digest_runner=digest_runner,
        morning_alerts_runner=morning_alerts_runner,
    )
    try:
        scheduler.start()
    except Exception:  # noqa: BLE001 — boundary
        logger.exception("Scheduler kon niet starten.")
        if connected_gateway is not None:
            with suppress(Exception):
                connected_gateway.disconnect()
        return
    _active_scheduler = scheduler

    def _shutdown(signum: int, _frame: Any) -> None:
        logger.info("Signal %s ontvangen; scheduler wordt afgesloten.", signum)
        if _active_scheduler is not None:
            with suppress(Exception):
                _active_scheduler.stop()
        # V1.2 §BM-2 — close the long-lived IBKR session opened by
        # ``_try_connect_ibkr`` so the TWS client slot is released.
        if connected_gateway is not None:
            with suppress(Exception):
                connected_gateway.disconnect()

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
    connected_gateway = _try_connect_ibkr()
    _start_scheduler(connected_gateway=connected_gateway)


# GAPS.md P4-3 — externe orchestrators (en de smoke-test prompt)
# verwachten een ``main`` symbol; geef ze de bestaande start_worker
# onder die naam zonder de huidige Dockerfile entry te breken.
main = start_worker


if __name__ == "__main__":
    start_worker()
