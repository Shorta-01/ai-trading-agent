"""Walk-forward predictor backtester (V1.1 Slice 25).

Pure-Python (numpy-backed) harness that scores any
:class:`PredictorProtocol` on its own historical accuracy. The
scoring artefact is :class:`BacktestWindowScore`; rolling Brier-score
aggregations feed the Slice 26 auto-weighting strategy on the
ensemble combiner.

Locked by §22 in `version-1-product-experience-locks.md`. The
backtest never authorises an order — its purpose is to surface
*which* predictors actually work over the recent window so the
operator can read a leaderboard and the ensemble can up-weight the
accurate predictors automatically.

Design notes
------------
- **Walk-forward, no look-ahead**: each fold trains/predicts on
  ``bars[start:end]`` and is scored against ``bars[end:end+horizon]``.
  The harness never lets a fold's predictor see the future.
- **Brier score**: mean ``(predicted_prob_gain - realised_indicator)²``
  across folds, where ``realised_indicator = 1`` if the realised
  end-of-horizon return was positive, ``0`` otherwise. Lower is
  better; 0.25 is the score of a constant 50/50 predictor.
- **Hit-rate**: share of folds where the predicted direction
  category and the realised category match. Direction is the
  locked five-bucket label set; we collapse `slight_up` /
  `strong_up` to "up" and the mirrored downs to "down" for
  scoring so a slightly-off direction call still earns credit.
- **Sharpe-ratio**: mean realised-return ÷ standard deviation of
  realised returns across folds (unitless; not annualised).
- Failure handling: a blocked predict at a fold is skipped silently
  (it counts as zero folds for that predictor). When ``< 2`` folds
  fit, the metrics return ``None`` rather than fake values.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
from uuid import uuid4

import numpy as np

from .baseline_forecast import HistoricalBar
from .predictor_protocol import (
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_READY,
    BacktestWindowScore,
    PredictorInputs,
    PredictorProtocol,
)

DEFAULT_WINDOW_DAYS: Final[int] = 252  # ~1 trading year
DEFAULT_HORIZON_DAYS: Final[int] = 21  # ~1 trading month
DEFAULT_STEP_DAYS: Final[int] = 5  # one fold per trading week
MIN_FOLDS_FOR_METRICS: Final[int] = 2

# Scoring constants — see module docstring.
_UP_DIRECTIONS = frozenset({DIRECTION_SLIGHT_UP, DIRECTION_STRONG_UP})
_DOWN_DIRECTIONS = frozenset({DIRECTION_SLIGHT_DOWN, DIRECTION_STRONG_DOWN})


@dataclass(frozen=True)
class FoldOutcome:
    """One walk-forward fold's prediction + realisation."""

    fold_index: int
    bars_used: int
    predicted_prob_gain: float
    predicted_direction: str
    predicted_return_pct: float
    realised_return_pct: float
    realised_indicator: int  # 1 if realised return > 0 else 0
    realised_direction: str
    direction_match: bool


def _realised_direction(return_pct: float) -> str:
    """Mirror the locked direction-label thresholds (10% strong /
    2% slight). The same thresholds the predictors use for their
    *predicted* direction, applied to the *realised* return."""

    if return_pct >= 10.0:
        return DIRECTION_STRONG_UP
    if return_pct >= 2.0:
        return DIRECTION_SLIGHT_UP
    if return_pct > -2.0:
        return DIRECTION_FLAT
    if return_pct > -10.0:
        return DIRECTION_SLIGHT_DOWN
    return DIRECTION_STRONG_DOWN


def _direction_match(predicted: str, realised: str) -> bool:
    """Up-vs-up and down-vs-down both count as a match. Flat-vs-flat
    counts as a match. Sign mismatches don't."""

    if predicted == realised:
        return True
    if predicted in _UP_DIRECTIONS and realised in _UP_DIRECTIONS:
        return True
    if predicted in _DOWN_DIRECTIONS and realised in _DOWN_DIRECTIONS:
        return True
    return False


