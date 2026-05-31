"""Tests for the locked market-hours catalog used by the scheduler."""

from __future__ import annotations

import pytest

from portfolio_outlook_worker.market_hours import (
    CLOSE_DIGEST_BUFFER_MINUTES,
    OPEN_CHECK_BUFFER_MINUTES,
    close_digest_minute,
    locked_market_sessions,
    open_check_minute,
    resolve_active_market_sessions,
)


def test_locked_catalog_is_non_empty_and_internally_consistent() -> None:
    sessions = locked_market_sessions()
    assert sessions, "Locked catalog must not be empty."
    seen_codes: set[str] = set()
    for session in sessions:
        assert session.code not in seen_codes, (
            f"Duplicate session code: {session.code}"
        )
        seen_codes.add(session.code)
        assert session.timezone, "Timezone must be set"
        assert 0 <= session.open_hour <= 23
        assert 0 <= session.open_minute <= 59
        assert 0 <= session.close_hour <= 23
        assert 0 <= session.close_minute <= 59
        assert session.index_codes, "Session must list at least one index code"


def test_resolve_returns_unique_sessions_in_catalog_order() -> None:
    # User selects BEL20 + AEX + DAX40 — expect 2 sessions back
    # (EURONEXT first, XETRA second; order matches the catalog).
    sessions = resolve_active_market_sessions(("BEL20", "AEX", "DAX40"))
    assert tuple(s.code for s in sessions) == ("EURONEXT", "XETRA")


def test_resolve_silently_skips_unknown_codes() -> None:
    # Empty + unknown codes are ignored; selecting only BEL20 returns
    # just the Euronext session.
    sessions = resolve_active_market_sessions(("BEL20", "", "BOGUS"))
    assert tuple(s.code for s in sessions) == ("EURONEXT",)


def test_resolve_returns_empty_tuple_when_nothing_selected() -> None:
    assert resolve_active_market_sessions(()) == ()
    assert resolve_active_market_sessions(("",)) == ()


def test_resolve_is_case_insensitive() -> None:
    sessions = resolve_active_market_sessions(("bel20", "AEX"))
    assert tuple(s.code for s in sessions) == ("EURONEXT",)


def test_close_digest_minute_adds_buffer() -> None:
    sessions = {s.code: s for s in locked_market_sessions()}
    euronext = sessions["EURONEXT"]
    # Euronext close is 17:30; with the +15min buffer the digest fires
    # at 17:45 in Europe/Brussels.
    assert close_digest_minute(euronext) == (17, 45)


def test_close_digest_minute_rolls_over_the_hour() -> None:
    sessions = {s.code: s for s in locked_market_sessions()}
    us = sessions["US_EQUITIES"]
    # US close is 16:00 NY; +15min buffer = 16:15. (Same hour, no
    # rollover for the locked catalog — but we still verify the
    # arithmetic.)
    assert close_digest_minute(us) == (16, 15)


def test_close_digest_minute_rolls_into_next_hour_when_buffer_overflows() -> None:
    # Build a synthetic session that closes at 23:55; +15min buffer
    # must roll forward to 00:10 the next day.
    from portfolio_outlook_worker.market_hours import MarketSession

    session = MarketSession(
        code="LATE",
        label_nl="Late",
        timezone="UTC",
        open_hour=0,
        open_minute=0,
        close_hour=23,
        close_minute=55,
        index_codes=("X",),
    )
    assert close_digest_minute(session) == (0, 10)


def test_open_check_minute_uses_open_buffer() -> None:
    sessions = {s.code: s for s in locked_market_sessions()}
    us = sessions["US_EQUITIES"]
    # US open is 09:30; +5min buffer = 09:35 NY local.
    assert open_check_minute(us) == (9, 35)


def test_buffer_constants_are_sane() -> None:
    assert CLOSE_DIGEST_BUFFER_MINUTES >= 5
    assert OPEN_CHECK_BUFFER_MINUTES >= 0
    # The open buffer should be small enough that the fire happens
    # while the operator can still react.
    assert OPEN_CHECK_BUFFER_MINUTES < 30


@pytest.mark.parametrize(
    "selection,expected_codes",
    [
        (("BEL20",), ("EURONEXT",)),
        (("AEX", "CAC40"), ("EURONEXT",)),
        (("BEL20", "DAX40", "SP100"), ("EURONEXT", "XETRA", "US_EQUITIES")),
        (("FTSE100",), ("LSE",)),
        (("NASDAQ100",), ("US_EQUITIES",)),
        (("FTSEMIB", "IBEX35"), ("BORSA_ITALIANA", "BME")),
        (("NORDIC30", "SLI"), ("NASDAQ_OMX", "SIX")),
    ],
)
def test_resolve_per_universe_pattern(
    selection: tuple[str, ...], expected_codes: tuple[str, ...]
) -> None:
    sessions = resolve_active_market_sessions(selection)
    assert tuple(s.code for s in sessions) == expected_codes
