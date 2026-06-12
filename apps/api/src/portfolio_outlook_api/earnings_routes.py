"""Earnings calendar endpoints (V1.2 §AI + §AJ).

* ``GET /earnings/upcoming`` — read-side; reads the
  ``earnings_events`` table and surfaces upcoming events.
* ``POST /earnings/refresh`` — write-side; calls the EODHD adapter
  for the given symbols and upserts via the repository.

Read-side never raises except on storage failure (503). Write-side
short-circuits with ``status="skipped"`` when the EODHD key is
missing so the endpoint stays useful in dev/paper deployments.
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
from portfolio_outlook_api.earnings_sync import refresh_earnings_calendar
from portfolio_outlook_api.eodhd_client import EodhdClient

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


class EarningsRefreshRequest(BaseModel):
    symbols: list[str]
    window_days: int = 21


class EarningsRefreshResponse(BaseModel):
    status: str  # ok | skipped | error
    fetched_count: int
    upserted_count: int
    symbols_requested: int
    window_days: int
    error_text: str | None
    safe_for_orders: bool


_MAX_REFRESH_WINDOW_DAYS = 90


@router.post("/earnings/refresh", response_model=EarningsRefreshResponse)
def post_refresh_earnings(
    payload: EarningsRefreshRequest,
) -> EarningsRefreshResponse:
    """Trigger a synchronous earnings calendar refresh for the given
    EODHD-shaped symbols (``AAPL.US``, ``ASML.AS``, …).

    Short-circuits with ``skipped`` when:
    * The operator's EODHD key is missing, or
    * Storage is disabled.

    Caps ``window_days`` at 90 so a bug in the caller doesn't burn
    EODHD quota.
    """

    if not payload.symbols:
        raise HTTPException(status_code=400, detail="symbols mag niet leeg zijn")
    if payload.window_days <= 0:
        raise HTTPException(status_code=400, detail="window_days moet > 0 zijn")
    window_days = min(payload.window_days, _MAX_REFRESH_WINDOW_DAYS)

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        return EarningsRefreshResponse(
            status="skipped",
            fetched_count=0,
            upserted_count=0,
            symbols_requested=len(payload.symbols),
            window_days=window_days,
            error_text="Opslag is uitgeschakeld of database_url ontbreekt.",
            safe_for_orders=False,
        )

    api_key = getattr(settings, "eodhd_api_key", None)
    if not api_key:
        return EarningsRefreshResponse(
            status="skipped",
            fetched_count=0,
            upserted_count=0,
            symbols_requested=len(payload.symbols),
            window_days=window_days,
            error_text="EODHD api-key ontbreekt — voeg ``eodhd_api_key`` toe.",
            safe_for_orders=False,
        )

    now = datetime.now(tz=UTC)
    try:
        provider_conn = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider_conn.checked_connection(require_writable=True) as checked:
            client = EodhdClient(api_key=api_key)
            repo = SqlAlchemyEarningsEventRepository(
                checked.connection, checked.readiness
            )
            summary = refresh_earnings_calendar(
                provider=client,
                repository=repo,
                symbols=payload.symbols,
                today=now.date(),
                window_days=window_days,
                source="eodhd",
                fetched_at=now,
            )
            # ``checked_connection`` doesn't auto-commit; the upserts
            # must persist past the context-manager close.
            checked.connection.commit()
    except StorageConnectionError as exc:
        logger.warning("earnings-refresh storage error: %s", exc)
        raise HTTPException(
            status_code=503, detail="Opslag is niet beschikbaar."
        ) from exc

    return EarningsRefreshResponse(
        status="error" if summary.error_text else "ok",
        fetched_count=summary.fetched_count,
        upserted_count=summary.upserted_count,
        symbols_requested=summary.symbols_requested,
        window_days=summary.window_days,
        error_text=summary.error_text,
        safe_for_orders=False,
    )


__all__ = ["router"]