def walk_forward_backtest(
    predictor: PredictorProtocol,
    bars: Sequence[HistoricalBar],
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    horizon_trading_days: int = DEFAULT_HORIZON_DAYS,
    step_days: int = DEFAULT_STEP_DAYS,
    asset_metadata: dict[str, str] | None = None,
) -> tuple[FoldOutcome, ...]:
    """Slide a ``window_days``-wide fitting/prediction window across
    ``bars`` and score each fold against the realised
    ``horizon_trading_days`` outcome.

    Returns the per-fold outcomes. ``walk_forward_score(...)``
    aggregates them into a :class:`BacktestWindowScore`.

    Raises ``ValueError`` only for non-positive ``window_days`` /
    ``horizon_trading_days`` / ``step_days``; everything else
    (insufficient bars, blocked predict, flat history) returns an
    empty tuple so the caller can surface a ``skipped`` row rather
    than crashing.
    """

    if window_days <= 0:
        raise ValueError("window_days must be positive")
    if horizon_trading_days <= 0:
        raise ValueError("horizon_trading_days must be positive")
    if step_days <= 0:
        raise ValueError("step_days must be positive")
    if len(bars) < window_days + horizon_trading_days + 1:
        return ()

    metadata = dict(asset_metadata) if asset_metadata else {}
    outcomes: list[FoldOutcome] = []
    last_fold_end = len(bars) - horizon_trading_days
    fold_index = 0

    for end in range(window_days, last_fold_end + 1, step_days):
        window_bars = bars[end - window_days : end]
        current_price = window_bars[-1].close_price
        try:
            prediction = predictor.predict(
                PredictorInputs(
                    historical_bars=window_bars,
                    current_price=current_price,
                    horizon_trading_days=horizon_trading_days,
                    asset_metadata=metadata,
                )
            )
        except Exception:  # noqa: BLE001 — fold-level boundary catch
            continue
        if prediction.status != STATUS_READY:
            continue

        future_index = end + horizon_trading_days - 1
        if future_index >= len(bars):
            break  # not enough data to score this fold
        realised_close = float(bars[future_index].close_price)
        start_close = float(current_price)
        if start_close <= 0:
            continue
        realised_return_pct = (realised_close / start_close - 1.0) * 100.0
        realised_direction = _realised_direction(realised_return_pct)
        outcomes.append(
            FoldOutcome(
                fold_index=fold_index,
                bars_used=len(window_bars),
                predicted_prob_gain=float(prediction.prob_gain),
                predicted_direction=prediction.direction,
                predicted_return_pct=float(prediction.expected_return_pct),
                realised_return_pct=realised_return_pct,
                realised_indicator=1 if realised_return_pct > 0 else 0,
                realised_direction=realised_direction,
                direction_match=_direction_match(
                    prediction.direction, realised_direction
                ),
            )
        )
        fold_index += 1

    return tuple(outcomes)


def aggregate_window_score(
    *,
    predictor: PredictorProtocol,
    outcomes: Sequence[FoldOutcome],
    window_days: int,
) -> BacktestWindowScore:
    """Aggregate per-fold outcomes into a :class:`BacktestWindowScore`.

    With fewer than :data:`MIN_FOLDS_FOR_METRICS` folds the metrics
    return ``None`` (we'd rather skip than fake them).
    """

    bars_used = max((fold.bars_used for fold in outcomes), default=0)
    if len(outcomes) < MIN_FOLDS_FOR_METRICS:
        return BacktestWindowScore(
            model_code=predictor.model_code,
            model_version=predictor.model_version,
            window_days=window_days,
            bars_used=bars_used,
            brier_score=None,
            hit_rate=None,
            sharpe_ratio=None,
            explanation_nl=(
                f"Onvoldoende folds ({len(outcomes)}) voor "
                f"{predictor.model_code} op {window_days}d-venster."
            ),
        )

    prob_gain = np.asarray([fold.predicted_prob_gain for fold in outcomes])
    indicators = np.asarray(
        [fold.realised_indicator for fold in outcomes], dtype=np.float64
    )
    brier_score = float(np.mean((prob_gain - indicators) ** 2))

    matches = np.asarray(
        [1.0 if fold.direction_match else 0.0 for fold in outcomes]
    )
    hit_rate = float(matches.mean())

    realised = np.asarray([fold.realised_return_pct for fold in outcomes])
    if realised.size < 2 or float(realised.std(ddof=1)) == 0.0:
        sharpe_ratio: float | None = None
    else:
        sharpe_ratio = float(realised.mean() / realised.std(ddof=1))

    explanation = (
        f"Walk-forward: {len(outcomes)} folds, {window_days}d-venster, "
        f"Brier {brier_score:.3f}, hit {hit_rate:.0%}"
        + (f", Sharpe {sharpe_ratio:.2f}" if sharpe_ratio is not None else "")
        + f" ({predictor.model_code})."
    )

    return BacktestWindowScore(
        model_code=predictor.model_code,
        model_version=predictor.model_version,
        window_days=window_days,
        bars_used=bars_used,
        brier_score=brier_score,
        hit_rate=hit_rate,
        sharpe_ratio=sharpe_ratio,
        explanation_nl=explanation,
    )


