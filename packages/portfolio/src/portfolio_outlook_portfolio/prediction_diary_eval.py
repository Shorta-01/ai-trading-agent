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
from datetime import datetime
from decimal import Decimal
from typing import Final, Protocol, runtime_checkable


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


@runtime_checkable
class _ContributionLike(Protocol):
    """Subset of ``PredictionDiaryPredictorContributionRecord`` we read.

    Tests only need to mock these four fields, not the whole record.
    Decorated ``@runtime_checkable`` so structural matching with the
    concrete storage record works across module boundaries under mypy.
    """

    model_code: str
    brier_score: Decimal | None
    realised_return_pct: Decimal | None
    created_at: datetime


def compute_brier_history_from_contributions(
    *,
    contributions: Iterable[_ContributionLike],
    cutoff_at: datetime | None = None,
    min_sample_size: int = 5,
) -> dict[str, Decimal]:
    """Per-predictor mean of stored *true* Brier scores (V1.2 §D).

    Drop-in replacement for :func:`compute_live_brier_history_from_diary`
    that reads ``(prob_gain − indicator)²`` directly from the
    ``prediction_diary_predictor_contributions`` rows instead of the
    crude four-bucket outcome-label mapping. The contribution table
    already stores these for every per-predictor outcome — the previous
    helper was discarding information already on disk.

    Why this matters: the outcome-label mapping treats every "wrong"
    contribution as Brier = 1.0 and every "right" as 0.0, collapsing
    the full continuous resolution of ``(prob_gain − indicator)²``. A
    predictor that issued prob_gain = 0.51 and was right scores the
    same as one that issued prob_gain = 0.99 and was right — both 0.0
    in the bucket world, but 0.24 vs 0.0001 in true Brier. Auto-weights
    built from the crude scores can't distinguish lucky from confident.

    Args:
        contributions: Iterable of contribution records. Rows without a
            stored ``brier_score`` (no realised outcome yet, or row
            written before the brier_score column existed) are skipped
            silently — they contribute no signal.
        cutoff_at: When provided, only contributions with
            ``created_at >= cutoff_at`` are scored. Use for "last 90
            days" rolling windows; ``None`` means "all rows in the
            iterable".
        min_sample_size: Predictors with fewer than this many scored
            contributions are *omitted* from the result entirely (not
            zeroed out). The caller's equal-weight fallback then
            applies, which is the safe choice: weighting a predictor by
            the inverse of an unstable mean is worse than just averaging
            it equally with the others.

    Returns: ``{model_code: mean_brier_score}`` with each value in
    ``[0, 1]``, quantised to six decimals for repository round-trip
    parity. Predictors below the sample-size floor are omitted.
    """

    sums: dict[str, Decimal] = {}
    counts: dict[str, int] = {}
    for contribution in contributions:
        if cutoff_at is not None and contribution.created_at < cutoff_at:
            continue
        if contribution.brier_score is None:
            continue
        if contribution.realised_return_pct is None:
            # No realised outcome → the brier_score (if any) was
            # written defensively; skip rather than score against an
            # absent ground truth.
            continue
        model_code = contribution.model_code
        sums[model_code] = sums.get(model_code, Decimal("0")) + contribution.brier_score
        counts[model_code] = counts.get(model_code, 0) + 1
    return {
        model: (sums[model] / Decimal(counts[model])).quantize(Decimal("0.000001"))
        for model in sums
        if counts[model] >= min_sample_size
    }
