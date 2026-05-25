"""Deterministic ensemble combiner (Slice 15).

Locked in `version-1-product-experience-locks.md §21.4`. The combiner:

1. Runs every supplied predictor on the same `PredictorInputs`.
2. Drops any predictor whose result is ``blocked``.
3. Combines the surviving distributions via weighted averages of
   p10/p50/p90, expected return %, prob_gain/loss and confidence.
4. Re-derives the direction label from the combined expected return.
5. Returns a single :class:`PredictionDistribution` with
   ``model_code = "ensemble_v1"`` plus a tuple of per-predictor
   :class:`EnsembleContribution` rows for downstream Diary tracking.

Default weighting is **equal-weight** across surviving predictors. The
caller can pass a ``weights`` mapping (``model_code → weight``) to
override; weights are normalised so they sum to 1.0 across the
surviving predictors. Unknown model_codes in the mapping are ignored
silently — the combiner only uses weights for predictors that actually
ran and were ready.

Pure Python. The combiner is deterministic given the same inputs +
predictor outputs + weight mapping; no AI, no randomness, no I/O.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

from .predictor_protocol import (
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_BLOCKED,
    STATUS_READY,
    PredictionDistribution,
    PredictorInputs,
    PredictorProtocol,
)

ENSEMBLE_MODEL_CODE: Final[str] = "ensemble_v1"
ENSEMBLE_MODEL_VERSION: Final[str] = "v1.0.0"

# Direction thresholds (same as the individual predictors).
THRESHOLD_STRONG_PCT: Final[float] = 10.0
THRESHOLD_SLIGHT_PCT: Final[float] = 2.0


# V1.1 §22.5 weight-strategy lock.
WEIGHT_STRATEGY_EQUAL: Final[str] = "equal_weight"
WEIGHT_STRATEGY_AUTO: Final[str] = "auto"
ALLOWED_WEIGHT_STRATEGIES: Final[frozenset[str]] = frozenset(
    {WEIGHT_STRATEGY_EQUAL, WEIGHT_STRATEGY_AUTO}
)


@dataclass(frozen=True)
class EnsembleContribution:
    """One row per predictor for downstream tracking.

    ``weight_raw`` is the input weight (1.0 when defaulted); ``weight_normalised``
    is the share of the ensemble after normalising surviving predictors
    to sum 1.0.
    """

    model_code: str
    model_version: str
    weight_raw: Decimal
    weight_normalised: Decimal
    prediction: PredictionDistribution


@dataclass(frozen=True)
class EnsembleResult:
    """Combined ensemble forecast + per-predictor breakdown."""

    forecast: PredictionDistribution
    contributions: tuple[EnsembleContribution, ...]
    blocked_model_codes: tuple[str, ...]


def _direction_label(expected_return_pct: float) -> str:
    if expected_return_pct >= THRESHOLD_STRONG_PCT:
        return DIRECTION_STRONG_UP
    if expected_return_pct >= THRESHOLD_SLIGHT_PCT:
        return DIRECTION_SLIGHT_UP
    if expected_return_pct > -THRESHOLD_SLIGHT_PCT:
        return DIRECTION_FLAT
    if expected_return_pct > -THRESHOLD_STRONG_PCT:
        return DIRECTION_SLIGHT_DOWN
    return DIRECTION_STRONG_DOWN


def _decimal(value: float, places: int = 6) -> Decimal:
    quant = Decimal(10) ** -places
    return Decimal(str(value)).quantize(quant)


def _money(value: float) -> Decimal:
    return _decimal(value, 6)


def _prob(value: float) -> Decimal:
    bounded = max(0.0, min(1.0, value))
    return _decimal(bounded, 6)


def _blocked_ensemble(
    *,
    inputs: PredictorInputs,
    reason: str,
    explanation_nl: str,
    blocked_codes: tuple[str, ...],
) -> EnsembleResult:
    safe_horizon = (
        inputs.horizon_trading_days if inputs.horizon_trading_days > 0 else 21
    )
    safe_price = inputs.current_price if inputs.current_price > 0 else Decimal("0.000001")
    forecast = PredictionDistribution(
        model_code=ENSEMBLE_MODEL_CODE,
        model_version=ENSEMBLE_MODEL_VERSION,
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
    return EnsembleResult(
        forecast=forecast, contributions=(), blocked_model_codes=blocked_codes
    )


def _agreement_factor(directions: Sequence[str]) -> float:
    """Multiplier on the combined confidence based on directional agreement.

    Returns 1.0 when every surviving predictor agrees on the direction;
    0.6 when there's mixed agreement; 0.4 when there's strong
    disagreement (positive + negative directions in the same set).
    """

    if not directions:
        return 0.0
    positive = sum(1 for d in directions if d in {DIRECTION_STRONG_UP, DIRECTION_SLIGHT_UP})
    negative = sum(1 for d in directions if d in {DIRECTION_STRONG_DOWN, DIRECTION_SLIGHT_DOWN})
    total = len(directions)
    if positive == total or negative == total:
        return 1.0
    if positive > 0 and negative > 0:
        return 0.4
    # One side + some flat
    return 0.6


def compute_ensemble_forecast(
    predictors: Sequence[PredictorProtocol],
    inputs: PredictorInputs,
    *,
    weights: dict[str, Decimal] | None = None,
    weight_strategy: str = WEIGHT_STRATEGY_EQUAL,
    brier_history: Mapping[str, Decimal | float | None] | None = None,
) -> EnsembleResult:
    """Run every predictor, drop blocked ones, combine the rest.

    Returns an :class:`EnsembleResult` containing the combined
    :class:`PredictionDistribution` and the per-predictor contributions
    + the list of blocked model_codes (so the orchestrator can log
    them as "did not participate" without losing trace).

    V1.1 §22.5 — ``weight_strategy``:

    * ``"equal_weight"`` (default) keeps the V1 behaviour. Optional
      ``weights`` override is still honoured.
    * ``"auto"`` consumes ``brier_history`` (a
      ``{model_code: rolling_brier}`` mapping) via
      :func:`compute_inverse_brier_weights` to up-weight the
      predictors with the lowest Brier score. The lower clip
      (`0.05` per the locked band) prevents any predictor from
      being silenced even after a long bad run.
    """

    if weight_strategy not in ALLOWED_WEIGHT_STRATEGIES:
        raise ValueError(
            f"weight_strategy must be one of {sorted(ALLOWED_WEIGHT_STRATEGIES)}, "
            f"got {weight_strategy!r}"
        )

    if not predictors:
        return _blocked_ensemble(
            inputs=inputs,
            reason="no_predictors",
            explanation_nl="Geen predictors geleverd aan de ensemble combiner.",
            blocked_codes=(),
        )

    all_predictions: list[PredictionDistribution] = [
        predictor.predict(inputs) for predictor in predictors
    ]
    ready = [p for p in all_predictions if p.status == STATUS_READY]
    blocked_codes = tuple(p.model_code for p in all_predictions if p.status == STATUS_BLOCKED)

    if not ready:
        return _blocked_ensemble(
            inputs=inputs,
            reason="all_predictors_blocked",
            explanation_nl=(
                "Alle predictors leverden een blocked-result; ensemble heeft "
                "geen ready-input."
            ),
            blocked_codes=blocked_codes,
        )

    # Resolve weights for surviving predictors. Missing entries default
    # to 1.0; non-positive weights default to 1.0 as well (a 0 weight
    # would effectively drop the predictor — use the dropped-predictor
    # path explicitly instead).
    weights_map: dict[str, Decimal] = dict(weights or {})

    if weight_strategy == WEIGHT_STRATEGY_AUTO:
        # Lazy import to avoid an import cycle between the combiner
        # and the feedback module (which itself imports the combiner's
        # value objects).
        from .predictor_feedback import compute_inverse_brier_weights

        ready_codes = [p.model_code for p in ready]
        history_subset: dict[str, Decimal | float | None] = {}
        if brier_history is not None:
            for code in ready_codes:
                if code in brier_history:
                    history_subset[code] = brier_history[code]
        auto_weights = compute_inverse_brier_weights(
            history_subset, fallback_codes=ready_codes
        )
        # Auto-weighting takes precedence over any operator-supplied
        # static weights for the codes it returns; codes outside its
        # output keep the static value (or 1.0 default).
        weights_map.update(auto_weights)

    raw_weights: list[Decimal] = []
    for pred in ready:
        w = weights_map.get(pred.model_code, Decimal("1.0"))
        raw_weights.append(w if w > 0 else Decimal("1.0"))
    total = sum(raw_weights, start=Decimal("0"))
    if total == 0:
        return _blocked_ensemble(
            inputs=inputs,
            reason="zero_total_weight",
            explanation_nl=(
                "Som van predictor-gewichten is 0; ensemble kan niet combineren."
            ),
            blocked_codes=blocked_codes,
        )
    norm_weights = [w / total for w in raw_weights]

    # Weighted averages on the floats then back to Decimal.
    def _weighted_avg(values: list[Decimal]) -> float:
        return float(
            sum(v * w for v, w in zip(values, norm_weights, strict=True))
        )

    p10 = _weighted_avg([p.p10_price for p in ready])
    p50 = _weighted_avg([p.p50_price for p in ready])
    p90 = _weighted_avg([p.p90_price for p in ready])
    prob_gain = _weighted_avg([p.prob_gain for p in ready])
    prob_loss = max(0.0, min(1.0, 1.0 - prob_gain))
    expected_return_pct = _weighted_avg([p.expected_return_pct for p in ready])
    base_confidence = _weighted_avg([p.confidence_score for p in ready])
    agreement = _agreement_factor([p.direction for p in ready])
    confidence = base_confidence * agreement

    direction = _direction_label(expected_return_pct)

    explanation_parts = [
        f"Ensemble over {len(ready)} ready-predictor(s)"
        f" (agreement={agreement:.2f}):"
    ]
    for pred, w_norm in zip(ready, norm_weights, strict=True):
        explanation_parts.append(
            f"  • {pred.model_code} (w={float(w_norm):.2f}, "
            f"dir={pred.direction}, ret={float(pred.expected_return_pct):.2f}%)"
        )
    if blocked_codes:
        explanation_parts.append(
            "Blocked: " + ", ".join(blocked_codes)
        )
    explanation = "\n".join(explanation_parts)

    forecast = PredictionDistribution(
        model_code=ENSEMBLE_MODEL_CODE,
        model_version=ENSEMBLE_MODEL_VERSION,
        horizon_trading_days=inputs.horizon_trading_days,
        current_price=inputs.current_price,
        p10_price=_money(p10),
        p50_price=_money(p50),
        p90_price=_money(p90),
        prob_gain=_prob(prob_gain),
        prob_loss=_prob(prob_loss),
        expected_return_pct=_decimal(expected_return_pct, 6),
        direction=direction,
        confidence_score=_decimal(max(0.0, min(1.0, confidence)), 6),
        status=STATUS_READY,
        blocking_reason=None,
        explanation_nl=explanation,
    )

    contributions = tuple(
        EnsembleContribution(
            model_code=pred.model_code,
            model_version=pred.model_version,
            weight_raw=raw_weights[i],
            weight_normalised=norm_weights[i],
            prediction=pred,
        )
        for i, pred in enumerate(ready)
    )
    return EnsembleResult(
        forecast=forecast,
        contributions=contributions,
        blocked_model_codes=blocked_codes,
    )


__all__ = [
    "ALLOWED_WEIGHT_STRATEGIES",
    "ENSEMBLE_MODEL_CODE",
    "ENSEMBLE_MODEL_VERSION",
    "WEIGHT_STRATEGY_AUTO",
    "WEIGHT_STRATEGY_EQUAL",
    "EnsembleContribution",
    "EnsembleResult",
    "compute_ensemble_forecast",
]
