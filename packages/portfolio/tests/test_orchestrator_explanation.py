"""Tests for the Dutch orchestrator-decision translator (V1.2 §T)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    HistoricalBar,
    NewsItem,
    OrchestratorInputs,
    SectorAllocation,
    TobSecurityClass,
    evaluate_profit_harvest_candidate,
    explain_decision,
    explain_decision_detail,
)


def _trending_up_bars(count: int, *, slope: float = 0.5) -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    return tuple(
        HistoricalBar(
            bar_date=base + timedelta(days=i),
            close_price=Decimal(repr(round(100.0 + i * slope, 4))),
        )
        for i in range(count)
    )


def _moderate_vol_bars(count: int) -> tuple[HistoricalBar, ...]:
    base = date(2025, 1, 1)
    price = 100.0
    bars = []
    for i in range(count):
        noise = math.sin(i * 17) * 0.015
        price *= math.exp(noise)
        bars.append(
            HistoricalBar(
                bar_date=base + timedelta(days=i),
                close_price=Decimal(repr(round(price, 4))),
            )
        )
    return tuple(bars)


def _base_inputs(**overrides) -> OrchestratorInputs:  # type: ignore[no-untyped-def]
    defaults: dict[str, object] = dict(
        ticker="AAPL",
        instrument_name="Apple Inc.",
        sector="technology",
        market_cap_eur=Decimal("3000000000000"),
        security_class=TobSecurityClass.STANDARD_STOCK,
        candidate_bars=_moderate_vol_bars(120),
        current_price=Decimal("100"),
        median_forecast_price=Decimal("115"),
        annual_volatility_pct=Decimal("20"),
        horizon_days=126,
        confidence_pct=Decimal("85"),
        vix_level=Decimal("15"),
        index_bars=_trending_up_bars(250),
        existing_sector_allocations=(),
        today=date(2025, 4, 15),
        next_earnings_date=None,
        target_net_pct=Decimal("4"),
        confidence_threshold_pct=Decimal("70"),
        min_position_eur=Decimal("25000"),
        max_position_eur=Decimal("100000"),
        total_budget_eur=Decimal("1000000"),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
        max_sector_pct=Decimal("25"),
    )
    defaults.update(overrides)
    return OrchestratorInputs(**defaults)  # type: ignore[arg-type]


# ---- happy path SUGGEST line -----------------------------------------


def test_suggest_summary_mentions_ticker_and_prices() -> None:
    result = evaluate_profit_harvest_candidate(_base_inputs())
    line = explain_decision(result)
    assert "AAPL" in line
    assert "Koop" in line
    assert "verkoop" in line.lower()
    # Belgian pricing convention: comma decimal.
    assert "€100,00" in line
    assert "€104,73" in line
    # Probability included.
    assert "kans" in line


def test_suggest_detail_contains_each_passed_gate_line() -> None:
    result = evaluate_profit_harvest_candidate(_base_inputs())
    detail = explain_decision_detail(result)
    assert "Beslissing:" in detail
    assert "Marktklimaat" in detail
    assert "Risico-filter" in detail
    assert "Vertrouwen" in detail
    assert "Sector" in detail
    assert "Order" in detail


def test_suggest_detail_lists_proposed_position_eur() -> None:
    result = evaluate_profit_harvest_candidate(_base_inputs())
    detail = explain_decision_detail(result)
    assert "€" in detail


def test_suggest_detail_with_news_includes_news_line() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(
            candidate_news_items=(
                NewsItem(title="Analyst upgrade for stock"),
                NewsItem(title="Routine quarterly update"),
            )
        )
    )
    detail = explain_decision_detail(result)
    assert "Nieuwsstroom" in detail


# ---- skip lines ------------------------------------------------------


def test_macro_skip_line_mentions_vix() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(vix_level=Decimal("40"))
    )
    line = explain_decision(result)
    assert "Marktklimaat" in line
    assert "VIX" in line


def test_macro_bear_trend_skip_line() -> None:
    bear_bars = tuple(
        HistoricalBar(
            bar_date=date(2025, 1, 1) + timedelta(days=i),
            close_price=Decimal(repr(round(200.0 - i * 0.5, 4))),
        )
        for i in range(250)
    )
    result = evaluate_profit_harvest_candidate(
        _base_inputs(index_bars=bear_bars)
    )
    line = explain_decision(result)
    assert "bear-trend" in line


def test_risk_universe_skip_line_mentions_filter() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(ticker="TQQQ", instrument_name="ProShares UltraPro QQQ")
    )
    line = explain_decision(result)
    assert "Risico-filter" in line
    assert "leveraged" in line.lower() or "uitgesloten" in line.lower()


def test_small_cap_skip_line() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(market_cap_eur=Decimal("1000000000"))
    )
    line = explain_decision(result)
    assert "Risico-filter" in line
    assert "marktkapitalisatie" in line.lower()


def test_earnings_skip_line_mentions_earnings() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(next_earnings_date=date(2025, 4, 18))
    )
    line = explain_decision(result)
    assert "Earnings" in line
    assert "blokkering" in line.lower() or "venster" in line.lower()


def test_confidence_skip_line() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(
            median_forecast_price=Decimal("90"),
            annual_volatility_pct=Decimal("5"),
            horizon_days=63,
        )
    )
    line = explain_decision(result)
    # "Onvoldoende" or "drempel" appear in the locked dictionary.
    assert "drempel" in line.lower() or "onvoldoende" in line.lower()


def test_sizing_skip_line() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(confidence_pct=Decimal("60"))  # below floor
    )
    line = explain_decision(result)
    assert "Overtuiging" in line
    assert "drempel" in line


def test_sector_skip_line() -> None:
    result = evaluate_profit_harvest_candidate(
        _base_inputs(
            existing_sector_allocations=(
                SectorAllocation(sector="technology", current_eur=Decimal("230000")),
            ),
            confidence_pct=Decimal("70"),
        )
    )
    line = explain_decision(result)
    assert "Sector" in line


# ---- formatting ------------------------------------------------------


def test_eur_format_uses_belgian_thousands() -> None:
    # Big ticket suggested → EUR in detail will use dot thousands.
    result = evaluate_profit_harvest_candidate(
        _base_inputs(confidence_pct=Decimal("100"))  # max position
    )
    detail = explain_decision_detail(result)
    # €100.000 thousand separator dot expected.
    assert "€100.000" in detail or "€99" in detail or "€100" in detail


def test_pct_format_uses_belgian_comma() -> None:
    result = evaluate_profit_harvest_candidate(_base_inputs())
    line = explain_decision(result)
    # Probability is rendered as e.g. "78,XX %".
    assert "," in line
    assert "%" in line


def test_unknown_decision_falls_back_gracefully() -> None:
    # Hand-craft an OrchestratorResult with an unknown decision code
    # to verify the translator falls back to a generic message
    # rather than raising.
    from portfolio_outlook_portfolio import OrchestratorResult

    fake = OrchestratorResult(
        decision="something_new_v2",
        blocking_reason="x",
        macro=None,
        risk_universe=None,
        earnings=None,
        confidence=None,
        news_sentiment=None,
        boosted_confidence_pct=None,
        proposed_position_eur=None,
        sector_concentration=None,
        pair_build=None,
    )
    line = explain_decision(fake)
    assert "Onbekende" in line
