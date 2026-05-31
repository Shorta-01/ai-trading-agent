"""Portfolio NAV history endpoint — sparkline feed for the dashboard.

``GET /portfolio/nav/history?days=30`` returns the operator's NAV
time series for the configured IBKR account over the last N days.
Each point is a ``(recorded_at_utc, nav_value)`` pair, ordered
oldest-first so the dashboard sparkline can render left-to-right
without sorting client-side.

Read-only. Never authorises an order, never modifies storage. The
``IbkrNavSnapshotRecord`` rows are written by the worker's sync loop
(read-only IBKR API), so this endpoint just surfaces what's already
there — same source the daily-digest NAV-drop alert uses.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from ai_trading_agent_storage import (
    SqlAlchemyIbkrSyncSnapshotRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_DAYS = 365
_DEFAULT_DAYS = 30


class NavHistoryPoint(BaseModel):
    """One NAV snapshot ready for the sparkline."""

    recorded_at_utc: str
    nav_value: str  # serialised Decimal so the wire is exact


class NavHistoryResponse(BaseModel):
    status: str
    status_nl: str
    help_nl: str
    ibkr_account_id: str | None
    base_currency: str | None
    days_requested: int
    points: list[NavHistoryPoint]


_NAV_HISTORY_HELP_NL = (
    "Tijdreeks van portfolio-NAV-snapshots uit de IBKR read-only sync. "
    "De sparkline laat de evolutie over de gekozen periode zien; bron "
    "is identiek aan de NAV-drop alert in de daily digest. Geen "
    "browser-berekening, geen herwaardering."
)


def _account_id() -> str | None:
    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


def _empty(
    status: str, status_nl: str, days_requested: int
) -> NavHistoryResponse:
    return NavHistoryResponse(
        status=status,
        status_nl=status_nl,
        help_nl=_NAV_HISTORY_HELP_NL,
        ibkr_account_id=_account_id(),
        base_currency=None,
        days_requested=days_requested,
        points=[],
    )


@router.get(
    "/portfolio/nav/history",
    response_model=NavHistoryResponse,
)
def read_nav_history(
    days: int = Query(default=_DEFAULT_DAYS, ge=1, le=_MAX_DAYS),
) -> NavHistoryResponse:
    account_id = _account_id()
    if account_id is None:
        return _empty(
            "no_account_configured",
            "Geen IBKR-rekening geconfigureerd; NAV-historiek leeg.",
            days,
        )
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty(
            "not_configured",
            "Opslag niet geconfigureerd; NAV-historiek niet beschikbaar.",
            days,
        )

    since = datetime.now(UTC) - timedelta(days=days)
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyIbkrSyncSnapshotRepository(
                checked.connection, checked.readiness
            )
            records = repo.list_ibkr_nav_snapshots_since(
                ibkr_account_id=account_id, since=since
            )
    except StorageConnectionError as exc:
        logger.warning("nav history storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    base_currency = records[-1].base_currency if records else None
    points = [
        NavHistoryPoint(
            recorded_at_utc=r.recorded_at.isoformat(),
            nav_value=str(r.nav_value),
        )
        for r in records
    ]
    status_nl = (
        f"{len(points)} NAV-punten over de laatste {days} dagen."
        if points
        else "Nog geen NAV-snapshots in de gekozen periode."
    )
    return NavHistoryResponse(
        status="ok" if points else "no_points",
        status_nl=status_nl,
        help_nl=_NAV_HISTORY_HELP_NL,
        ibkr_account_id=account_id,
        base_currency=base_currency,
        days_requested=days,
        points=points,
    )


__all__ = ["NavHistoryPoint", "NavHistoryResponse", "router"]
