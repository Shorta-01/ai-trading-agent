"""V1.1 Slice 26 — predictor feedback loop helpers.

Two pure-Python helpers that turn the per-predictor Brier scores
produced by Slice 25's backtester into a usable feedback signal:

* :func:`compute_per_predictor_outcomes` — given an
  :class:`EnsembleResult` and a realised market outcome, emit one
  outcome row per surviving predictor. Each row carries the
  predictor's *issued* numbers + the realised return + a Brier-score
  cell and the diary outcome label, ready for persistence as a
  :class:`PredictionDiaryPredictorContributionRecord`.
* :func:`compute_inverse_brier_weights` — given a mapping
  ``{model_code: rolling_brier_score}``, produce a weighting dict
  for the ensemble combiner by ``1/brier``, clipped per-predictor
  to a band (default ``(0.05, 0.40)``), normalised to sum to 1.0.
  Falls back to equal-weight when the history is degenerate
  (missing data / zero-spread / all-equal).

Locked by §22.5 in `version-1-product-experience-locks.md`. The
auto-weighting strategy may down-weight a predictor but never
silence it: the lower clip is a non-negative floor so every V1
predictor keeps at least a small share even after a long bad run.
The morning chain never goes dark.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final

from .ensemble_combiner import EnsembleResult

# Outcome labels mirror the Prediction Diary set; the per-predictor
# table re-uses the same vocabulary so the leaderboard surface can
# show a consistent Dutch story.
OUTCOME_CORRECT: Final[str] = "correct"
OUTCOME_PARTIAL: Final[str] = "partial"
OUTCOME_WRONG: Final[str] = "wrong"
OUTCOME_NO_DATA: Final[str] = "no_data"


# Per-predictor clip band — floor 10%, ceiling 40% per the locked forecast
# engine (forecast-engine.md §3 + predictor-lifecycle.md §6 + ADR-0003): no
# single predictor dominates and no active predictor falls below the floor
# (below-floor signals push toward retirement, not silent zeroing).
DEFAULT_WEIGHT_CLIP_LOW: Final[Decimal] = Decimal("0.10")
DEFAULT_WEIGHT_CLIP_HIGH: Final[Decimal] = Decimal("0.40")


@dataclass(frozen=True)
class PerPredictorOutcome:
    """Output row of :func:`compute_per_predictor_outcomes`."""

    model_code: str
    model_version: str
    predicted_return_pct: Decimal
    predicted_prob_gain: Decimal
    predicted_direction: str
    realised_return_pct: Decimal | None
    realised_direction: str | None
    outcome_label: str
    brier_score: Decimal | None
    return_spread_pct: Decimal | None
    explanation_nl: str


def _realised_direction(return_pct: Decimal) -> str:
    """Mirror the locked direction-label thresholds (10% strong /
    2% slight) on the realised return."""

    if return_pct >= Decimal("10"):
        return "strong_up"
    if return_pct >= Decimal("2"):
        return "slight_up"
    if return_pct > Decimal("-2"):
        return "flat"
    if return_pct > Decimal("-10"):
        return "slight_down"
    return "strong_down"


def _direction_buckets(label: str) -> str:
    """Collapse the five-bucket direction label to ``up`` / ``flat`` /
    ``down`` for outcome-label scoring."""

    if label in {"strong_up", "slight_up"}:
        return "up"
    if label in {"strong_down", "slight_down"}:
        return "down"
    return "flat"


def _outcome_label(predicted: str, realised: str) -> str:
    """``correct`` when the buckets match exactly, ``partial`` when
    the predicted/realised are both up or both down but at a different
    strength, ``wrong`` otherwise."""

    pred_bucket = _direction_buckets(predicted)
    real_bucket = _direction_buckets(realised)
    if predicted == realised:
        return OUTCOME_CORRECT
    if pred_bucket == real_bucket:
        return OUTCOME_PARTIAL
    return OUTCOME_WRONG


def _brier(predicted_prob_gain: Decimal, realised_return_pct: Decimal) -> Decimal:
    """Single-fold Brier on prob_gain: ``(prob_gain - indicator)²``."""

    indicator = Decimal("1") if realised_return_pct > 0 else Decimal("0")
    diff = predicted_prob_gain - indicator
    return (diff * diff).quantize(Decimal("0.000001"))


def compute_per_predictor_outcomes(
    *,
    ensemble: EnsembleResult,
    realised_return_pct: Decimal | None,
    now: datetime | None = None,
) -> tuple[PerPredictorOutcome, ...]:
    """Emit one :class:`PerPredictorOutcome` per surviving predictor.

    Blocked predictors are skipped — they never participated in the
    ensemble and so don't contribute to the feedback signal.

    ``realised_return_pct`` is the realised market return over the
    same horizon the ensemble forecast targeted. When it's ``None``
    every outcome row stays at ``outcome_label="no_data"`` with
    ``brier_score=None`` so the feedback loop is invariant under
    insufficient horizon data.
    """

    _ = now if now is not None else datetime.now(UTC)
    outcomes: list[PerPredictorOutcome] = []
    for contribution in ensemble.contributions:
        prediction = contribution.prediction
        if realised_return_pct is None:
            outcomes.append(
                PerPredictorOutcome(
                    model_code=prediction.model_code,
                    model_version=prediction.model_version,
                    predicted_return_pct=prediction.expected_return_pct,
                    predicted_prob_gain=prediction.prob_gain,
                    predicted_direction=prediction.direction,
                    realised_return_pct=None,
                    realised_direction=None,
                    outcome_label=OUTCOME_NO_DATA,
                    brier_score=None,
                    return_spread_pct=None,
                    explanation_nl=(
                        f"{prediction.model_code}: nog geen gerealiseerd "
                        "rendement beschikbaar voor scoring."
                    ),
                )
            )
            continue
        realised_dir = _realised_direction(realised_return_pct)
        outcome = _outcome_label(prediction.direction, realised_dir)
        brier = _brier(prediction.prob_gain, realised_return_pct)
        spread = (prediction.expected_return_pct - realised_return_pct).quantize(
            Decimal("0.000001")
        )
        outcomes.append(
            PerPredictorOutcome(
                model_code=prediction.model_code,
                model_version=prediction.model_version,
                predicted_return_pct=prediction.expected_return_pct,
                predicted_prob_gain=prediction.prob_gain,
                predicted_direction=prediction.direction,
                realised_return_pct=realised_return_pct,
                realised_direction=realised_dir,
                outcome_label=outcome,
                brier_score=brier,
                return_spread_pct=spread,
                explanation_nl=(
                    f"{prediction.model_code}: voorspeld "
                    f"{float(prediction.expected_return_pct):.2f}% "
                    f"vs gerealiseerd {float(realised_return_pct):.2f}% "
                    f"({outcome}, brier {float(brier):.3f})."
                ),
            )
        )
    return tuple(outcomes)


def _clip(value: Decimal, low: Decimal, high: Decimal) -> Decimal:
    if value < low:
        return low
    if value > high:
        return high
    return value


def compute_inverse_brier_weights(
    history: Mapping[str, Decimal | float | None],
    *,
    clip: tuple[Decimal, Decimal] = (
        DEFAULT_WEIGHT_CLIP_LOW,
        DEFAULT_WEIGHT_CLIP_HIGH,
    ),
    fallback_codes: Iterable[str] = (),
) -> dict[str, Decimal]:
    """Produce per-predictor ensemble weights from a rolling Brier
    history.

    ``history`` maps a `model_code` → recent average Brier score.
    Weights are computed as ``1 / max(brier, ε)`` then clipped to
    ``clip`` per-predictor and re-normalised to sum to 1.0.

    Falls back to equal-weight on:
    * an empty / all-``None`` / all-zero history (no signal to lean on);
    * any predictor with an invalid score; or
    * a normalised set where every weight equals ``1 / N`` already.

    ``fallback_codes`` lets callers add codes that don't appear in the
    history (e.g. a new predictor that hasn't backtested yet). When
    used they're always equal-weighted with the rest of the surviving
    set.
    """

    clip_low, clip_high = clip
    if clip_low <= 0 or clip_high <= clip_low or clip_high > Decimal("1"):
        raise ValueError(
            "clip must satisfy 0 < clip_low < clip_high <= 1"
        )

    codes_from_history = [
        code
        for code, brier in history.items()
        if brier is not None and Decimal(str(brier)) > 0
    ]
    codes = list(dict.fromkeys([*codes_from_history, *fallback_codes]))
    if not codes:
        return {}

    # Inverse-Brier inputs. Predictors only in fallback_codes get the
    # historical mean Brier so they inherit a neutral starting weight.
    if codes_from_history:
        mean_brier = sum(
            Decimal(str(history[c])) for c in codes_from_history
        ) / Decimal(str(len(codes_from_history)))
    else:
        mean_brier = Decimal("0.25")  # neutral baseline

    raw_inverse: dict[str, Decimal] = {}
    for code in codes:
        if code in codes_from_history:
            brier = Decimal(str(history[code]))
        else:
            brier = mean_brier
        # Inverse-Brier; the higher the Brier the smaller the weight.
        raw_inverse[code] = Decimal("1") / brier

    total = sum(raw_inverse.values(), Decimal("0"))
    if total == 0:
        share = Decimal("1") / Decimal(str(len(codes)))
        return {code: share for code in codes}

    normalised = {code: raw / total for code, raw in raw_inverse.items()}
    final = _apply_clip_with_water_filling(
        normalised, clip_low=clip_low, clip_high=clip_high
    )
    # Six-decimal quantisation so the weights round predictably and
    # round-trip cleanly through Decimal arithmetic in the combiner.
    return {
        code: weight.quantize(Decimal("0.000001"))
        for code, weight in final.items()
    }


def _apply_clip_with_water_filling(
    weights: Mapping[str, Decimal],
    *,
    clip_low: Decimal,
    clip_high: Decimal,
    max_iterations: int = 20,
) -> dict[str, Decimal]:
    """Iteratively clip + re-distribute so every weight ends up in
    ``[clip_low, clip_high]`` and the set still sums to 1.0.

    Two-pass water-filling: first pin every predictor that exceeds
    ``clip_high`` and redistribute its surplus proportionally to the
    unpinned rest; once the upper-cap constraint is stable, do the
    same for predictors below ``clip_low``. The two passes are
    repeated until no further pin happens.

    Falls back to equal-weight when the bounds make the constraint
    infeasible (``N × clip_low > 1`` or ``N × clip_high < 1``).
    """

    codes = list(weights.keys())
    n = Decimal(str(len(codes)))
    if n == 0:
        return {}
    if clip_low * n > Decimal("1") or clip_high * n < Decimal("1"):
        return {code: Decimal("1") / n for code in codes}

    current = {code: Decimal(str(w)) for code, w in weights.items()}
    high_pinned: set[str] = set()
    low_pinned: set[str] = set()

    for _ in range(max_iterations):
        changed = False
        # ---- Upper cap pass ----
        for code, value in current.items():
            if code in high_pinned or code in low_pinned:
                continue
            if value > clip_high:
                current[code] = clip_high
                high_pinned.add(code)
                changed = True
        # Redistribute surplus among unpinned set.
        if high_pinned or low_pinned:
            pinned_total = sum(current[c] for c in high_pinned | low_pinned)
            unpinned = [c for c in codes if c not in high_pinned and c not in low_pinned]
            residual = Decimal("1") - pinned_total
            if unpinned:
                unpinned_total = sum(current[c] for c in unpinned)
                if unpinned_total > 0 and residual > 0:
                    for c in unpinned:
                        current[c] = residual * (current[c] / unpinned_total)
                else:
                    share = residual / Decimal(str(len(unpinned)))
                    for c in unpinned:
                        current[c] = share
        # ---- Lower floor pass ----
        for code, value in current.items():
            if code in high_pinned or code in low_pinned:
                continue
            if value < clip_low:
                current[code] = clip_low
                low_pinned.add(code)
                changed = True
        if high_pinned or low_pinned:
            pinned_total = sum(current[c] for c in high_pinned | low_pinned)
            unpinned = [c for c in codes if c not in high_pinned and c not in low_pinned]
            residual = Decimal("1") - pinned_total
            if unpinned:
                unpinned_total = sum(current[c] for c in unpinned)
                if unpinned_total > 0 and residual > 0:
                    for c in unpinned:
                        current[c] = residual * (current[c] / unpinned_total)
                else:
                    share = residual / Decimal(str(len(unpinned)))
                    for c in unpinned:
                        current[c] = share
        if not changed:
            break
    return current


__all__ = [
    "DEFAULT_WEIGHT_CLIP_HIGH",
    "DEFAULT_WEIGHT_CLIP_LOW",
    "OUTCOME_CORRECT",
    "OUTCOME_NO_DATA",
    "OUTCOME_PARTIAL",
    "OUTCOME_WRONG",
    "PerPredictorOutcome",
    "compute_inverse_brier_weights",
    "compute_per_predictor_outcomes",
]
