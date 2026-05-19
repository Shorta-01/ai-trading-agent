from datetime import datetime
from decimal import Decimal

import pytest

from portfolio_outlook_domain.quantitative_research import (
    ActionProbabilityEstimate,
    HistoricalBarSize,
    HistoricalDataRequestSpec,
    HistoricalDataType,
    HistoricalMarketBar,
    MarketDataProvider,
    RegularTradingHoursMode,
    get_quantitative_research_help_texts,
)
from portfolio_outlook_domain.research_suggestions import SuggestionAction


def test_historical_data_request_spec_validations() -> None:
    with pytest.raises(ValueError):
        HistoricalDataRequestSpec(
            request_id="",
            provider=MarketDataProvider.IBKR,
            asset_symbol="AAPL",
            currency="USD",
            data_type=HistoricalDataType.TRADES,
            bar_size=HistoricalBarSize.ONE_DAY,
            regular_trading_hours_mode=RegularTradingHoursMode.REGULAR_TRADING_HOURS_ONLY,
            requested_at=datetime(2026, 1, 1),
            reason_nl="test",
        )


def test_historical_market_bar_rejects_float_and_negative_trade_count() -> None:
    with pytest.raises(ValueError):
        HistoricalMarketBar(
            bar_id="b1",
            provider=MarketDataProvider.IBKR,
            asset_symbol="AAPL",
            currency="USD",
            bar_start_at=datetime(2026, 1, 1),
            bar_end_at=datetime(2026, 1, 2),
            open_price=1.2,
            high_price=Decimal("2"),
            low_price=Decimal("1"),
            close_price=Decimal("1.5"),
            trade_count=1,
            data_type=HistoricalDataType.TRADES,
            bar_size=HistoricalBarSize.ONE_DAY,
            regular_trading_hours_mode=RegularTradingHoursMode.REGULAR_TRADING_HOURS_ONLY,
            received_at=datetime(2026, 1, 2),
        )

    with pytest.raises(ValueError):
        HistoricalMarketBar(
            bar_id="b1",
            provider=MarketDataProvider.IBKR,
            asset_symbol="AAPL",
            currency="USD",
            bar_start_at=datetime(2026, 1, 1),
            bar_end_at=datetime(2026, 1, 2),
            open_price=Decimal("1.2"),
            high_price=Decimal("2"),
            low_price=Decimal("1"),
            close_price=Decimal("1.5"),
            trade_count=-1,
            data_type=HistoricalDataType.TRADES,
            bar_size=HistoricalBarSize.ONE_DAY,
            regular_trading_hours_mode=RegularTradingHoursMode.REGULAR_TRADING_HOURS_ONLY,
            received_at=datetime(2026, 1, 2),
        )


def test_action_probability_rejects_float_and_has_help_texts() -> None:
    with pytest.raises(ValueError):
        ActionProbabilityEstimate(
            action=SuggestionAction.HOUDEN,
            probability_score=1.2,
            reason_nl="uitleg",
        )

    assert get_quantitative_research_help_texts()
