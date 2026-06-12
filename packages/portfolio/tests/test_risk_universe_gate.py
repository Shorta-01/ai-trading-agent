"""Tests for the risk-universe gate (V1.2 §G)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

import pytest

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_ABOVE_MAX_VOLATILITY,
    BLOCKING_REASON_BELOW_MIN_MARKET_CAP,
    BLOCKING_REASON_LEVERAGED_OR_INVERSE,
    BLOCKING_REASON_UNKNOWN_MARKET_CAP,
    RISK_UNIVERSE_BLOCKING_REASON_INSUFFICIENT_BARS,
    HistoricalBar,
    RiskUniverseInputs,
    annualized_volatility_pct,
    evaluate_risk_universe_gate,
    is_leveraged_or_inverse,
)

# ---- bar fixture builders --------------------------------------------


def _flat_bars(count: int, *, start_price: Decimal = Decimal("100.00")) -> list[HistoricalBar]:
    """A perfectly flat series — zero volatility."""

    base = date(2025, 1, 1)
    return [
        HistoricalBar(bar_date=base + timedelta(days=i), close_price=start_price)
        for i in range(count)
    ]


def _gbm_bars(
    count: int, *, drift_daily: float = 0.0, vol_daily: float = 0.01, seed: int = 0
) -> list[HistoricalBar]:
    """Deterministic GBM-like series: drift + sinusoidal-noise vol."""

    base = date(2025, 1, 1)
    price = 100.0
    bars: list[HistoricalBar] = []
    for i in range(count):
        # Deterministic pseudo-noise so tests are reproducible without
        # touching random.
        noise = math.sin(i * 17 + seed) * vol_daily
        price *= math.exp(drift_daily + noise)
        bars.append(
            HistoricalBar(
                bar_date=base + timedelta(days=i),
                close_price=Decimal(repr(round(price, 4))),
            )
        )
    return bars


# ---- is_leveraged_or_inverse -----------------------------------------


def test_known_3x_ticker_is_blocked() -> None:
    assert is_leveraged_or_inverse("TQQQ", "ProShares UltraPro QQQ")


def test_known_inverse_ticker_is_blocked() -> None:
    assert is_leveraged_or_inverse("SQQQ", "ProShares UltraPro Short QQQ")


def test_ticker_case_insensitive() -> None:
    assert is_leveraged_or_inverse("tqqq", "doesn't matter")


def test_name_with_2x_blocked() -> None:
    assert is_leveraged_or_inverse("XYZ", "Acme Bull 2x ETF")


def test_name_with_3x_blocked() -> None:
    assert is_leveraged_or_inverse("XYZ", "Direxion Daily Energy Bull 3X")


def test_name_with_leveraged_blocked() -> None:
    assert is_leveraged_or_inverse("XYZ", "Vanguard Leveraged Growth Fund")


def test_name_with_inverse_blocked() -> None:
    assert is_leveraged_or_inverse("XYZ", "iShares Inverse Treasury")


def test_name_with_ultra_blocked() -> None:
    assert is_leveraged_or_inverse("XYZ", "ProShares Ultra Real Estate")


def test_plain_stock_not_blocked() -> None:
    assert not is_leveraged_or_inverse("AAPL", "Apple Inc.")
    assert not is_leveraged_or_inverse("MSFT", "Microsoft Corporation")
    assert not is_leveraged_or_inverse("VWRL", "Vanguard FTSE All-World UCITS ETF")


def test_word_boundary_avoids_substring_false_positives() -> None:
    # "Ultratech" should NOT match because the regex uses \b.
    assert not is_leveraged_or_inverse("UTEK", "Ultratech Inc.")
    # "Inversion" too — no word-boundary match for "inverse".
    assert not is_leveraged_or_inverse("INVR", "Inversion Holdings")


# ---- annualized_volatility_pct ---------------------------------------


def test_flat_series_returns_zero_volatility() -> None:
    bars = _flat_bars(100)
    vol = annualized_volatility_pct(bars)
    assert vol == Decimal("0.00")


def test_high_vol_series_returns_high_number() -> None:
    bars = _gbm_bars(252, drift_daily=0.0, vol_daily=0.03)  # ~48% annual
    vol = annualized_volatility_pct(bars)
    assert vol is not None
    assert vol > Decimal("30.00")


def test_too_few_bars_returns_none() -> None:
    assert annualized_volatility_pct(_flat_bars(1)) is None
    assert annualized_volatility_pct(_flat_bars(0)) is None


def test_two_bars_returns_none_because_only_one_log_return() -> None:
    # Sample stdev needs ≥ 2 points; one log return is not enough.
    bars = [
        HistoricalBar(bar_date=date(2025, 1, 1), close_price=Decimal("100")),
        HistoricalBar(bar_date=date(2025, 1, 2), close_price=Decimal("101")),
    ]
    assert annualized_volatility_pct(bars) is None


def test_negative_close_returns_none() -> None:
    bars = [
        HistoricalBar(bar_date=date(2025, 1, 1), close_price=Decimal("100")),
        HistoricalBar(bar_date=date(2025, 1, 2), close_price=Decimal("-1")),
        HistoricalBar(bar_date=date(2025, 1, 3), close_price=Decimal("100")),
    ]
    assert annualized_volatility_pct(bars) is None


# ---- evaluate_risk_universe_gate -------------------------------------


def _inputs(
    *,
    ticker: str = "AAPL",
    name: str = "Apple Inc.",
    market_cap: Decimal | None = Decimal("3000000000000"),
    bars: list[HistoricalBar] | None = None,
) -> RiskUniverseInputs:
    if bars is None:
        bars = _gbm_bars(80, vol_daily=0.01)
    return RiskUniverseInputs(
        ticker=ticker,
        instrument_name=name,
        market_cap_eur=market_cap,
        bars=tuple(bars),
    )


def test_blue_chip_passes_gate() -> None:
    result = evaluate_risk_universe_gate(
        _inputs(),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert result.allowed
    assert result.blocking_reason is None
    assert result.annualized_volatility_pct is not None


def test_leveraged_ticker_blocked_first() -> None:
    result = evaluate_risk_universe_gate(
        _inputs(ticker="TQQQ", name="ProShares UltraPro QQQ"),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_LEVERAGED_OR_INVERSE


def test_unknown_market_cap_blocks() -> None:
    result = evaluate_risk_universe_gate(
        _inputs(market_cap=None),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_UNKNOWN_MARKET_CAP


def test_small_cap_blocks() -> None:
    result = evaluate_risk_universe_gate(
        _inputs(market_cap=Decimal("4000000000")),  # 4 B < 5 B floor
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_BELOW_MIN_MARKET_CAP


def test_insufficient_bars_blocks() -> None:
    result = evaluate_risk_universe_gate(
        _inputs(bars=_flat_bars(30)),  # < default 60
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert not result.allowed
    assert result.blocking_reason == RISK_UNIVERSE_BLOCKING_REASON_INSUFFICIENT_BARS


def test_high_volatility_blocks() -> None:
    # vol_daily=0.05 → ~79% annualised, well above the 30% ceiling.
    result = evaluate_risk_universe_gate(
        _inputs(bars=_gbm_bars(120, vol_daily=0.05)),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert not result.allowed
    assert result.blocking_reason == BLOCKING_REASON_ABOVE_MAX_VOLATILITY
    # Volatility is reported even on block — for the UI explanation.
    assert result.annualized_volatility_pct is not None
    assert result.annualized_volatility_pct > Decimal("30")


def test_volatility_reported_on_pass() -> None:
    result = evaluate_risk_universe_gate(
        _inputs(bars=_gbm_bars(252, vol_daily=0.005)),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert result.allowed
    assert result.annualized_volatility_pct is not None
    assert result.annualized_volatility_pct < Decimal("30")


def test_check_order_leveraged_beats_market_cap() -> None:
    # Even a giant leveraged ETF must be blocked for the leveraged
    # reason, not the market-cap reason.
    result = evaluate_risk_universe_gate(
        _inputs(
            ticker="TQQQ",
            name="ProShares UltraPro QQQ",
            market_cap=Decimal("20000000000"),
        ),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert result.blocking_reason == BLOCKING_REASON_LEVERAGED_OR_INVERSE


def test_check_order_market_cap_beats_volatility() -> None:
    # Small-cap with high vol → blocked for cap, not vol.
    result = evaluate_risk_universe_gate(
        _inputs(
            market_cap=Decimal("1000000000"),
            bars=_gbm_bars(120, vol_daily=0.05),
        ),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
    )
    assert result.blocking_reason == BLOCKING_REASON_BELOW_MIN_MARKET_CAP


def test_float_thresholds_rejected() -> None:
    with pytest.raises(TypeError):
        evaluate_risk_universe_gate(
            _inputs(),
            min_market_cap_eur=5_000_000_000.0,  # type: ignore[arg-type]
            max_annual_volatility_pct=Decimal("30"),
        )
    with pytest.raises(TypeError):
        evaluate_risk_universe_gate(
            _inputs(),
            min_market_cap_eur=Decimal("5000000000"),
            max_annual_volatility_pct=30.0,  # type: ignore[arg-type]
        )


def test_min_bars_threshold_is_configurable() -> None:
    # With min_bars=20 the same input that failed at default 60 passes
    # the bar-count check (and lands on a different verdict path).
    result = evaluate_risk_universe_gate(
        _inputs(bars=_flat_bars(30)),
        min_market_cap_eur=Decimal("5000000000"),
        max_annual_volatility_pct=Decimal("30"),
        min_bars_for_volatility=20,
    )
    # Flat series gives 0% vol → passes the vol ceiling cleanly.
    assert result.allowed
    assert result.annualized_volatility_pct == Decimal("0.00")
