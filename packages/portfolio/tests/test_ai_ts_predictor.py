"""Tests for the AI TS predictor + protocol guards (Slice 18)."""

from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    AI_TS_BLOCKING_REASON_INVALID_CONFIDENCE,
    AI_TS_BLOCKING_REASON_INVALID_PROB_GAIN,
    AI_TS_BLOCKING_REASON_INVALID_QUANTILES,
    AI_TS_BLOCKING_REASON_PROVIDER_ERROR,
    AI_TS_BLOCKING_REASON_PROVIDER_UNAVAILABLE,
    AI_TS_MODEL_CODE,
    BLOCKING_REASON_INVALID_CURRENT_PRICE,
    BLOCKING_REASON_INVALID_HORIZON,
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_UP,
    PREDICTOR_STATUS_BLOCKED,
    PREDICTOR_STATUS_READY,
    AiTsPredictor,
    HistoricalBar,
    PredictorInputs,
    TsModelProviderInputs,
    TsModelProviderResult,
    TsModelProviderUnavailable,
)


def _bars(closes: list[float], start: date = date(2025, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


def _inputs(
    *,
    horizon: int = 21,
    current_price: str = "100",
    metadata: dict[str, str] | None = None,
) -> PredictorInputs:
    return PredictorInputs(
        historical_bars=_bars([100.0] * 60),
        current_price=Decimal(current_price),
        horizon_trading_days=horizon,
        asset_metadata=metadata or {"symbol": "AAPL"},
    )


def _provider_result(
    *,
    p10: str = "95",
    p50: str = "100",
    p90: str = "105",
    prob_gain: str = "0.55",
    expected_return_pct: str = "1.0",
    confidence: str = "0.6",
) -> TsModelProviderResult:
    return TsModelProviderResult(
        p10_price=Decimal(p10),
        p50_price=Decimal(p50),
        p90_price=Decimal(p90),
        prob_gain=Decimal(prob_gain),
        expected_return_pct=Decimal(expected_return_pct),
        confidence_score=Decimal(confidence),
        model_provider_code="stub",
        model_name="empirical",
        model_version="v1",
        explanation_nl="ok",
    )


class _StaticProvider:
    def __init__(self, result: TsModelProviderResult) -> None:
        self._result = result

    def forecast(self, _inputs: TsModelProviderInputs) -> TsModelProviderResult:
        return self._result


class _RaisingProvider:
    def forecast(self, _inputs: TsModelProviderInputs) -> TsModelProviderResult:
        raise RuntimeError("provider-down")


# ---- happy path ------------------------------------------------------


def test_happy_path_returns_ready_with_provider_quantiles() -> None:
    predictor = AiTsPredictor(provider=_StaticProvider(_provider_result()))
    result = predictor.predict(_inputs())
    assert result.status == PREDICTOR_STATUS_READY
    assert result.model_code == AI_TS_MODEL_CODE
    assert result.p10_price == Decimal("95")
    assert result.p50_price == Decimal("100")
    assert result.p90_price == Decimal("105")
    assert result.prob_gain == Decimal("0.55")
    assert result.direction == DIRECTION_FLAT


def test_explanation_includes_provider_identity_and_horizon() -> None:
    predictor = AiTsPredictor(provider=_StaticProvider(_provider_result()))
    result = predictor.predict(_inputs())
    assert "stub" in result.explanation_nl
    assert "21" in result.explanation_nl


def test_direction_maps_from_expected_return() -> None:
    pred_strong = AiTsPredictor(
        provider=_StaticProvider(_provider_result(expected_return_pct="12.0"))
    )
    assert pred_strong.predict(_inputs()).direction == DIRECTION_STRONG_UP

    pred_slight = AiTsPredictor(
        provider=_StaticProvider(_provider_result(expected_return_pct="5.0"))
    )
    assert pred_slight.predict(_inputs()).direction == DIRECTION_SLIGHT_UP

    pred_down = AiTsPredictor(
        provider=_StaticProvider(_provider_result(expected_return_pct="-4.0"))
    )
    assert pred_down.predict(_inputs()).direction == DIRECTION_SLIGHT_DOWN


def test_prob_loss_is_one_minus_prob_gain() -> None:
    pred = AiTsPredictor(
        provider=_StaticProvider(_provider_result(prob_gain="0.7"))
    )
    result = pred.predict(_inputs())
    assert result.prob_loss == Decimal("0.3")


# ---- blocked paths --------------------------------------------------


def test_blocks_on_invalid_horizon() -> None:
    pred = AiTsPredictor(provider=_StaticProvider(_provider_result()))
    result = pred.predict(_inputs(horizon=0))
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_HORIZON


def test_blocks_on_zero_current_price() -> None:
    pred = AiTsPredictor(provider=_StaticProvider(_provider_result()))
    result = pred.predict(_inputs(current_price="0"))
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == BLOCKING_REASON_INVALID_CURRENT_PRICE


def test_blocks_when_provider_is_unavailable() -> None:
    pred = AiTsPredictor(
        provider=TsModelProviderUnavailable(
            reason="ai_ts_predictor_disabled",
            detail_nl="provider is uitgeschakeld in deze test",
        )
    )
    result = pred.predict(_inputs())
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == AI_TS_BLOCKING_REASON_PROVIDER_UNAVAILABLE
    assert "uitgeschakeld" in result.explanation_nl


def test_blocks_when_provider_raises() -> None:
    pred = AiTsPredictor(provider=_RaisingProvider())
    result = pred.predict(_inputs())
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == AI_TS_BLOCKING_REASON_PROVIDER_ERROR
    assert "provider-down" in result.explanation_nl


def test_blocks_when_quantiles_are_not_monotone() -> None:
    pred = AiTsPredictor(
        provider=_StaticProvider(_provider_result(p10="105", p50="100", p90="110"))
    )
    result = pred.predict(_inputs())
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == AI_TS_BLOCKING_REASON_INVALID_QUANTILES


def test_blocks_when_prob_gain_is_out_of_range() -> None:
    pred = AiTsPredictor(
        provider=_StaticProvider(_provider_result(prob_gain="1.5"))
    )
    result = pred.predict(_inputs())
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == AI_TS_BLOCKING_REASON_INVALID_PROB_GAIN


def test_blocks_when_confidence_is_out_of_range() -> None:
    pred = AiTsPredictor(
        provider=_StaticProvider(_provider_result(confidence="-0.1"))
    )
    result = pred.predict(_inputs())
    assert result.status == PREDICTOR_STATUS_BLOCKED
    assert result.blocking_reason == AI_TS_BLOCKING_REASON_INVALID_CONFIDENCE


# ---- deterministic + identity ---------------------------------------


def test_predictor_is_deterministic_given_same_provider_output() -> None:
    pred = AiTsPredictor(provider=_StaticProvider(_provider_result()))
    a = pred.predict(_inputs())
    b = pred.predict(_inputs())
    assert a == b


def test_predictor_exposes_model_identity() -> None:
    pred = AiTsPredictor(provider=_StaticProvider(_provider_result()))
    assert pred.model_code == AI_TS_MODEL_CODE
    assert pred.model_version


def test_asset_metadata_is_forwarded_to_provider() -> None:
    captured: list[TsModelProviderInputs] = []

    class _CapturingProvider:
        def forecast(self, inputs: TsModelProviderInputs) -> TsModelProviderResult:
            captured.append(inputs)
            return _provider_result()

    pred = AiTsPredictor(provider=_CapturingProvider())
    pred.predict(
        _inputs(metadata={"symbol": "MSFT", "sector": "Technology"})
    )
    assert captured[0].asset_symbol == "MSFT"
    assert captured[0].sector == "Technology"
