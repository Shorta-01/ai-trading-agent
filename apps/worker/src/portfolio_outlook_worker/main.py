"""Worker entrypoint.

Task 126: when ``WORKER_IBKR__ENABLED=true`` and storage is reachable,
the worker opens a long-lived TWS session via :class:`IbkrGateway`
on startup. The audit-row writes happen synchronously inside
``gateway.connect(...)`` so a successful boot leaves a
``connect_success`` row in ``ibkr_connection_audit`` for the API to
read.

This file intentionally stays minimal — the sync loop that pulls
positions/cash on a schedule lands in Task 126b alongside the API
route rewrite. 126a only proves the connection + audit pipeline.
"""

from __future__ import annotations

import logging
from contextlib import suppress

from ai_trading_agent_storage import (
    SqlAlchemyIbkrConnectionAuditRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_worker.config import settings
from portfolio_outlook_worker.ibkr_gateway import IbkrGateway

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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


def start_worker() -> None:
    logger.info(
        "Worker gestart (env=%s, paper_only_mode=%s, ibkr_enabled=%s).",
        settings.environment,
        settings.paper_only_mode,
        settings.ibkr.enabled,
    )
    _try_connect_ibkr()


if __name__ == "__main__":
    start_worker()
