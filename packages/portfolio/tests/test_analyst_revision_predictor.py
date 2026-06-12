"""Tests for the analyst-revision predictor (V1.2 §O)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    ANALYST_REVISION_MODEL_CODE,
    BLOCKING_REASON_NO_ANALYST_DATA,
    AnalystRevisionEntry,
    AnalystRevisionPredictor,
    AnalystRevisionUniverse,
    HistoricalBar,
)
from portfolio_outlook_portfolio.predictor_protocol import (
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_BLOCKED,
    STATUS_READY,
    PredictorInputs,
)


def _bars(count: int = 130) -> list[HistoricalBar]:
    """Series with moderate vol so the predictor gets a stable σ."""

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
    return bars


def _universe(**entries: AnalystRevisionEntry) -> AnalystRevisionUniverse:
    return AnalystRevisionUniverse(entries=dict(entries))


def _inputs(
    *,
    symbol: str = "AAPL",
    current_price: Decimal = Decimal("100"),
    horizon: int = 126,
    bar_count: int = 130,
) -> PredictorInputs:
    return PredictorInputs(
        historical_bars=_bars(bar_count),
        current_price=current_price,
        horizon_trading_days=horizon,
        asset_metadata={"symbol": symbol},
    )


# ---- happy path ------------------------------------------------------


def test_strong_up_revisions_produce_up_direction() -> None:
    # Big revisions all pointing up — composite ≈ 0.32, annual drift
    # ≈ 8 %, half-year drift ≈ 4 %.
    entry = AnalystRevisionEntry(
        symbol="AAPL",
        eps_current_estimate=Decimal("9.00"),  # up 29 % vs 3m ago
        eps_estimate_3m_ago=Decimal("7.00"),
        eps_estimate_6m_ago=Decimal("6.00"),  # up 50 % vs 6m ago
        target_price_current=Decimal("240"),
        target_price_3m_ago=Decimal("200"),  # up 20 %
    )
    pred = AnalystRevisionPredictor(universe=_universe(AAPL=entry))
    result = pred.predict(_inputs())
    assert result.status == STATUS_READY
    assert result.direction in {DIRECTION_SLIGHT_UP, DIRECTION_STRONG_UP}
    assert result.confidence_score > Decimal("0.50")


def test_strong_down_revisions_produce_down_direction() -> None:
    entry = AnalystRevisionEntry(
        symbol="XYZ",
        eps_current_estimate=Decimal("3.50"),  # down 42 % vs 3m ago
        eps_estimate_3m_ago=Decimal("6.00"),
        eps_estimate_6m_ago=Decimal("7.00"),  # down 50 % vs 6m ago
        target_price_current=Decimal("70"),
        target_price_3m_ago=Decimal("100"),  # down 30 %
    )
    pred = AnalystRevisionPredictor(universe=_universe(XYZ=entry))
    result = pred.predict(_inputs(symbol="XYZ"))
    assert result.status == STATUS_READY
    assert result.direction in {DIRECTION_SLIGHT_DOWN, DIRECTION_STRONG_DOWN}


def test_no_revisions_produces_flat() -> None:
    # Same estimate now as 3m + 6m ago — composite = 0, drift ≈ 0.
    entry = AnalystRevisionEntry(
        symbol="FLAT",
        eps_current_estimate=Decimal("5.00"),
        eps_estimate_3m_ago=Decimal("5.00"),
        eps_estimate_6m_ago=Decimal("5.00"),
        target_price_current=Decimal("100"),
        target_price_3m_ago=Decimal("100"),
    )
    pred = AnalystRevisionPredictor(universe=_universe(FLAT=entry))
    result = pred.predict(_inputs(symbol="FLAT"))
    assert result.status == STATUS_READY
    assert result.direction == DIRECTION_FLAT


def test_confidence_higher_when_components_agree() -> None:
    agree = AnalystRevisionEntry(
        symbol="A",
        eps_current_estimate=Decimal("8"),
        eps_estimate_3m_ago=Decimal("7"),
        eps_estimate_6m_ago=Decimal("6.5"),
        target_price_current=Decimal("220"),
        target_price_3m_ago=Decimal("200"),
    )
    disagree = AnalystRevisionEntry(
        symbol="D",
        eps_current_estimate=Decimal("8"),
        eps_estimate_3m_ago=Decimal("7"),  # EPS up
        eps_estimate_6m_ago=Decimal("9"),  # EPS down vs 6m
        target_price_current=Decimal("180"),  # target down
        target_price_3m_ago=Decimal("200"),
    )
    pred_a = AnalystRevisionPredictor(universe=_universe(A=agree))
    pred_d = AnalystRevisionPredictor(universe=_universe(D=disagree))
    res_a = pred_a.predict(_inputs(symbol="A"))
    res_d = pred_d.predict(_inputs(symbol="D"))
    assert res_a.confidence_score > res_d.confidence_score


def test_partial_revisions_still_score() -> None:
    # Only the 3m EPS revision is available.
    entry = AnalystRevisionEntry(
        symbol="P",
        eps_current_estimate=Decimal("8"),
        eps_estimate_3m_ago=Decimal("7"),
    )
    pred = AnalystRevisionPredictor(universe=_universe(P=entry))
    result = pred.predict(_inputs(symbol="P"))
    assert result.status == STATUS_READY
    assert result.confidence_score > Decimal("0")
    # Confidence should be lower than a full 3-component case.
    full = AnalystRevisionEntry(
        symbol="F",
        eps_current_estimate=Decimal("8"),
        eps_estimate_3m_ago=Decimal("7"),
        eps_estimate_6m_ago=Decimal("6.5"),
        target_price_current=Decimal("220"),
        target_price_3m_ago=Decimal("200"),
    )
    pred_full = AnalystRevisionPredictor(universe=_universe(F=full))
    result_full = pred_full.predict(_inputs(symbol="F"))
    assert result.confidence_score < result_full.confidence_score


# ---- blocking paths --------------------------------------------------


def test_invalid_current_price_blocked() -> None:
    pred = AnalystRevisionPredictor(
        universe=_universe(
            X=AnalystRevisionEntry(
                symbol="X",
                eps_current_estimate=Decimal("8"),
                eps_estimate_3m_ago=Decimal("7"),
            )
        )
    )
    result = pred.predict(_inputs(current_price=Decimal("0"), symbol="X"))
    assert result.status == STATUS_BLOCKED


def test_invalid_horizon_blocked() -> None:
    pred = AnalystRevisionPredictor(universe=_universe())
    result = pred.predict(_inputs(horizon=0))
    assert result.status == STATUS_BLOCKED


def test_insufficient_bars_blocked() -> None:
    pred = AnalystRevisionPredictor(universe=_universe())
    result = pred.predict(_inputs(bar_count=50))  # < 100
    assert result.status == STATUS_BLOCKED


def test_no_universe_blocks_with_no_data() -> None:
    pred = AnalystRevisionPredictor(universe=None)
    result = pred.predict(_inputs())
    assert result.status == STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_NO_ANALYST_DATA


def test_symbol_not_in_universe_blocked() -> None:
    pred = AnalystRevisionPredictor(
        universe=_universe(
            OTHER=AnalystRevisionEntry(
                symbol="OTHER",
                eps_current_estimate=Decimal("8"),
                eps_estimate_3m_ago=Decimal("7"),
            )
        )
    )
    result = pred.predict(_inputs(symbol="AAPL"))
    assert result.status == STATUS_BLOCKED


def test_empty_entry_blocks() -> None:
    # All revision fields None → can't form a composite.
    pred = AnalystRevisionPredictor(
        universe=_universe(EMPTY=AnalystRevisionEntry(symbol="EMPTY"))
    )
    result = pred.predict(_inputs(symbol="EMPTY"))
    assert result.status == STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_NO_ANALYST_DATA


# ---- protocol contract -----------------------------------------------


def test_protocol_properties() -> None:
    pred = AnalystRevisionPredictor()
    assert pred.model_code == ANALYST_REVISION_MODEL_CODE
    assert pred.model_version  # non-empty


def test_distribution_invariants() -> None:
    entry = AnalystRevisionEntry(
        symbol="AAPL",
        eps_current_estimate=Decimal("8"),
        eps_estimate_3m_ago=Decimal("7"),
        eps_estimate_6m_ago=Decimal("6.5"),
        target_price_current=Decimal("220"),
        target_price_3m_ago=Decimal("200"),
    )
    pred = AnalystRevisionPredictor(universe=_universe(AAPL=entry))
    result = pred.predict(_inputs())
    # Lognormal invariants: p10 < p50 < p90 (assuming positive σ).
    assert result.p10_price < result.p50_price
    assert result.p50_price < result.p90_price
    # Probability sum invariant.
    assert (result.prob_gain + result.prob_loss - Decimal("1")).copy_abs() < Decimal("0.01")
    # Confidence and bounds.
    assert Decimal("0") <= result.confidence_score <= Decimal("1")


def test_clipping_caps_extreme_revisions() -> None:
    # A 500 % revision should be clipped to 100 % so the drift stays
    # at the cap.
    extreme = AnalystRevisionEntry(
        symbol="EX",
        eps_current_estimate=Decimal("6"),
        eps_estimate_3m_ago=Decimal("1"),  # 500 % up
        eps_estimate_6m_ago=Decimal("1"),  # 500 % up
        target_price_current=Decimal("500"),
        target_price_3m_ago=Decimal("100"),  # 400 % up
    )
    pred = AnalystRevisionPredictor(universe=_universe(EX=extreme))
    result = pred.predict(_inputs(symbol="EX"))
    # Composite is clipped to 1.0; annual drift = MAX × 1 = 25 %.
    # On a 126-day horizon → 12.5 %.
    assert result.status == STATUS_READY
    assert result.direction == DIRECTION_STRONG_UP
    # Expected return should be in the right ballpark.
    assert Decimal("5") < result.expected_return_pct < Decimal("20")
