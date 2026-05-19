from datetime import UTC, date, datetime

import pytest
from pydantic import ValidationError

from portfolio_outlook_domain.market_calendar import (
    ExchangeCode,
    MarketCalendarDay,
    MarketCalendarDayType,
    MarketSessionStatus,
    MarketSessionType,
    MarketStatusAssessment,
    MarketStatusFreshness,
    MarketVenue,
    TradabilityStatus,
    TradingSessionWindow,
    default_market_venue_catalog,
    evaluate_tradability,
    get_market_calendar_help_texts,
)


def _session(session_type: MarketSessionType = MarketSessionType.REGULAR) -> TradingSessionWindow:
    return TradingSessionWindow(
        session_type=session_type,
        status=MarketSessionStatus.OPEN,
        starts_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
        ends_at=datetime(2026, 1, 2, 17, 0, tzinfo=UTC),
        timezone="Europe/Brussels",
        allows_market_orders=True,
        allows_limit_orders=True,
        liquidity_warning_nl="Lage liquiditeit."
        if session_type != MarketSessionType.REGULAR
        else None,
        explanation_nl="Testsessie.",
    )


def test_market_venue_requires_non_empty_fields() -> None:
    with pytest.raises(ValidationError):
        MarketVenue(
            venue_id="",
            exchange_code=ExchangeCode.NASDAQ,
            display_name="Nasdaq",
            region="united_states",
            timezone="America/New_York",
            venue_type="primary_exchange",
            explanation_nl="u",
        )

    with pytest.raises(ValidationError):
        MarketVenue(
            venue_id="nasdaq",
            exchange_code=ExchangeCode.NASDAQ,
            display_name="Nasdaq",
            region="united_states",
            timezone="",
            venue_type="primary_exchange",
            explanation_nl="u",
        )


def test_trading_session_window_validation() -> None:
    with pytest.raises(ValidationError):
        TradingSessionWindow(
            session_type=MarketSessionType.REGULAR,
            status=MarketSessionStatus.OPEN,
            starts_at=datetime(2026, 1, 2, 17, 0, tzinfo=UTC),
            ends_at=datetime(2026, 1, 2, 9, 0, tzinfo=UTC),
            timezone="Europe/Brussels",
            allows_market_orders=True,
            allows_limit_orders=True,
            explanation_nl="x",
        )

    with pytest.raises(ValidationError):
        TradingSessionWindow(
            session_type=MarketSessionType.PRE_MARKET,
            status=MarketSessionStatus.OPEN,
            starts_at=datetime(2026, 1, 2, 7, 0, tzinfo=UTC),
            ends_at=datetime(2026, 1, 2, 8, 0, tzinfo=UTC),
            timezone="Europe/Brussels",
            allows_market_orders=False,
            allows_limit_orders=True,
            explanation_nl="Voorbeurs",
        )


def test_market_calendar_day_and_status_assessment() -> None:
    day = MarketCalendarDay(
        venue_id="euronext_brussels",
        trading_date=date(2026, 1, 2),
        day_type=MarketCalendarDayType.FULL_TRADING_DAY,
        sessions=(_session(),),
        explanation_nl="Volledige handelsdag.",
    )
    assert day.sessions

    closed_day = MarketCalendarDay(
        venue_id="euronext_brussels",
        trading_date=date(2026, 1, 3),
        day_type=MarketCalendarDayType.HOLIDAY_CLOSED,
        sessions=(),
        explanation_nl="Gesloten dag.",
    )
    assert closed_day.day_type == MarketCalendarDayType.HOLIDAY_CLOSED

    for status, freshness in [
        (MarketSessionStatus.UNKNOWN, MarketStatusFreshness.FRESH),
        (MarketSessionStatus.CLOSED, MarketStatusFreshness.FRESH),
        (MarketSessionStatus.HALTED, MarketStatusFreshness.FRESH),
        (MarketSessionStatus.OPEN, MarketStatusFreshness.STALE),
        (MarketSessionStatus.OPEN, MarketStatusFreshness.MISSING),
    ]:
        assessment = MarketStatusAssessment(
            assessment_id="a1",
            venue_id="nasdaq",
            exchange_code=ExchangeCode.NASDAQ,
            checked_at=datetime(2026, 1, 2, 12, 0, tzinfo=UTC),
            as_of_time=datetime(2026, 1, 2, 11, 59, tzinfo=UTC),
            current_session_type=MarketSessionType.REGULAR,
            current_session_status=status,
            tradability_status=TradabilityStatus.BLOCKED,
            freshness_status=freshness,
            blocks_suggestions=True,
            blocks_orders=True,
            reason_nl="Geblokkeerd",
            help_nl="Niet uitvoerbaar",
        )
        assert assessment.blocks_orders


def test_evaluate_tradability_and_helptexts() -> None:
    assert (
        evaluate_tradability(
            current_session_status=MarketSessionStatus.OPEN,
            current_session_type=MarketSessionType.REGULAR,
            freshness_status=MarketStatusFreshness.FRESH,
            allows_market_orders=True,
            allows_limit_orders=False,
        )
        == TradabilityStatus.TRADABLE
    )
    assert (
        evaluate_tradability(
            current_session_status=MarketSessionStatus.OPEN,
            current_session_type=MarketSessionType.PRE_MARKET,
            freshness_status=MarketStatusFreshness.FRESH,
            allows_market_orders=False,
            allows_limit_orders=True,
        )
        == TradabilityStatus.TRADABLE_WITH_WARNING
    )
    assert (
        evaluate_tradability(
            current_session_status=MarketSessionStatus.OPEN,
            current_session_type=MarketSessionType.POST_MARKET,
            freshness_status=MarketStatusFreshness.FRESH,
            allows_market_orders=False,
            allows_limit_orders=True,
        )
        == TradabilityStatus.TRADABLE_WITH_WARNING
    )
    assert (
        evaluate_tradability(
            current_session_status=MarketSessionStatus.AUCTION,
            current_session_type=MarketSessionType.OPENING_AUCTION,
            freshness_status=MarketStatusFreshness.FRESH,
            allows_market_orders=False,
            allows_limit_orders=False,
        )
        != TradabilityStatus.TRADABLE
    )
    assert (
        evaluate_tradability(
            current_session_status=MarketSessionStatus.UNKNOWN,
            current_session_type=MarketSessionType.UNKNOWN,
            freshness_status=MarketStatusFreshness.FRESH,
            allows_market_orders=True,
            allows_limit_orders=True,
        )
        == TradabilityStatus.UNKNOWN
    )
    assert evaluate_tradability(
        current_session_status=MarketSessionStatus.OPEN,
        current_session_type=MarketSessionType.REGULAR,
        freshness_status=MarketStatusFreshness.FRESH,
        allows_market_orders=True,
        allows_limit_orders=False,
    ) == evaluate_tradability(
        current_session_status=MarketSessionStatus.OPEN,
        current_session_type=MarketSessionType.REGULAR,
        freshness_status=MarketStatusFreshness.FRESH,
        allows_market_orders=True,
        allows_limit_orders=False,
    )

    help_texts = get_market_calendar_help_texts()
    assert all(item.label_nl and item.help_nl for item in help_texts)

    catalog = default_market_venue_catalog()
    ids = {item.venue_id for item in catalog}
    assert "euronext_brussels" in ids
    assert "nasdaq" in ids
