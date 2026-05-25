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
from portfolio_outlook_worker.scheduler import PortfolioScheduler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


_active_scheduler: PortfolioScheduler | None = None


def _try_connect_ibkr() -> None:
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
                    "IBKR verbonden: account=%s mode=%s connection_id=%s",
                    result.account_id,
                    result.account_mode,
                    result.connection_id,
                )
            else:
                logger.warning(
                    "IBKR-verbinding geweigerd: %s", result.error_nl
                )
            # 126a: tear the session down at end-of-startup. 126b
            # adds the durable worker-state row + sync loop that
            # keeps the connection open.
            with suppress(Exception):
                gateway.disconnect()
    except StorageConnectionError as exc:
        logger.warning(
            "Opslag niet bereikbaar tijdens IBKR-boot: %s; "
            "verbinding overgeslagen.",
            exc,
        )


def _start_scheduler() -> None:
    global _active_scheduler

    if not settings.scheduler.enabled:
        logger.info("Scheduler is uitgeschakeld.")
        return
    gateway = IbkrGateway()
    scheduler = PortfolioScheduler(
        gateway=gateway,
        storage_settings=settings.storage,
        ibkr_settings=settings.ibkr,
        scheduler_settings=settings.scheduler,
    )
    try:
        scheduler.start()
    except Exception:  # noqa: BLE001 — boundary
        logger.exception("Scheduler kon niet starten.")
        return
    _active_scheduler = scheduler

    def _shutdown(signum: int, _frame: Any) -> None:
        logger.info("Signal %s ontvangen; scheduler wordt afgesloten.", signum)
        if _active_scheduler is not None:
            with suppress(Exception):
                _active_scheduler.stop()

    with suppress(ValueError):
        signal.signal(signal.SIGTERM, _shutdown)
    with suppress(ValueError):
        signal.signal(signal.SIGINT, _shutdown)


def start_worker() -> None:
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


if __name__ == "__main__":
    start_worker()
