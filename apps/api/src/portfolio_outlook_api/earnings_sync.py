"""Earnings calendar refresh (V1.2 §AJ).

Pure-Python writer that takes a provider + repository + symbol list,
fetches upcoming events, and upserts them. Lives separately from the
HTTP client (``eodhd_client.py``) and the route layer
(``earnings_routes.py``) so the same function can be invoked from:

* The manual ``POST /earnings/refresh`` endpoint (operator-triggered).
* The morning-chain orchestrator leg (when the runtime flag wires it
  up in a follow-up slice).
* A standalone CLI for smoke-testing against a paper database.

The provider is a narrow Protocol so tests can inject a fake without
touching the network. The function never raises on provider errors —
it summarises them in the returned dataclass so the caller can audit
what worked and what didn't.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from ai_trading_agent_storage import (
    SaveEarningsEventRequest,
    SqlAlchemyEarningsEventRepository,
)

from portfolio_outlook_api.eodhd_client import EodhdEarningsEvent


class EarningsCalendarProvider(Protocol):
    """Anything that can return upcoming earnings rows for a tuple
    of EODHD-symbols within a window."""

    def fetch_earnings_calendar(
        self,
        *,
        symbols: tuple[str, ...],
        from_date: date,
        to_date: date,
    ) -> list[EodhdEarningsEvent]: ...


@dataclass(frozen=True)
class EarningsRefreshSummary:
    """Counts returned to the caller after one refresh round.

    ``fetched_count`` is the number of provider rows accepted by the
    parser; ``upserted_count`` is the number that survived repository
    validation. ``error_text`` is non-empty when the provider call
    failed outright; ``upserted_count`` will be zero in that case.
    """

    fetched_count: int
    upserted_count: int
    symbols_requested: int
    window_days: int
    error_text: str | None


def _build_earnings_event_id(symbol: str, event_date: date) -> str:
    """Deterministic id so refetches upsert into the same row."""

    return f"{symbol}:{event_date.isoformat()}"


def refresh_earnings_calendar(
    *,
    provider: EarningsCalendarProvider,
    repository: SqlAlchemyEarningsEventRepository,
    symbols: Sequence[str],
    today: date,
    window_days: int,
    source: str,
    fetched_at: datetime,
) -> EarningsRefreshSummary:
    """Fetch + upsert upcoming earnings for ``symbols``.

    ``window_days`` controls how far ahead to ask the provider; 21
    is a sensible default for the morning chain (covers the next
    earnings season but not so wide that EODHD's quota burns).

    Symbols are passed through verbatim; the caller is responsible
    for mapping ``conid → EODHD symbol`` and deduplicating. Empty
    input is a no-op (the function returns a zero summary, not an
    error).
    """

    requested = len(symbols)
    if requested == 0:
        return EarningsRefreshSummary(
            fetched_count=0,
            upserted_count=0,
            symbols_requested=0,
            window_days=window_days,
            error_text=None,
        )
    to_date = date.fromordinal(today.toordinal() + max(1, window_days))
    try:
        events = provider.fetch_earnings_calendar(
            symbols=tuple(symbols),
            from_date=today,
            to_date=to_date,
        )
    except Exception as exc:  # noqa: BLE001 — boundary catch
        return EarningsRefreshSummary(
            fetched_count=0,
            upserted_count=0,
            symbols_requested=requested,
            window_days=window_days,
            error_text=f"{type(exc).__name__}: {exc}",
        )

    upserted = 0
    for event in events:
        try:
            repository.upsert_event(
                SaveEarningsEventRequest(
                    earnings_event_id=_build_earnings_event_id(
                        event.symbol, event.event_date
                    ),
                    symbol=event.symbol,
                    ibkr_conid=None,
                    event_date=event.event_date,
                    status=event.status,
                    source=source,
                    fetched_at=fetched_at,
                    raw_json=event.raw_payload,
                )
            )
            upserted += 1
        except ValueError:
            # Repository contract rejects an invalid row (e.g.
            # unknown status). Skip silently and keep going so a
            # single bad row doesn't tank the whole refresh.
            continue

    return EarningsRefreshSummary(
        fetched_count=len(events),
        upserted_count=upserted,
        symbols_requested=requested,
        window_days=window_days,
        error_text=None,
    )


__all__ = [
    "EarningsCalendarProvider",
    "EarningsRefreshSummary",
    "refresh_earnings_calendar",
]
