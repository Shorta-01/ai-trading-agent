"""Operator-configureerbaar winstdoel (V1.2 §AZ).

Centrale lookup zodat alle rapporten / engines dezelfde drempel
gebruiken. CLAUDE.md §6.1 vergrendelt 4 % als doctrine-default; deze
helper geeft die terug wanneer de operator niets heeft gekozen.

Read-only; storage-fout → doctrine-default.
"""

from __future__ import annotations

import logging
from decimal import Decimal

from ai_trading_agent_storage import (
    SqlAlchemyRuntimeConfigRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

DOCTRINE_DEFAULT_PCT = Decimal("4")


def get_profit_target_pct() -> Decimal:
    """Return the operator-configured target, or 4 % when unset.

    Defensive: any storage hiccup falls back to the doctrine default
    so the rapporten/belasting endpoints nooit een 5xx geven over
    een gemiste config-lookup.
    """

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return DOCTRINE_DEFAULT_PCT
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyRuntimeConfigRepository(
                checked.connection, checked.readiness
            )
            record = repo.get()
    except StorageConnectionError as exc:
        logger.warning("profit-target lookup storage error: %s", exc)
        return DOCTRINE_DEFAULT_PCT
    if record is None or record.profit_target_net_pct is None:
        return DOCTRINE_DEFAULT_PCT
    return record.profit_target_net_pct


__all__ = ["DOCTRINE_DEFAULT_PCT", "get_profit_target_pct"]
