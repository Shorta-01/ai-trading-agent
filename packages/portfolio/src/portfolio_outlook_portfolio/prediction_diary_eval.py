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

from dataclasses import dataclass
from decimal import Decimal
from typing import Final

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
