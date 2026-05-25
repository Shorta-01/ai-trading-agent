"""AI time-series predictor (Slice 18) — packages/portfolio side.

The fifth predictor in the V1 §21.4 ensemble. AI participates as **one
vote** alongside the four deterministic predictors (GBM, Momentum,
Mean-Reversion, QVM); the ensemble combiner already enforces that no
single predictor overrides the action label.

This module is the deterministic boundary the rest of the system
depends on. It:

1. Defines the locked input/output contract (``TsModelProviderInputs``,
   ``TsModelProviderResult``, ``TsModelProviderProtocol``,
   ``TsModelProviderUnavailable``).
2. Validates the provider's output (numeric quantile ordering,
   prob_gain ∈ [0, 1], blank-string + bounded-confidence checks).
3. Wraps everything in :class:`AiTsPredictor` which implements
   :class:`PredictorProtocol` and gracefully degrades to a
   ``status=blocked`` distribution when the provider is unavailable.

The actual provider implementations (stub + future TimesFM /
Chronos / Lag-Llama wrappers) live in ``apps/api`` so this package
remains stdlib-only and free of any AI dependency.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol

from .baseline_forecast import HistoricalBar
from .predictor_protocol import (
    BLOCKING_REASON_INVALID_CURRENT_PRICE,
    BLOCKING_REASON_INVALID_HORIZON,
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_BLOCKED,
    STATUS_READY,
    PredictionDistribution,
    PredictorInputs,
)

MODEL_CODE: Final[str] = "ai_ts_v1"
MODEL_VERSION: Final[str] = "v1.0.0"

BLOCKING_REASON_PROVIDER_UNAVAILABLE: Final[str] = "provider_unavailable"
BLOCKING_REASON_PROVIDER_ERROR: Final[str] = "provider_error"
BLOCKING_REASON_INVALID_QUANTILES: Final[str] = "invalid_quantiles"
BLOCKING_REASON_INVALID_PROB_GAIN: Final[str] = "invalid_prob_gain"
BLOCKING_REASON_INVALID_CONFIDENCE: Final[str] = "invalid_confidence"


@dataclass(frozen=True)
class TsModelProviderInputs:
    """Input bundle for the AI time-series provider.

    Mirrors :class:`PredictorInputs` but flattened to the fields a
    foundation TS model actually needs (bars + horizon + an asset
    metadata mapping). Kept distinct so the provider boundary doesn't
    leak the full predictor-protocol shape.
    """

    historical_bars: Sequence[HistoricalBar]
    current_price: Decimal
    horizon_trading_days: int
    asset_symbol: str
    sector: str | None = None


@dataclass(frozen=True)
class TsModelProviderResult:
    """The locked output a provider must return.

    All quantiles in the issuing currency; `prob_gain` ∈ [0, 1];
    `confidence_score` ∈ [0, 1]. `model_provider_code`,
    `model_name` and `model_version` identify the runtime so the
    Prediction Diary can track accuracy per AI provider.
    """

    p10_price: Decimal
    p50_price: Decimal
    p90_price: Decimal
    prob_gain: Decimal
    expected_return_pct: Decimal
    confidence_score: Decimal
    model_provider_code: str
    model_name: str
    model_version: str
    explanation_nl: str


class TsModelProviderProtocol(Protocol):
    """Every AI TS-model provider implements this."""

    def forecast(self, inputs: TsModelProviderInputs) -> TsModelProviderResult: ...


@dataclass(frozen=True)
class TsModelProviderUnavailable:
    """Sentinel returned by the factory when no provider is available."""

    reason: str
    detail_nl: str


def _direction_label(expected_return_pct: Decimal) -> str:
    val = float(expected_return_pct)
    if val >= 10.0:
        return DIRECTION_STRONG_UP
    if val >= 2.0:
        return DIRECTION_SLIGHT_UP
    if val > -2.0:
        return DIRECTION_FLAT
    if val > -10.0:
        return DIRECTION_SLIGHT_DOWN
    return DIRECTION_STRONG_DOWN


def _blocked(
    *,
    horizon_trading_days: int,
    current_price: Decimal,
    reason: str,
    explanation_nl: str,
) -> PredictionDistribution:
    safe_horizon = horizon_trading_days if horizon_trading_days > 0 else 21
    safe_price = current_price if current_price > 0 else Decimal("0.000001")
    return PredictionDistribution(
        model_code=MODEL_CODE,
        model_version=MODEL_VERSION,
        horizon_trading_days=safe_horizon,
        current_price=safe_price,
        p10_price=safe_price,
        p50_price=safe_price,
        p90_price=safe_price,
        prob_gain=Decimal("0.500000"),
        prob_loss=Decimal("0.500000"),
        expected_return_pct=Decimal("0.000000"),
        direction=DIRECTION_FLAT,
        confidence_score=Decimal("0.000000"),
        status=STATUS_BLOCKED,
        blocking_reason=reason,
        explanation_nl=explanation_nl,
    )


def _validate_result(
    result: TsModelProviderResult,
) -> tuple[str, str | None] | None:
    """Return ``(blocking_reason, detail_nl)`` if the provider output
    violates the locked contract, otherwise ``None``."""

    if not (result.p10_price <= result.p50_price <= result.p90_price):
        return (
            BLOCKING_REASON_INVALID_QUANTILES,
            "Provider gaf kwantielen die niet monotoon stijgen "
            "(p10 ≤ p50 ≤ p90).",
        )
    if not (Decimal("0") <= result.prob_gain <= Decimal("1")):
        return (
            BLOCKING_REASON_INVALID_PROB_GAIN,
            "Provider's prob_gain ligt buiten [0, 1].",
        )
    if not (Decimal("0") <= result.confidence_score <= Decimal("1")):
        return (
            BLOCKING_REASON_INVALID_CONFIDENCE,
            "Provider's confidence_score ligt buiten [0, 1].",
        )
    return None


class AiTsPredictor:
    """AI foundation TS-model predictor exposed via :class:`PredictorProtocol`.

    The provider is injected. When the injected object is a
    :class:`TsModelProviderUnavailable` sentinel, every prediction
    returns a ``status=blocked`` distribution with reason
    ``provider_unavailable`` — the ensemble combiner then drops the AI
    vote cleanly. Provider exceptions are caught at the boundary and
    surfaced as a ``provider_error`` block.
    """

    def __init__(
        self,
        *,
        provider: TsModelProviderProtocol | TsModelProviderUnavailable,
    ) -> None:
        self._provider = provider

    @property
    def model_code(self) -> str:
        return MODEL_CODE

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def predict(self, inputs: PredictorInputs) -> PredictionDistribution:
        if inputs.horizon_trading_days <= 0:
            return _blocked(
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INVALID_HORIZON,
                explanation_nl="Horizon moet positief zijn.",
            )
        if inputs.current_price <= 0:
            return _blocked(
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_INVALID_CURRENT_PRICE,
                explanation_nl="Huidige prijs is niet beschikbaar of <= 0.",
            )

        if isinstance(self._provider, TsModelProviderUnavailable):
            return _blocked(
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_PROVIDER_UNAVAILABLE,
                explanation_nl=self._provider.detail_nl,
            )

        symbol = inputs.asset_metadata.get("symbol", "")
        sector = inputs.asset_metadata.get("sector")
        provider_inputs = TsModelProviderInputs(
            historical_bars=inputs.historical_bars,
            current_price=inputs.current_price,
            horizon_trading_days=inputs.horizon_trading_days,
            asset_symbol=symbol,
            sector=sector,
        )
        try:
            result = self._provider.forecast(provider_inputs)
        except Exception as exc:  # noqa: BLE001 — boundary catch
            return _blocked(
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                reason=BLOCKING_REASON_PROVIDER_ERROR,
                explanation_nl=f"AI TS-provider gaf een fout: {exc}",
            )

        validation = _validate_result(result)
        if validation is not None:
            blocking_reason, detail_nl = validation
            return _blocked(
                horizon_trading_days=inputs.horizon_trading_days,
                current_price=inputs.current_price,
                reason=blocking_reason,
                explanation_nl=detail_nl or "AI TS-provider output ongeldig.",
            )

        prob_loss = max(Decimal("0"), Decimal("1") - result.prob_gain)
        explanation = (
            f"AI TS-model ({result.model_provider_code}/{result.model_name}) "
            f"voorspelt p50 {result.p50_price} over {inputs.horizon_trading_days} "
            f"dagen (verwachte rendement {result.expected_return_pct}%). "
            + result.explanation_nl
        )
        return PredictionDistribution(
            model_code=MODEL_CODE,
            model_version=MODEL_VERSION,
            horizon_trading_days=inputs.horizon_trading_days,
            current_price=inputs.current_price,
            p10_price=result.p10_price,
            p50_price=result.p50_price,
            p90_price=result.p90_price,
            prob_gain=result.prob_gain,
            prob_loss=prob_loss,
            expected_return_pct=result.expected_return_pct,
            direction=_direction_label(result.expected_return_pct),
            confidence_score=result.confidence_score,
            status=STATUS_READY,
            blocking_reason=None,
            explanation_nl=explanation,
        )


__all__ = [
    "MODEL_CODE",
    "MODEL_VERSION",
    "BLOCKING_REASON_PROVIDER_UNAVAILABLE",
    "BLOCKING_REASON_PROVIDER_ERROR",
    "BLOCKING_REASON_INVALID_QUANTILES",
    "BLOCKING_REASON_INVALID_PROB_GAIN",
    "BLOCKING_REASON_INVALID_CONFIDENCE",
    "TsModelProviderInputs",
    "TsModelProviderResult",
    "TsModelProviderProtocol",
    "TsModelProviderUnavailable",
    "AiTsPredictor",
]
