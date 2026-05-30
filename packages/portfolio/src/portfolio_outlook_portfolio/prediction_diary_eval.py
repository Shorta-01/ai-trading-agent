"""Deterministic outcome-label rules for the Prediction Diary.

The diary captures every suggestion's *issued* forecast and the *realised*
market outcome at fixed horizons (1d/1w/1m). Outcome labels are computed
by a pure-Python rule engine — **AI never assigns the label**. The doctrine
in ``docs/product/action-draft-prediction-diary-alerts-decision-locks-task-127.md
§17`` is explicit on this.

Labels per horizon:

* ``right``           — the issued probability was > 0.5 and realised return
                        is in the right direction
* ``wrong``           — the issued probability was > 0.5 and the realised
                        return is in the **wrong** direction
* ``inconclusive``    — the realised return is within the p10..p90 forecast
                        band or too small to call (default ±0.25%)
* ``early``           — direction matched but magnitude undershot the p50
                        target (within the window between the current
                        horizon and the next)
* ``no_data``         — realised price is missing at this horizon
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Final, Protocol


class _DiaryEntryLike(Protocol):
    """Structural shape of a prediction-diary entry the live-Brier
    aggregator reads.

    Declared locally so the ``packages/portfolio`` leaf package stays
    free of any dependency on ``packages/storage`` — the API caller
    passes its real ``PredictionDiaryEntryRecord`` instances and Python
    duck-typing handles the rest.
    """

    forecast_id: str | None
    outcome_label_1d: str | None
    outcome_label_1w: str | None
    outcome_label_1m: str | None

# Labels — exposed as string constants so callers can compare without
# importing the enum-shape into UI layers.
OUTCOME_RIGHT: Final = "right"
OUTCOME_WRONG: Final = "wrong"
OUTCOME_INCONCLUSIVE: Final = "inconclusive"
OUTCOME_EARLY: Final = "early"
OUTCOME_NO_DATA: Final = "no_data"


# Tolerance band for ``inconclusive``: |realised return| <= this → inconclusive.
DEFAULT_INCONCLUSIVE_TOLERANCE_PCT: Final[Decimal] = Decimal("0.25")


@dataclass(frozen=True)
class HorizonEvaluation:
    realized_price: Decimal | None
    realized_return_pct: Decimal | None
    outcome_label: str


@dataclass(frozen=True)
class DiaryEvaluation:
    horizon_1d: HorizonEvaluation
    horizon_1w: HorizonEvaluation
    horizon_1m: HorizonEvaluation
    explanation_nl: str


def _compute_return_pct(issued_price: Decimal, realized_price: Decimal) -> Decimal:
    if issued_price <= 0:
        return Decimal("0")
    return ((realized_price - issued_price) / issued_price) * Decimal("100")


def _classify_horizon(
    *,
    issued_price: Decimal,
    issued_p10_price: Decimal,
    issued_p50_price: Decimal,
    issued_p90_price: Decimal,
    issued_prob_gain: Decimal,
    realized_price: Decimal | None,
    inconclusive_tolerance_pct: Decimal,
) -> HorizonEvaluation:
    if realized_price is None or realized_price <= 0:
        return HorizonEvaluation(
            realized_price=realized_price,
            realized_return_pct=None,
            outcome_label=OUTCOME_NO_DATA,
        )
    return_pct = _compute_return_pct(issued_price, realized_price)
    # 1) Inside the inconclusive band → inconclusive
    if abs(return_pct) <= inconclusive_tolerance_pct:
        return HorizonEvaluation(
            realized_price=realized_price,
            realized_return_pct=return_pct,
            outcome_label=OUTCOME_INCONCLUSIVE,
        )
    forecast_gain = issued_prob_gain > Decimal("0.5")
    realised_gain = return_pct > 0
    # 2) Direction missed → wrong
    if forecast_gain != realised_gain:
        return HorizonEvaluation(
            realized_price=realized_price,
            realized_return_pct=return_pct,
            outcome_label=OUTCOME_WRONG,
        )
    # 3) Direction matched. ``early`` when realised hasn't reached the
    # median forecast yet (direction right, magnitude undershoot); ``right``
    # once realised has reached or exceeded p50 in the expected direction.
    if forecast_gain:
        if realized_price >= issued_p50_price:
            label = OUTCOME_RIGHT
        else:
            label = OUTCOME_EARLY
    else:
        if realized_price <= issued_p50_price:
            label = OUTCOME_RIGHT
        else:
            label = OUTCOME_EARLY
    return HorizonEvaluation(
        realized_price=realized_price,
        realized_return_pct=return_pct,
        outcome_label=label,
    )


def evaluate_diary_outcomes(
    *,
    issued_price: Decimal,
    issued_p10_price: Decimal,
    issued_p50_price: Decimal,
    issued_p90_price: Decimal,
    issued_prob_gain: Decimal,
    realized_price_1d: Decimal | None,
    realized_price_1w: Decimal | None,
    realized_price_1m: Decimal | None,
    inconclusive_tolerance_pct: Decimal = DEFAULT_INCONCLUSIVE_TOLERANCE_PCT,
) -> DiaryEvaluation:
    """Evaluate the three locked horizons and return labelled outcomes.

    Every horizon is independent — a 1d horizon can be ``no_data`` while
    1w is ``right``. The caller decides which horizons to surface in the
    UI based on the per-horizon label.
    """

    horizon_1d = _classify_horizon(
        issued_price=issued_price,
        issued_p10_price=issued_p10_price,
        issued_p50_price=issued_p50_price,
        issued_p90_price=issued_p90_price,
        issued_prob_gain=issued_prob_gain,
        realized_price=realized_price_1d,
        inconclusive_tolerance_pct=inconclusive_tolerance_pct,
    )
    horizon_1w = _classify_horizon(
        issued_price=issued_price,
        issued_p10_price=issued_p10_price,
        issued_p50_price=issued_p50_price,
        issued_p90_price=issued_p90_price,
        issued_prob_gain=issued_prob_gain,
        realized_price=realized_price_1w,
        inconclusive_tolerance_pct=inconclusive_tolerance_pct,
    )
    horizon_1m = _classify_horizon(
        issued_price=issued_price,
        issued_p10_price=issued_p10_price,
        issued_p50_price=issued_p50_price,
        issued_p90_price=issued_p90_price,
        issued_prob_gain=issued_prob_gain,
        realized_price=realized_price_1m,
        inconclusive_tolerance_pct=inconclusive_tolerance_pct,
    )

    explanation_nl = (
        f"Outcome 1d={horizon_1d.outcome_label}, "
        f"1w={horizon_1w.outcome_label}, "
        f"1m={horizon_1m.outcome_label}. "
        "Deterministische evaluatie zonder AI-scoring."
    )

    return DiaryEvaluation(
        horizon_1d=horizon_1d,
        horizon_1w=horizon_1w,
        horizon_1m=horizon_1m,
        explanation_nl=explanation_nl,
    )


# ---- #5 — diary → live per-predictor Brier-style scores -----------------


# Brier-equivalent scoring per diary outcome label. The classical Brier
# score is mean squared error against the realised outcome; for our
# categorical outcome labels we use a deliberately simple mapping that
# preserves ordering: lower is better, ``right`` is 0, ``wrong`` is 1.
# Tunable in one place; the relative ordering is what the inverse-Brier
# ensemble weighting consumes.
_OUTCOME_TO_BRIER_EQUIVALENT: dict[str, Decimal] = {
    "right": Decimal("0.0"),
    "early": Decimal("0.4"),
    "inconclusive": Decimal("0.5"),
    "wrong": Decimal("1.0"),
}


def compute_live_brier_history_from_diary(
    *,
    diary_entries: Iterable[_DiaryEntryLike],
    forecast_model_by_id: Mapping[str, str],
    horizon_key: str = "outcome_label_1m",
) -> dict[str, Decimal]:
    """Per-predictor Brier-equivalent score from live diary outcomes.

    Drop-in replacement for the backtest-only ``brier_history`` that
    ``run_ensemble_forecast(weight_strategy="auto")`` already consumes:
    the keys are predictor ``model_code`` values (e.g. ``"baseline_gbm"``,
    ``"momentum"``, ``"qvm"``), the values are average Brier-equivalent
    scores in [0, 1] across all evaluated diary entries.

    Args:
        diary_entries: Iterable of ``PredictionDiaryEntryRecord``.
            ``no_data`` and ``None`` outcome labels are skipped — they
            contribute no signal.
        forecast_model_by_id: Mapping ``forecast_id → forecast.model_code``.
            Built once by the caller from the forecast repo.
        horizon_key: Which horizon's outcome to score
            (``outcome_label_1d``, ``outcome_label_1w``, or
            ``outcome_label_1m``). Default 1m matches the morning-chain
            cadence.

    Returns: ``{model_code: mean_brier_equivalent}``. Predictors with no
    scored entries are omitted so the existing equal-weight fallback
    applies.
    """

    sums: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    for entry in diary_entries:
        if entry.forecast_id is None:
            continue
        model_code = forecast_model_by_id.get(entry.forecast_id)
        if not model_code:
            continue
        label = getattr(entry, horizon_key, None)
        if label is None or label == "no_data":
            continue
        score = _OUTCOME_TO_BRIER_EQUIVALENT.get(label)
        if score is None:
            continue
        sums[model_code] = sums.get(model_code, Decimal("0")) + score
        counts[model_code] = counts.get(model_code, 0) + 1
    return {
        model: (sums[model] / Decimal(counts[model])).quantize(Decimal("0.000001"))
        for model in sums
    }
