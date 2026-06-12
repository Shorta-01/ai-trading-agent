"""Tests for the profit-harvest orchestrator (V1.2 §M)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    DECISION_SKIP_CONFIDENCE,
    DECISION_SKIP_EARNINGS,
    DECISION_SKIP_MACRO,
    DECISION_SKIP_RISK_UNIVERSE,
    DECISION_SKIP_SECTOR,
    DECISION_SKIP_SIZING,
    DECISION_SUGGEST,
    HistoricalBar,
    NewsItem,
    OrchestratorInputs,
    SectorAllocation,
    TobSecurityClass,
    evaluate_profit_harvest_candidate,
)

# ---- fixture builders ------------------------------------------------


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
    """A series with deterministic moderate-vol noise. Annual vol ~25 %."""

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


def _make_inputs(
    *,
    ticker: str = "AAPL",
    instrument_name: str = "Apple Inc.",
    sector: str | None = "technology",
    market_cap_eur: Decimal | None = Decimal("3000000000000"),
    security_class: TobSecurityClass = TobSecurityClass.STANDARD_STOCK,
    candidate_bars: tuple[HistoricalBar, ...] | None = None,
    current_price: Decimal = Decimal("100"),
    median_forecast_price: Decimal = Decimal("115"),
    annual_volatility_pct: Decimal = Decimal("20"),
    horizon_days: int = 126,
    confidence_pct: Decimal = Decimal("85"),
    vix_level: Decimal | None = Decimal("15"),
    index_bars: tuple[HistoricalBar, ...] | None = None,
    existing_sector_allocations: tuple[SectorAllocation, ...] = (),
    target_net_pct: Decimal = Decimal("4"),
    confidence_threshold_pct: Decimal = Decimal("70"),
    min_position_eur: Decimal = Decimal("25000"),
    max_position_eur: Decimal = Decimal("100000"),
    total_budget_eur: Decimal = Decimal("1000000"),
    min_market_cap_eur: Decimal = Decimal("5000000000"),
    max_annual_volatility_pct: Decimal = Decimal("30"),
    max_sector_pct: Decimal = Decimal("25"),
    today: date = date(2025, 4, 15),
    next_earnings_date: date | None = None,
    candidate_news_items: tuple[NewsItem, ...] = (),
    news_buy_bias_max_boost_pct: Decimal = Decimal("5"),
) -> OrchestratorInputs:
    if candidate_bars is None:
        candidate_bars = _moderate_vol_bars(120)
    if index_bars is None:
        index_bars = _trending_up_bars(250)
    return OrchestratorInputs(
        ticker=ticker,
        instrument_name=instrument_name,
        sector=sector,
        market_cap_eur=market_cap_eur,
        security_class=security_class,
        candidate_bars=candidate_bars,
        current_price=current_price,
        median_forecast_price=median_forecast_price,
        annual_volatility_pct=annual_volatility_pct,
        horizon_days=horizon_days,
        confidence_pct=confidence_pct,
        vix_level=vix_level,
        index_bars=index_bars,
        existing_sector_allocations=existing_sector_allocations,
        today=today,
        next_earnings_date=next_earnings_date,
        candidate_news_items=candidate_news_items,
        news_buy_bias_max_boost_pct=news_buy_bias_max_boost_pct,
        target_net_pct=target_net_pct,
        confidence_threshold_pct=confidence_threshold_pct,
        min_position_eur=min_position_eur,
        max_position_eur=max_position_eur,
        total_budget_eur=total_budget_eur,
        min_market_cap_eur=min_market_cap_eur,
        max_annual_volatility_pct=max_annual_volatility_pct,
        max_sector_pct=max_sector_pct,
    )


# ---- happy path ------------------------------------------------------


def test_blue_chip_candidate_suggests() -> None:
    result = evaluate_profit_harvest_candidate(_make_inputs())
    assert result.decision == DECISION_SUGGEST
    assert result.blocking_reason is None
    # Every gate diagnostic populated.
    assert result.macro is not None and result.macro.favorable
    assert result.risk_universe is not None and result.risk_universe.allowed
    assert result.confidence is not None and result.confidence.allowed
    assert result.proposed_position_eur is not None
    assert result.proposed_position_eur > Decimal("0")
    assert result.sector_concentration is not None and result.sector_concentration.allowed
    assert result.pair_build is not None and result.pair_build.allowed
    # Order pair has the gross uplift.
    assert result.pair_build.pair is not None
    assert result.pair_build.pair.take_profit_sell_price == Decimal("104.7300")


def test_suggest_carries_intended_position_through_to_pair() -> None:
    result = evaluate_profit_harvest_candidate(
        _make_inputs(confidence_pct=Decimal("100"))
    )
    assert result.decision == DECISION_SUGGEST
    assert result.proposed_position_eur == Decimal("100000")
    # At entry €100, position €100k → 996 shares (€100 × 1.0035 = €100.35
    # per share inclusive of TOB; 100000 / 100.35 = 996.51 → 996).
    assert result.pair_build is not None and result.pair_build.pair is not None
    assert result.pair_build.pair.qty == 996


# ---- skip-at-macro --------------------------------------------------


def test_high_vix_short_circuits_at_macro() -> None:
    result = evaluate_profit_harvest_candidate(
        _make_inputs(vix_level=Decimal("40"))
    )
    assert result.decision == DECISION_SKIP_MACRO
    assert result.blocking_reason == "macro_vix_too_high"
    # Everything after macro must be None.
    assert result.risk_universe is None
    assert result.confidence is None
    assert result.proposed_position_eur is None
    assert result.sector_concentration is None
    assert result.pair_build is None


def test_bear_market_short_circuits_at_macro() -> None:
    bear_bars = tuple(
        HistoricalBar(
            bar_date=date(2025, 1, 1) + timedelta(days=i),
            close_price=Decimal(repr(round(200.0 - i * 0.5, 4))),
        )
        for i in range(250)
    )
    result = evaluate_profit_harvest_candidate(_make_inputs(index_bars=bear_bars))
    assert result.decision == DECISION_SKIP_MACRO


# ---- skip-at-risk-universe ------------------------------------------


def test_leveraged_etf_short_circuits_at_risk_universe() -> None:
    result = evaluate_profit_harvest_candidate(
        _make_inputs(ticker="TQQQ", instrument_name="ProShares UltraPro QQQ")
    )
    assert result.decision == DECISION_SKIP_RISK_UNIVERSE
    # Macro is populated (it ran), risk_universe is populated (where
    # we stopped), confidence onwards is None.
    assert result.macro is not None
    assert result.risk_universe is not None and not result.risk_universe.allowed
    assert result.confidence is None
    assert result.pair_build is None


def test_small_cap_short_circuits_at_risk_universe() -> None:
    result = evaluate_profit_harvest_candidate(
        _make_inputs(market_cap_eur=Decimal("1000000000"))  # 1 B < 5 B floor
    )
    assert result.decision == DECISION_SKIP_RISK_UNIVERSE


# ---- skip-at-confidence ---------------------------------------------


def test_bullish_news_lifts_position_size() -> None:
    # Compare same candidate with and without bullish news. With
    # news flow the boosted confidence pushes the proposed position
    # higher under conviction-weighted sizing.
    base = evaluate_profit_harvest_candidate(_make_inputs())
    boosted = evaluate_profit_harvest_candidate(
        _make_inputs(
            candidate_news_items=(
                NewsItem(title="Morgan Stanley analyst upgrade"),
                NewsItem(title="Dividend hike announced"),
            )
        )
    )
    assert base.decision == DECISION_SUGGEST
    assert boosted.decision == DECISION_SUGGEST
    assert base.proposed_position_eur is not None
    assert boosted.proposed_position_eur is not None
    assert boosted.proposed_position_eur > base.proposed_position_eur
    assert boosted.news_sentiment is not None
    assert boosted.news_sentiment.buy_bias > Decimal("0")
    assert boosted.boosted_confidence_pct is not None
    assert boosted.boosted_confidence_pct > base.boosted_confidence_pct  # type: ignore[operator]


def test_zero_news_boost_setting_disables_lift() -> None:
    # Setting max_boost = 0 means even bullish news doesn't change
    # the position size.
    base = evaluate_profit_harvest_candidate(
        _make_inputs(news_buy_bias_max_boost_pct=Decimal("0"))
    )
    boosted = evaluate_profit_harvest_candidate(
        _make_inputs(
            candidate_news_items=(NewsItem(title="Analyst upgrade for stock"),),
            news_buy_bias_max_boost_pct=Decimal("0"),
        )
    )
    assert base.proposed_position_eur == boosted.proposed_position_eur


def test_neutral_news_does_not_boost() -> None:
    base = evaluate_profit_harvest_candidate(_make_inputs())
    neutral = evaluate_profit_harvest_candidate(
        _make_inputs(
            candidate_news_items=(
                NewsItem(title="Quarterly 10-Q filed with SEC"),
            )
        )
    )
    assert base.proposed_position_eur == neutral.proposed_position_eur


def test_earnings_window_short_circuits_at_earnings() -> None:
    # Earnings 3 days out → blocked at the earnings gate.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(next_earnings_date=date(2025, 4, 18))
    )
    assert result.decision == DECISION_SKIP_EARNINGS
    assert result.macro is not None
    assert result.risk_universe is not None and result.risk_universe.allowed
    assert result.earnings is not None and not result.earnings.allowed
    assert result.earnings.days_to_earnings == 3
    # Everything after earnings is None.
    assert result.confidence is None
    assert result.pair_build is None


def test_earnings_safely_in_future_passes() -> None:
    result = evaluate_profit_harvest_candidate(
        _make_inputs(next_earnings_date=date(2025, 6, 1))
    )
    assert result.decision == DECISION_SUGGEST
    assert result.earnings is not None and result.earnings.allowed


def test_missing_earnings_date_passes() -> None:
    # Missing earnings data is allowed (doctrine choice).
    result = evaluate_profit_harvest_candidate(
        _make_inputs(next_earnings_date=None)
    )
    assert result.decision == DECISION_SUGGEST


def test_low_p_hit_short_circuits_at_confidence() -> None:
    # V1.2 §P running-max upgrade: even a mildly bearish median still
    # gives meaningful hit probability over a 6-month horizon with
    # 20 % vol. To produce a *clear* skip we need a low-vol forecast
    # whose median sits well below the target.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(
            median_forecast_price=Decimal("90"),  # 10 % below current
            annual_volatility_pct=Decimal("5"),  # low vol
            horizon_days=63,  # 3 months
        )
    )
    assert result.decision == DECISION_SKIP_CONFIDENCE
    assert result.macro is not None
    assert result.risk_universe is not None and result.risk_universe.allowed
    assert result.confidence is not None and not result.confidence.allowed
    assert result.proposed_position_eur is None


# ---- skip-at-sizing -------------------------------------------------


def test_confidence_below_floor_short_circuits_at_sizing() -> None:
    # The confidence-gate uses the lognormal P; the orchestrator's
    # sizing input is a separate `confidence_pct` reading (the
    # predictor's calibrated confidence). The two can diverge: the
    # gate may pass on math while the calibrated reading is below
    # the threshold.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(
            confidence_pct=Decimal("60"),  # below 70 % threshold
        )
    )
    assert result.decision == DECISION_SKIP_SIZING
    assert result.proposed_position_eur == Decimal("0")


# ---- skip-at-sector -------------------------------------------------


def test_sector_at_cap_short_circuits() -> None:
    # Tech already at 23 %; €25 000 minimum position would push to
    # 23 % + 2.5 % = 25.5 % > 25 % cap.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(
            existing_sector_allocations=(
                SectorAllocation(sector="technology", current_eur=Decimal("230000")),
            ),
            confidence_pct=Decimal("70"),  # min position size
        )
    )
    assert result.decision == DECISION_SKIP_SECTOR
    assert result.sector_concentration is not None
    assert not result.sector_concentration.allowed
    assert result.pair_build is None


def test_different_sector_does_not_block() -> None:
    # Lots of healthcare, tech is empty — tech candidate passes.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(
            existing_sector_allocations=(
                SectorAllocation(sector="healthcare", current_eur=Decimal("240000")),
            ),
            sector="technology",
        )
    )
    assert result.decision == DECISION_SUGGEST


# ---- pipeline ordering ----------------------------------------------


def test_macro_runs_before_risk_universe() -> None:
    # Both fail (high VIX + leveraged ticker) — macro wins because
    # it runs first.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(
            vix_level=Decimal("40"),
            ticker="TQQQ",
            instrument_name="ProShares UltraPro QQQ",
        )
    )
    assert result.decision == DECISION_SKIP_MACRO


def test_risk_universe_runs_before_confidence() -> None:
    # Risk-universe fails (small cap), confidence would also fail
    # (forecast below target) — risk-universe wins.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(
            market_cap_eur=Decimal("1000000000"),
            median_forecast_price=Decimal("90"),
        )
    )
    assert result.decision == DECISION_SKIP_RISK_UNIVERSE


def test_sector_runs_after_sizing() -> None:
    # Sector check must see the actual sized position, not the user's
    # cap. With 70 % confidence size = €25 000; with 100 % conf size =
    # €100 000. Same existing 22 % tech allocation: at min size the
    # 22 % + 2.5 % = 24.5 % is under cap; at max size 22 % + 10 % =
    # 32 % > cap. Demonstrates sizing happens before sector check.
    accept = evaluate_profit_harvest_candidate(
        _make_inputs(
            existing_sector_allocations=(
                SectorAllocation(sector="technology", current_eur=Decimal("220000")),
            ),
            confidence_pct=Decimal("70"),
        )
    )
    block = evaluate_profit_harvest_candidate(
        _make_inputs(
            existing_sector_allocations=(
                SectorAllocation(sector="technology", current_eur=Decimal("220000")),
            ),
            confidence_pct=Decimal("100"),
        )
    )
    assert accept.decision == DECISION_SUGGEST
    assert block.decision == DECISION_SKIP_SECTOR


# ---- diagnostics preserved on partial pipeline ----------------------


def test_diagnostics_preserved_through_pipeline_on_success() -> None:
    result = evaluate_profit_harvest_candidate(_make_inputs())
    assert result.macro is not None
    assert result.risk_universe is not None
    assert result.risk_universe.annualized_volatility_pct is not None
    assert result.confidence is not None
    assert result.confidence.p_target_hit_pct > Decimal("0")
    assert result.sector_concentration is not None
    assert result.sector_concentration.projected_sector_pct > Decimal("0")
    assert result.pair_build is not None
    assert result.pair_build.pair is not None
    assert result.pair_build.pair.qty > 0


def test_diagnostics_preserved_on_skip_carry_what_we_know() -> None:
    # Skip at confidence — macro and risk_universe should have been
    # computed and surfaced. Uses the same low-vol bearish forecast
    # as `test_low_p_hit_short_circuits_at_confidence` so the skip
    # actually fires under the V1.2 §P running-max math.
    result = evaluate_profit_harvest_candidate(
        _make_inputs(
            median_forecast_price=Decimal("90"),
            annual_volatility_pct=Decimal("5"),
            horizon_days=63,
        )
    )
    assert result.decision == DECISION_SKIP_CONFIDENCE
    assert result.macro is not None
    assert result.macro.favorable
    assert result.risk_universe is not None
    assert result.risk_universe.allowed
    assert result.confidence is not None
    assert not result.confidence.allowed
    # Confidence still has its diagnostics.
    assert result.confidence.target_price == Decimal("104.7300")