def walk_forward_score(
    predictor: PredictorProtocol,
    bars: Sequence[HistoricalBar],
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    horizon_trading_days: int = DEFAULT_HORIZON_DAYS,
    step_days: int = DEFAULT_STEP_DAYS,
    asset_metadata: dict[str, str] | None = None,
) -> BacktestWindowScore:
    """End-to-end walk-forward backtest + aggregation."""

    outcomes = walk_forward_backtest(
        predictor,
        bars,
        window_days=window_days,
        horizon_trading_days=horizon_trading_days,
        step_days=step_days,
        asset_metadata=asset_metadata,
    )
    return aggregate_window_score(
        predictor=predictor,
        outcomes=outcomes,
        window_days=window_days,
    )


@dataclass(frozen=True)
class BacktestPersistenceInputs:
    """Inputs the orchestrator hands to :func:`run_predictor_backtest`."""

    run_id: str
    asset_symbol: str
    started_at: datetime


@dataclass(frozen=True)
class BacktestPersistenceOutputs:
    """Outputs the orchestrator returns from
    :func:`run_predictor_backtest` — both the structured score and
    the audit-row fields ready for persistence."""

    score: BacktestWindowScore
    status: str
    blocking_reason: str | None
    finished_at: datetime


def run_predictor_backtest(
    predictor: PredictorProtocol,
    bars: Sequence[HistoricalBar],
    *,
    window_days: int = DEFAULT_WINDOW_DAYS,
    horizon_trading_days: int = DEFAULT_HORIZON_DAYS,
    step_days: int = DEFAULT_STEP_DAYS,
    asset_metadata: dict[str, str] | None = None,
) -> BacktestPersistenceOutputs:
    """Run one backtest and surface the audit shape.

    ``status`` is ``"succeeded"`` when metrics are present,
    ``"skipped"`` when insufficient folds (no exception was raised,
    just not enough data). Failures inside :func:`walk_forward_backtest`
    are caught at the fold boundary; this top-level call never
    raises.
    """

    score = walk_forward_score(
        predictor,
        bars,
        window_days=window_days,
        horizon_trading_days=horizon_trading_days,
        step_days=step_days,
        asset_metadata=asset_metadata,
    )
    finished_at = datetime.now(UTC)
    if score.brier_score is None or score.hit_rate is None:
        return BacktestPersistenceOutputs(
            score=score,
            status="skipped",
            blocking_reason="insufficient_folds",
            finished_at=finished_at,
        )
    return BacktestPersistenceOutputs(
        score=score,
        status="succeeded",
        blocking_reason=None,
        finished_at=finished_at,
    )


def new_backtest_run_id() -> str:
    """Stable id-helper so tests + the orchestrator agree on shape."""

    return f"bt_{uuid4().hex}"


def backtest_window_score_for_predictor(
    predictor: PredictorProtocol,
    inputs: PredictorInputs,
    *,
    window_days: int,
    step_days: int = DEFAULT_STEP_DAYS,
) -> BacktestWindowScore:
    """Helper for :class:`PredictorResearchProtocol` implementations.

    Lets each V1 predictor wire ``backtest_window_score(...)`` as a
    one-liner: pull the bars + horizon from the ``PredictorInputs``
    and hand the call to the shared walk-forward harness. Predictors
    don't need to know anything about pandas/numpy internals.
    """

    horizon = inputs.horizon_trading_days
    if horizon <= 0:
        return BacktestWindowScore(
            model_code=predictor.model_code,
            model_version=predictor.model_version,
            window_days=window_days,
            bars_used=0,
            brier_score=None,
            hit_rate=None,
            sharpe_ratio=None,
            explanation_nl=(
                f"Backtest geblokkeerd: ongeldige horizon {horizon}d "
                f"voor {predictor.model_code}."
            ),
        )
    return walk_forward_score(
        predictor,
        list(inputs.historical_bars),
        window_days=window_days,
        horizon_trading_days=horizon,
        step_days=step_days,
        asset_metadata=dict(inputs.asset_metadata),
    )


__all__ = [
    "DEFAULT_HORIZON_DAYS",
    "DEFAULT_STEP_DAYS",
    "DEFAULT_WINDOW_DAYS",
    "MIN_FOLDS_FOR_METRICS",
    "BacktestPersistenceInputs",
    "BacktestPersistenceOutputs",
    "FoldOutcome",
    "aggregate_window_score",
    "backtest_window_score_for_predictor",
    "new_backtest_run_id",
    "run_predictor_backtest",
    "walk_forward_backtest",
    "walk_forward_score",
]
