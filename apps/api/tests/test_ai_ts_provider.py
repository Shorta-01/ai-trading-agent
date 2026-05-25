"""Tests for the AI TS provider stub + factory (Slice 18)."""

from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal

from portfolio_outlook_portfolio import (
    HistoricalBar,
    TsModelProviderInputs,
    TsModelProviderUnavailable,
)

from portfolio_outlook_api.ai_ts_provider import (
    STUB_PROVIDER_CODE,
    StubTsModelProvider,
    build_ts_model_provider,
)
from portfolio_outlook_api.config import Settings


def _settings(**overrides: object) -> Settings:
    base = Settings()
    for key, value in overrides.items():
        setattr(base, key, value)
    return base


def _bars(closes: list[float], start: date = date(2025, 1, 1)) -> list[HistoricalBar]:
    return [
        HistoricalBar(bar_date=start + timedelta(days=i), close_price=Decimal(str(c)))
        for i, c in enumerate(closes)
    ]


def _stub_inputs(
    *,
    closes: list[float] | None = None,
    current_price: str = "100",
    horizon: int = 21,
) -> TsModelProviderInputs:
    series = closes if closes is not None else [100.0 + 0.05 * i for i in range(260)]
    return TsModelProviderInputs(
        historical_bars=_bars(series),
        current_price=Decimal(current_price),
        horizon_trading_days=horizon,
        asset_symbol="AAPL",
        sector="Technology",
    )


# ---- factory --------------------------------------------------------


def test_factory_returns_unavailable_when_predictor_disabled() -> None:
    result = build_ts_model_provider(_settings())
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "ai_ts_predictor_disabled"


def test_factory_returns_stub_when_enabled_with_stub_code() -> None:
    result = build_ts_model_provider(
        _settings(
            ai_ts_predictor_enabled=True,
            ai_ts_predictor_provider_code=STUB_PROVIDER_CODE,
        )
    )
    assert isinstance(result, StubTsModelProvider)


def test_factory_returns_unavailable_when_real_client_not_enabled() -> None:
    result = build_ts_model_provider(
        _settings(
            ai_ts_predictor_enabled=True,
            ai_ts_predictor_provider_code="anthropic",
            ai_ts_predictor_real_client_enabled=False,
        )
    )
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "real_client_not_enabled"


def test_factory_returns_unavailable_for_unimplemented_real_provider() -> None:
    result = build_ts_model_provider(
        _settings(
            ai_ts_predictor_enabled=True,
            ai_ts_predictor_provider_code="anthropic",
            ai_ts_predictor_real_client_enabled=True,
        )
    )
    assert isinstance(result, TsModelProviderUnavailable)
    assert result.reason == "real_client_not_implemented"


# ---- stub provider --------------------------------------------------


def test_stub_emits_monotone_quantiles_on_a_clean_series() -> None:
    provider = StubTsModelProvider()
    result = provider.forecast(_stub_inputs())
    assert result.p10_price <= result.p50_price <= result.p90_price
    assert Decimal("0") <= result.prob_gain <= Decimal("1")
    assert Decimal("0") <= result.confidence_score <= Decimal("1")
    assert result.model_provider_code == STUB_PROVIDER_CODE


def test_stub_neutral_distribution_on_short_history() -> None:
    provider = StubTsModelProvider()
    result = provider.forecast(_stub_inputs(closes=[100.0] * 10))
    # Too few bars → fallback neutral distribution centred on current price.
    assert result.p50_price == Decimal("100.000000")
    assert result.prob_gain == Decimal("0.500000")
    assert result.confidence_score == Decimal("0.100000")


def test_stub_neutral_distribution_when_current_price_is_zero() -> None:
    provider = StubTsModelProvider()
    result = provider.forecast(_stub_inputs(current_price="0"))
    # Current price 0 → fallback path; the result is a tiny positive
    # distribution rather than a hard error so the predictor can still
    # render a row.
    assert result.p50_price > Decimal("0")


def test_stub_signals_positive_drift_on_steady_uptrend() -> None:
    closes = [100.0 * math.exp(0.001 * i) for i in range(260)]
    provider = StubTsModelProvider()
    result = provider.forecast(_stub_inputs(closes=closes, current_price=str(closes[-1])))
    assert result.expected_return_pct > Decimal("0")
    assert result.prob_gain > Decimal("0.5")


def test_stub_signals_negative_drift_on_steady_downtrend() -> None:
    closes = [100.0 * math.exp(-0.001 * i) for i in range(260)]
    provider = StubTsModelProvider()
    result = provider.forecast(_stub_inputs(closes=closes, current_price=str(closes[-1])))
    assert result.expected_return_pct < Decimal("0")
    assert result.prob_gain < Decimal("0.5")


def test_stub_is_deterministic() -> None:
    provider = StubTsModelProvider()
    a = provider.forecast(_stub_inputs())
    b = provider.forecast(_stub_inputs())
    assert a == b


def test_stub_explanation_mentions_provider_code() -> None:
    provider = StubTsModelProvider()
    result = provider.forecast(_stub_inputs())
    assert "Stub TS-provider" in result.explanation_nl
