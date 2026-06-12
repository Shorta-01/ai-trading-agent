"""Upcoming earnings calendar endpoint (V1.2 §AI).

Reads the ``earnings_events`` table populated by the EODHD writer
leg (follow-up §AJ) and surfaces the most-imminent earnings events
within a configurable window. Powers two consumers:

* The dashboard's ``EarningsThisWeekStrip`` — replaces the previous
  workaround that filtered orchestrator verdicts for
  ``decision == "skip_earnings_window"``.
* The orchestrator candidate provider (via
  :meth:`SqlAlchemyEarningsEventRepository.get_next_for_symbols`) —
  feeds the locked earnings-window gate.

Read-only; never raises except on storage-niet-beschikbaar (503).
When the table is empty (no writer leg wired yet), the endpoint
returns ``items=[]`` and the dashboard falls back gracefully.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime, timedelta

from ai_trading_agent_storage import (
    SqlAlchemyEarningsEventRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from portfolio_outlook_api.config import settings

logger = logging.getLogger(__name__)

router = APIRouter()


class EarningsEventRow(BaseModel):
    earnings_event_id: str
    symbol: str
    ibkr_conid: str | None
    event_date: str
    status: str
    source: str
    fetched_at: str


class EarningsUpcomingResponse(BaseModel):
    title_nl: str
    help_nl: str
    window_days: int
    items: list[EarningsEventRow]


_HELP_NL = (
    "Aankomende earnings-events binnen het opgegeven venster, "
    "soonest first. Confirmed en estimated events worden getoond; "
    "past events worden door de gate uitgesloten."
)

_DEFAULT_WINDOW_DAYS = 14
_MAX_WINDOW_DAYS = 60


def _empty_response(window_days: int) -> EarningsUpcomingResponse:
    return EarningsUpcomingResponse(
        title_nl="Aankomende earnings",
        help_nl=_HELP_NL,
        window_days=window_days,
        items=[],
    )


@router.get("/earnings/upcoming", response_model=EarningsUpcomingResponse)
def get_upcoming_earnings(
    days: int = _DEFAULT_WINDOW_DAYS,
) -> EarningsUpcomingResponse:
    """Return upcoming earnings events within ``days`` of today.

    Defaults to 14-day window. Hard cap at 60 days so a careless
    ``?days=9999`` doesn't return three years of data.
    """

    if days <= 0:
        raise HTTPException(status_code=400, detail="days moet > 0 zijn")
    if days > _MAX_WINDOW_DAYS:
        days = _MAX_WINDOW_DAYS

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return _empty_response(days)

    today = datetime.now(tz=UTC).date()
    upper: date = today + timedelta(days=days)

    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            repo = SqlAlchemyEarningsEventRepository(
                checked.connection, checked.readiness
            )
            result = repo.list_upcoming(
                from_date=today, to_date=upper, limit=200
            )
    except StorageConnectionError as exc:
        logger.warning("earnings-upcoming storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    items = [
        EarningsEventRow(
            earnings_event_id=rec.earnings_event_id,
            symbol=rec.symbol,
            ibkr_conid=rec.ibkr_conid,
            event_date=rec.event_date.isoformat(),
            status=rec.status,
            source=rec.source,
            fetched_at=rec.fetched_at.isoformat(),
        )
        for rec in result.records
    ]
    return EarningsUpcomingResponse(
        title_nl="Aankomende earnings",
        help_nl=_HELP_NL,
        window_days=days,
        items=items,
    )


__all__ = ["router"]
