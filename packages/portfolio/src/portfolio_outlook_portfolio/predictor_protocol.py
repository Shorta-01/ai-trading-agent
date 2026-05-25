"""Predictor boundary (Slice 14).

Locked in `version-1-product-experience-locks.md §21.4`. V1 launches
with five predictors that all implement the same shape:

* :class:`GbmPredictor` (existing baseline lognormal GBM)
* :class:`MomentumPredictor` (12-1 + time-series momentum)
* Mean-reversion (Slice 15)
* QVM factor (Slice 16)
* AI foundation TS model (Slice 18)

The combiner (Slice 15) takes a list of :class:`PredictionDistribution`
results from each predictor and picks the action label by deterministic
rule — no single predictor decides.

This module is pure Python: the protocol carries no I/O, no provider
factories, no datetime.now(). Predictors must be deterministic given
the same inputs.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from .baseline_forecast import HistoricalBar

# Direction labels are intentionally narrow — they classify the
# distribution, not the action. The translator in Slice 4 maps direction
# + confidence + held-state to the locked Dutch action label set.
DIRECTION_STRONG_UP = "strong_up"
DIRECTION_SLIGHT_UP = "slight_up"
DIRECTION_FLAT = "flat"
DIRECTION_SLIGHT_DOWN = "slight_down"
DIRECTION_STRONG_DOWN = "strong_down"

# Predictor statuses. ``ready`` means the prediction can be combined;
# ``blocked`` means the input chain was incomplete and the predictor
# returned a quarantine record. The combiner ignores blocked predictors
# but logs them in the Diary.
STATUS_READY = "ready"
STATUS_BLOCKED = "blocked"

# Blocking reasons re-used across predictors for stable audit codes.
BLOCKING_REASON_INVALID_CURRENT_PRICE = "invalid_current_price"
BLOCKING_REASON_INSUFFICIENT_HISTORY = "insufficient_history"
BLOCKING_REASON_INVALID_HORIZON = "invalid_horizon"
BLOCKING_REASON_FLAT_HISTORY = "flat_history"


@dataclass(frozen=True)
class PredictorInputs:
    """The locked input contract for every predictor.

    ``historical_bars`` is the EOD series. ``current_price`` is the
    market price as of the snapshot. ``horizon_trading_days`` is the
    forecast horizon. ``asset_metadata`` is a free-form mapping (e.g.
    ``{"symbol": "AAPL", "sector": "Technology"}``) that some predictors
    may consult; the combiner ignores it.
    """

    historical_bars: Sequence[HistoricalBar]
    current_price: Decimal
    horizon_trading_days: int
    asset_metadata: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class PredictionDistribution:
    """The locked output contract for every predictor.

    All fields are Decimal-only money math; AI predictors must produce
    this exact shape so the combiner can treat every contribution
    identically.
    """

    model_code: str
    model_version: str
    horizon_trading_days: int
    current_price: Decimal
    p10_price: Decimal
    p50_price: Decimal
    p90_price: Decimal
    prob_gain: Decimal
    prob_loss: Decimal
    expected_return_pct: Decimal
    direction: str
    confidence_score: Decimal
    status: str
    blocking_reason: str | None = None
    explanation_nl: str = ""

    def __post_init__(self) -> None:
        if not self.model_code.strip():
            raise ValueError("model_code must be non-empty")
        if not self.model_version.strip():
            raise ValueError("model_version must be non-empty")
        if self.horizon_trading_days <= 0:
            raise ValueError("horizon_trading_days must be positive")
        if self.status not in {STATUS_READY, STATUS_BLOCKED}:
            raise ValueError(
                f"status must be ready/blocked, got {self.status!r}"
            )
        if self.direction not in {
            DIRECTION_STRONG_UP,
            DIRECTION_SLIGHT_UP,
            DIRECTION_FLAT,
            DIRECTION_SLIGHT_DOWN,
            DIRECTION_STRONG_DOWN,
        }:
            raise ValueError(f"direction is not a locked label: {self.direction!r}")


class PredictorProtocol(Protocol):
    """Every V1 predictor implements this."""

    @property
    def model_code(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    def predict(self, inputs: PredictorInputs) -> PredictionDistribution: ...


@dataclass(frozen=True)
class BacktestWindowScore:
    """One predictor's score over a single backtest window.

    Slice 25 (backtesting framework) fills these from a pandas-based
    walk-forward harness; Slice 26 (feedback loop) aggregates them
    into the inverse-Brier-weighting strategy on the ensemble
    combiner. Score fields are ``None`` when the window had too
    little data for the corresponding metric.
    """

    model_code: str
    model_version: str
    window_days: int
    bars_used: int
    brier_score: float | None
    hit_rate: float | None
    sharpe_ratio: float | None
    explanation_nl: str = ""


class PredictorResearchProtocol(Protocol):
    """V1.1 extension. Optional research methods every predictor MAY
    implement. The morning-chain combiner uses only the
    :class:`PredictorProtocol` interface; the research methods are
    consumed by the backtesting framework (Slice 25) and the
    feedback loop (Slice 26).

    Predictors that don't implement the research methods stay as
    plain :class:`PredictorProtocol`; the backtester reports
    ``research_protocol_not_implemented`` for those rows so the
    operator can tell at a glance which predictors carry walk-forward
    backtest support.
    """

    @property
    def model_code(self) -> str: ...

    @property
    def model_version(self) -> str: ...

    def predict(self, inputs: PredictorInputs) -> PredictionDistribution: ...

    def backtest_window_score(
        self,
        inputs: PredictorInputs,
        *,
        window_days: int,
    ) -> BacktestWindowScore: ...


__all__ = [
    "DIRECTION_STRONG_UP",
    "DIRECTION_SLIGHT_UP",
    "DIRECTION_FLAT",
    "DIRECTION_SLIGHT_DOWN",
    "DIRECTION_STRONG_DOWN",
    "STATUS_READY",
    "STATUS_BLOCKED",
    "BLOCKING_REASON_INVALID_CURRENT_PRICE",
    "BLOCKING_REASON_INSUFFICIENT_HISTORY",
    "BLOCKING_REASON_INVALID_HORIZON",
    "BLOCKING_REASON_FLAT_HISTORY",
    "BacktestWindowScore",
    "PredictorInputs",
    "PredictionDistribution",
    "PredictorProtocol",
    "PredictorResearchProtocol",
]
