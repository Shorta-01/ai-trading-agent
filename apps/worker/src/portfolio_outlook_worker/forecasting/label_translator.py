"""Task 130: deterministic Dutch label translator.

The label translator is pure Python with no AI. Same inputs always
produce same outputs. Six locked Dutch labels:

* ``Kopen``      — strong positive signal + position not blocked.
* ``Verminderen`` — weak negative signal + user holds the position.
* ``Verkopen``   — strong negative + high downside + user holds.
* ``Houden``     — user holds + no sell-side trigger fires.
* ``Bekijken``   — everything else when freshness is good.
* ``Geblokkeerd`` — data-quality issue; ``block_reason`` enum.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Literal

from portfolio_outlook_worker.forecasting.historical_bootstrap import (
    BootstrapForecastResult,
)

Freshness = Literal["fresh", "stale", "unavailable"]
ConfidenceLevel = Literal["Laag", "Gemiddeld", "Hoog"]
Label = Literal[
    "Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken", "Geblokkeerd"
]
BlockReason = Literal[
    "data_stale",
    "data_unavailable",
    "insufficient_history",
    "implausible_volatility",
    "not_held_for_sell_label",
]


# Thresholds locked by product brainstorm 2026-05-25 §Q4.
_KOPEN_PROB_POSITIVE_MIN = Decimal("0.65")
_KOPEN_PROB_LOSS_MAX = Decimal("0.15")
_VERMINDEREN_PROB_POSITIVE_MAX = Decimal("0.35")
_VERKOPEN_PROB_POSITIVE_MAX = Decimal("0.25")
_VERKOPEN_PROB_LOSS_MIN = Decimal("0.40")
_IMPLAUSIBLE_VOLATILITY_THRESHOLD = Decimal("0.50")  # annualized
_ZERO = Decimal("0")


@dataclass(frozen=True)
class LabelResult:
    label: Label
    block_reason: BlockReason | None = None


def translate_to_label(
    *,
    forecast: BootstrapForecastResult,
    user_holds_position: bool,
    freshness: Freshness,
    confidence: ConfidenceLevel,  # noqa: ARG001 — captured in caller's audit row
    history_closes_count: int,
) -> LabelResult:
    """Apply the locked label-translator rules.

    Args:
        forecast: the just-computed BootstrapForecastResult.
        user_holds_position: True if the user currently owns the asset.
        freshness: derived from market-data SLA at call time.
        confidence: derived from data-quality checks. Accepted for
            audit-completeness but not used in the label decision —
            the block_reason branches handle data quality.
        history_closes_count: number of EOD closes in the input window.
            Used by the `insufficient_history` block path.
    """

    # ---- block reasons trump every label rule ---------------------
    if freshness == "stale":
        return LabelResult(label="Geblokkeerd", block_reason="data_stale")
    if freshness == "unavailable":
        return LabelResult(
            label="Geblokkeerd", block_reason="data_unavailable"
        )
    if history_closes_count < 200:
        return LabelResult(
            label="Geblokkeerd", block_reason="insufficient_history"
        )
    if (
        forecast.expected_volatility_annualized
        > _IMPLAUSIBLE_VOLATILITY_THRESHOLD
    ):
        return LabelResult(
            label="Geblokkeerd", block_reason="implausible_volatility"
        )

    # ---- sell-side rules (require holding the position) -----------
    if user_holds_position:
        if (
            forecast.prob_positive <= _VERKOPEN_PROB_POSITIVE_MAX
            and forecast.prob_loss_gt_5pct >= _VERKOPEN_PROB_LOSS_MIN
        ):
            return LabelResult(label="Verkopen")
        if (
            forecast.prob_positive <= _VERMINDEREN_PROB_POSITIVE_MAX
            and forecast.p50_log_return < _ZERO
        ):
            return LabelResult(label="Verminderen")

    # ---- buy-side rule (no holding requirement) -------------------
    if (
        forecast.prob_positive >= _KOPEN_PROB_POSITIVE_MIN
        and forecast.p50_log_return > _ZERO
        and forecast.prob_loss_gt_5pct <= _KOPEN_PROB_LOSS_MAX
    ):
        return LabelResult(label="Kopen")

    # ---- residual cases -------------------------------------------
    if user_holds_position:
        return LabelResult(label="Houden")
    return LabelResult(label="Bekijken")


def derive_confidence(
    *,
    history_closes_count: int,
    gaps_in_last_60_days: int,
    expected_volatility_annualized: Decimal,
) -> ConfidenceLevel:
    """Locked confidence categorical from data-quality checks.

    * ``Hoog``: ≥252 closes + no gaps + volatility ≤30% annualized.
    * ``Gemiddeld``: 200-251 closes OR small gaps (≤2) OR moderate vol.
    * ``Laag``: anything borderline.
    """

    if (
        history_closes_count >= 252
        and gaps_in_last_60_days == 0
        and expected_volatility_annualized <= Decimal("0.30")
    ):
        return "Hoog"
    if history_closes_count >= 200 and gaps_in_last_60_days <= 2:
        return "Gemiddeld"
    return "Laag"


__all__ = [
    "BlockReason",
    "ConfidenceLevel",
    "Freshness",
    "Label",
    "LabelResult",
    "derive_confidence",
    "translate_to_label",
]
