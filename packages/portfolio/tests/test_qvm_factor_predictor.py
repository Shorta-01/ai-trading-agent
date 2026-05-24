"""Tests for the deterministic QVM factor predictor (Slice 16)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    BLOCKING_REASON_FLAT_HISTORY,
    BLOCKING_REASON_INSUFFICIENT_HISTORY,
    BLOCKING_REASON_INVALID_CURRENT_PRICE,
    BLOCKING_REASON_INVALID_HORIZON,
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    PREDICTOR_STATUS_BLOCKED,
    PREDICTOR_STATUS_READY,
    QVM_BLOCKING_REASON_INSUFFICIENT_FACTORS,
    QVM_BLOCKING_REASON_INSUFFICIENT_UNIVERSE,
    QVM_BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE,
    QVM_MIN_BARS,
    QVM_MODEL_CODE,
    FundamentalsEntry,
    HistoricalBar,
    PredictorInputs,
    QvmFactorPredictor,
    UniverseFundamentals,
)


def _bars(closes: list[float], start: date = date(2024, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


def _noisy_uptrend(length: int = QVM_MIN_BARS + 30) -> list[float]:
    return [100.0 + 0.05 * i + 0.5 * math.sin(i / 4) for i in range(length)]


def _universe(*entries: FundamentalsEntry) -> UniverseFundamentals:
    return UniverseFundamentals(entries=tuple(entries))


def _entry(
    symbol: str,
    *,
    pe: float | None = 15.0,
    pb: float | None = 2.0,
    ev: float | None = 12.0,
    roic: float | None = 12.0,
    gm: float | None = 40.0,
    r6: float | None = 5.0,
    r12: float | None = 10.0,
    sector: str | None = "Technology",
) -> FundamentalsEntry:
    return FundamentalsEntry(
        symbol=symbol,
        sector=sector,
        pe_ratio=Decimal(str(pe)) if pe is not None else None,
        pb_ratio=Decimal(str(pb)) if pb is not None else None,
        ev_ebitda=Decimal(str(ev)) if ev is not None else None,
        roic_pct=Decimal(str(roic)) if roic is not None else None,
        gross_margin_pct=Decimal(str(gm)) if gm is not None else None,
        return_6m_pct=Decimal(str(r6)) if r6 is not None else None,
        return_12m_pct=Decimal(str(r12)) if r12 is not None else None,
    )


# ---- blocking paths ----------------------------------------------------


def test_blocks_on_invalid_horizon() -> None:
    pred = QvmFactorPredictor(
        universe=_universe(*[_entry(f"S{i}") for i in range(5)]),
        target_symbol="S0",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=0,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_HORIZON


def test_blocks_on_invalid_current_price() -> None:
    pred = QvmFactorPredictor(
        universe=_universe(*[_entry(f"S{i}") for i in range(5)]),
        target_symbol="S0",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("0"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_CURRENT_PRICE


def test_blocks_on_short_history() -> None:
    pred = QvmFactorPredictor(
        universe=_universe(*[_entry(f"S{i}") for i in range(5)]),
        target_symbol="S0",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars([100.0] * 50),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INSUFFICIENT_HISTORY


def test_blocks_on_tiny_universe() -> None:
    pred = QvmFactorPredictor(
        universe=_universe(_entry("S0"), _entry("S1")),
        target_symbol="S0",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == QVM_BLOCKING_REASON_INSUFFICIENT_UNIVERSE


def test_blocks_when_target_symbol_not_in_universe() -> None:
    pred = QvmFactorPredictor(
        universe=_universe(*[_entry(f"S{i}") for i in range(6)]),
        target_symbol="MISSING",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == QVM_BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE


def test_blocks_when_target_has_no_factor_components() -> None:
    target = _entry(
        "S0",
        pe=None,
        pb=None,
        ev=None,
        roic=None,
        gm=None,
        r6=None,
        r12=None,
    )
    rest = [_entry(f"S{i}") for i in range(1, 6)]
    pred = QvmFactorPredictor(
        universe=_universe(target, *rest),
        target_symbol="S0",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == QVM_BLOCKING_REASON_INSUFFICIENT_FACTORS


def test_blocks_on_flat_recent_history() -> None:
    pred = QvmFactorPredictor(
        universe=_universe(*[_entry(f"S{i}") for i in range(6)]),
        target_symbol="S0",
    )
    closes = [100.0 + 0.05 * i for i in range(50)] + [105.0] * QVM_MIN_BARS
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(closes),
            current_price=Decimal("105"),
            horizon_trading_days=21,
        )
    )
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_FLAT_HISTORY


# ---- factor math --------------------------------------------------------


def test_strong_qvm_score_yields_positive_expected_return() -> None:
    # Target stock: cheap (low P/E, P/B, EV/EBITDA), high quality, high
    # momentum. Peers are middle-of-the-road.
    target = _entry(
        "TARGET",
        pe=8.0,
        pb=1.0,
        ev=6.0,
        roic=30.0,
        gm=60.0,
        r6=20.0,
        r12=35.0,
    )
    peers = [
        _entry(f"P{i}", pe=20.0, pb=3.0, ev=18.0, roic=10.0, gm=35.0, r6=2.0, r12=5.0)
        for i in range(10)
    ]
    pred = QvmFactorPredictor(
        universe=_universe(target, *peers),
        target_symbol="TARGET",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=60,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.expected_return_pct > 0
    assert result.direction in {DIRECTION_STRONG_UP, DIRECTION_SLIGHT_UP}


def test_weak_qvm_score_yields_negative_expected_return() -> None:
    target = _entry(
        "TARGET",
        pe=60.0,
        pb=15.0,
        ev=50.0,
        roic=2.0,
        gm=15.0,
        r6=-15.0,
        r12=-25.0,
    )
    peers = [
        _entry(f"P{i}", pe=15.0, pb=2.0, ev=12.0, roic=15.0, gm=45.0, r6=10.0, r12=20.0)
        for i in range(10)
    ]
    pred = QvmFactorPredictor(
        universe=_universe(target, *peers),
        target_symbol="TARGET",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=60,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.expected_return_pct < 0
    assert result.direction in {DIRECTION_STRONG_DOWN, DIRECTION_SLIGHT_DOWN}


def test_target_near_universe_mean_yields_flat() -> None:
    # Every universe member is identical → z-scores are zero for all
    # factors → composite is zero → projection is zero return.
    universe = _universe(*[_entry(f"S{i}") for i in range(10)])
    pred = QvmFactorPredictor(universe=universe, target_symbol="S0")
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=60,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.direction == DIRECTION_FLAT


def test_predictor_uses_only_available_factors() -> None:
    """If quality data is missing for the whole universe the predictor
    must still run on value + momentum alone."""

    target = _entry("TARGET", pe=8.0, pb=1.0, ev=6.0, roic=None, gm=None, r6=15.0, r12=25.0)
    peers = [
        _entry(f"P{i}", pe=20.0, pb=3.0, ev=18.0, roic=None, gm=None, r6=2.0, r12=5.0)
        for i in range(10)
    ]
    pred = QvmFactorPredictor(
        universe=_universe(target, *peers),
        target_symbol="TARGET",
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=60,
        )
    )
    assert result.status == PREDICTOR_STATUS_READY
    assert result.expected_return_pct > 0


def test_predictor_is_deterministic() -> None:
    target = _entry("TARGET", pe=8.0, roic=20.0, r12=30.0)
    peers = [_entry(f"P{i}") for i in range(10)]
    pred = QvmFactorPredictor(
        universe=_universe(target, *peers), target_symbol="TARGET"
    )
    inputs = PredictorInputs(
        historical_bars=_bars(_noisy_uptrend()),
        current_price=Decimal("100"),
        horizon_trading_days=21,
    )
    a = pred.predict(inputs)
    b = pred.predict(inputs)
    assert a == b


def test_explanation_mentions_qvm_components_and_universe_size() -> None:
    target = _entry("TARGET", pe=8.0)
    peers = [_entry(f"P{i}") for i in range(10)]
    pred = QvmFactorPredictor(
        universe=_universe(target, *peers), target_symbol="TARGET"
    )
    result = pred.predict(
        PredictorInputs(
            historical_bars=_bars(_noisy_uptrend()),
            current_price=Decimal("100"),
            horizon_trading_days=21,
        )
    )
    text = result.explanation_nl
    assert "Q=" in text and "V=" in text and "M=" in text
    assert "composite" in text
    assert "11" in text  # universe-size 1 target + 10 peers


def test_predictor_identity() -> None:
    pred = QvmFactorPredictor(
        universe=_universe(*[_entry(f"S{i}") for i in range(6)]),
        target_symbol="S0",
    )
    assert pred.model_code == QVM_MODEL_CODE
    assert pred.model_version
