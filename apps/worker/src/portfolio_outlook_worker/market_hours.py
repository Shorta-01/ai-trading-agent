"""Locked mapping of operator-selectable index codes to market sessions.

Used by the scheduler to register market-aware cron fires (per-market
close digest, optional per-market open check). Replaces the previous
``hour="7-21"`` dumb hourly cadence with one that fires only when a
market the operator actually follows opens or closes.

The mapping is deliberately conservative:
- Regular session times only — pre/post market hours are out of scope.
- Times are local to each exchange; APScheduler handles DST via the
  ``timezone`` argument on the cron trigger.
- Holidays + half-days are NOT honoured in this v1 module; the handler
  itself can skip work via short-circuits when there's nothing to do.
  A follow-up can wire ``exchange_calendars`` for full holiday support.

The single source of truth for locked-index-code → exchange-session
mapping. Both the worker scheduler (job registration) and the API
``/settings/market-events`` endpoint (display) read this module.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class MarketSession:
    """One regular-session window for one exchange (or set of cross-listed
    Euronext venues)."""

    code: str
    """Internal stable code, e.g. ``"EURONEXT"`` or ``"US_EQUITIES"``."""

    label_nl: str
    """Operator-facing Dutch label rendered in the settings page."""

    timezone: str
    """IANA timezone name; APScheduler applies DST automatically."""

    open_hour: int
    open_minute: int
    close_hour: int
    close_minute: int

    index_codes: tuple[str, ...]
    """Locked index codes from ``universe_registry.LOCKED_INDEX_CODES``
    that map to this session."""


# Locked-session catalog. Adding a new session here makes it available
# to the scheduler automatically; the worker re-derives its job list at
# startup from the operator's selected index codes.
_LOCKED_MARKET_SESSIONS: tuple[MarketSession, ...] = (
    MarketSession(
        code="EURONEXT",
        label_nl="Euronext — Brussel, Amsterdam, Parijs",
        timezone="Europe/Brussels",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("BEL20", "AEX", "CAC40"),
    ),
    MarketSession(
        code="XETRA",
        label_nl="Deutsche Börse Xetra (Frankfurt)",
        timezone="Europe/Berlin",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("DAX40",),
    ),
    MarketSession(
        code="LSE",
        label_nl="London Stock Exchange",
        timezone="Europe/London",
        open_hour=8,
        open_minute=0,
        close_hour=16,
        close_minute=30,
        index_codes=("FTSE100",),
    ),
    MarketSession(
        code="BORSA_ITALIANA",
        label_nl="Borsa Italiana (Milaan)",
        timezone="Europe/Rome",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("FTSEMIB",),
    ),
    MarketSession(
        code="BME",
        label_nl="Bolsa de Madrid",
        timezone="Europe/Madrid",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("IBEX35",),
    ),
    MarketSession(
        code="NASDAQ_OMX",
        label_nl="Nasdaq Stockholm (Nordic 30)",
        timezone="Europe/Stockholm",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("NORDIC30",),
    ),
    MarketSession(
        code="SIX",
        label_nl="SIX Swiss Exchange (Zürich)",
        timezone="Europe/Zurich",
        open_hour=9,
        open_minute=0,
        close_hour=17,
        close_minute=30,
        index_codes=("SLI",),
    ),
    MarketSession(
        code="US_EQUITIES",
        label_nl="NYSE & Nasdaq (VS)",
        timezone="America/New_York",
        open_hour=9,
        open_minute=30,
        close_hour=16,
        close_minute=0,
        index_codes=("SP100", "NASDAQ100", "RUSSELL1000", "RUSSELL2000"),
    ),
)


# Close-digest buffer minutes. The digest fire runs this many minutes
# AFTER the official close so end-of-day data has time to settle in
# the EODHD feed / IBKR snapshot before we summarise.
CLOSE_DIGEST_BUFFER_MINUTES = 15

# Open-check buffer minutes. The open-check fire runs this many minutes
# AFTER the official open so the first-print quotes have time to
# stabilise.
OPEN_CHECK_BUFFER_MINUTES = 5


def locked_market_sessions() -> tuple[MarketSession, ...]:
    """Return the immutable locked-session catalog."""

    return _LOCKED_MARKET_SESSIONS


def resolve_active_market_sessions(
    selected_index_codes: Iterable[str],
) -> tuple[MarketSession, ...]:
    """Return the unique :class:`MarketSession`s that contain at least
    one of the operator's selected index codes.

    Order matches the locked catalog so the UI list is stable. Unknown
    codes are silently ignored (they're rejected at the
    ``/settings/universe-scan`` boundary, so they cannot reach here
    after the API has validated the operator's selection).
    """

    selected = {code.upper().strip() for code in selected_index_codes if code}
    if not selected:
        return ()
    return tuple(
        session
        for session in _LOCKED_MARKET_SESSIONS
        if any(code in selected for code in session.index_codes)
    )


def close_digest_minute(session: MarketSession) -> tuple[int, int]:
    """Cron (hour, minute) for the close-digest fire in the session's
    own timezone. Adds the ``CLOSE_DIGEST_BUFFER_MINUTES`` buffer and
    rolls forward into the next hour when minutes overflow 60."""

    total = session.close_minute + CLOSE_DIGEST_BUFFER_MINUTES
    overflow_hours, minute = divmod(total, 60)
    hour = (session.close_hour + overflow_hours) % 24
    return hour, minute


def open_check_minute(session: MarketSession) -> tuple[int, int]:
    """Cron (hour, minute) for the open-check fire in the session's
    own timezone, with ``OPEN_CHECK_BUFFER_MINUTES`` buffer."""

    total = session.open_minute + OPEN_CHECK_BUFFER_MINUTES
    overflow_hours, minute = divmod(total, 60)
    hour = (session.open_hour + overflow_hours) % 24
    return hour, minute


__all__ = [
    "CLOSE_DIGEST_BUFFER_MINUTES",
    "OPEN_CHECK_BUFFER_MINUTES",
    "MarketSession",
    "close_digest_minute",
    "locked_market_sessions",
    "open_check_minute",
    "resolve_active_market_sessions",
]
