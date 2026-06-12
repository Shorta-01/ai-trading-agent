"""Analyst-revision momentum predictor (V1.2 §O).

Empirically the strongest signal at the 3-6 month horizon next to
price momentum: when sell-side analysts revise their earnings
estimates *up*, the stock tends to keep drifting up for 2-3 months
("post-earnings-announcement drift", Bernard & Thomas 1989; the
mechanism survives every replication). The mirror holds for
revisions *down*.

This predictor maps a composite revision score onto a horizon-scaled
lognormal distribution — same output shape as every other predictor
so the ensemble combiner doesn't need to know which model produced
the row. The composite weights:

* **3-month EPS revision** — weight 0.4 (most recent, strongest)
* **6-month EPS revision** — weight 0.3 (smoother, less reactive)
* **3-month target-price revision** — weight 0.3 (analyst price
  targets carry their own information separate from EPS)

A positive composite → drift bias *up*; negative → bias *down*.
The annualised drift is capped at ±25 % (same convention as
``MomentumPredictor`` and ``QvmFactorPredictor``) so a single
revision can't dominate the ensemble.

Confidence rises when the three components agree on sign and shrinks
when they disagree. Missing inputs are tolerated — the predictor
re-weights the remaining components and lowers confidence rather
than refusing.

Data source: this slice consumes a pre-built
``AnalystRevisionUniverse`` snapshot the way ``QvmFactorPredictor``
consumes ``UniverseFundamentals``. The daily-scan worker is where
the snapshot gets populated from EODHD's analyst-estimates endpoint
(out of scope for this slice).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Final

import numpy as np

from .baseline_forecast import DEFAULT_TRADING_DAYS_PER_YEAR
from .predictor_protocol import (
    BLOCKING_REASON_FLAT_HISTORY,
    BLOCKING_REASON_INSUFFICIENT_HISTORY,
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

MODEL_CODE: Final[str] = "analyst_revision_v1"
MODEL_VERSION: Final[str] = "v1.0.0"

# Minimum bars to ground the distribution width. Vol from the last
# 6 trading months ≈ 126 bars; we accept 100 to handle recent IPOs
# with three months of history but enough to compute a stable σ.
ANALYST_REVISION_MIN_BARS: Final[int] = 100

# Conservative drift cap. Same convention as MomentumPredictor +
# QvmFactorPredictor so a single revision can't dominate the
# ensemble.
MAX_ANNUAL_DRIFT_PCT: Final[float] = 25.0

# Clip individual revision ratios to ±100 %. A 200 %-up revision is
# almost always a stub-to-real-estimate jump (typically a name with
# nascent coverage), not a genuine bullish update — clipping keeps
# the signal numerically stable.
_REVISION_CLIP: Final[float] = 1.0

# Direction thresholds on the expected return % (matches the
# convention used by the rest of the predictor stack).
_DIRECTION_THRESHOLD_STRONG_PCT: Final[float] = 10.0
_DIRECTION_THRESHOLD_SLIGHT_PCT: Final[float] = 2.0

# Component weights — must sum to 1.0. The most-recent EPS revision
# carries the most weight because it incorporates the most recent
# earnings cycle information.
_WEIGHT_EPS_3M: Final[float] = 0.4
_WEIGHT_EPS_6M: Final[float] = 0.3
_WEIGHT_TARGET_3M: Final[float] = 0.3

# Locked blocking reason — surfaced when the predictor finds no
# analyst data for the requested symbol or the data is too thin
# to produce a signal.
BLOCKING_REASON_NO_ANALYST_DATA: Final[str] = "no_analyst_data"
BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE: Final[str] = "symbol_not_in_universe"


@dataclass(frozen=True)
class AnalystRevisionEntry:
    """One symbol's analyst-revision snapshot.

    All EPS / target-price values are point-in-time consensus
    estimates from the data provider. ``None`` is allowed: the
    composite gracefully re-weights around missing pieces and the
    confidence falls as a result.
    """

    symbol: str
    eps_current_estimate: Decimal | None = None
    eps_estimate_3m_ago: Decimal | None = None
    eps_estimate_6m_ago: Decimal | None = None
    target_price_current: Decimal | None = None
    target_price_3m_ago: Decimal | None = None


@dataclass(frozen=True)
class AnalystRevisionUniverse:
    """Bundle of analyst snapshots keyed by symbol."""

    entries: dict[str, AnalystRevisionEntry]


def _safe_revision_ratio(current: Decimal | None, past: Decimal | None) -> float | None:
    """Return ``(current - past) / |past|`` clipped to ``[-1, +1]``.

    ``None`` is returned when either input is missing or ``|past|``
    is too small to produce a stable ratio (treat as missing).
    """

    if current is None or past is None:
        return None
    p = float(past)
    if abs(p) < 1e-6:
        return None
    raw = (float(current) - p) / abs(p)
    return max(-_REVISION_CLIP, min(_REVISION_CLIP, raw))


def _composite_score(
    r_eps_3m: float | None,
    r_eps_6m: float | None,
    r_target_3m: float | None,
) -> tuple[float, float, int]:
    """Weighted-average the available revision ratios.

    Returns ``(composite, agreement_factor, n_components)``:

    * ``composite`` — weighted mean of the available components,
      with weights re-normalised over the present components.
    * ``agreement_factor`` — 1.0 when all present components have
      the same sign; falls to 0.4 when both directions are present;
      0.7 when mixed-with-flat. Drives the confidence score.
    * ``n_components`` — count of present components (0–3). Used by
      the caller to refuse when zero.
    """

    components: list[tuple[float, float]] = []
    if r_eps_3m is not None:
        components.append((r_eps_3m, _WEIGHT_EPS_3M))
    if r_eps_6m is not None:
        components.append((r_eps_6m, _WEIGHT_EPS_6M))
    if r_target_3m is not None:
        components.append((r_target_3m, _WEIGHT_TARGET_3M))

    n = len(components)
    if n == 0:
        return 0.0, 0.0, 0

    weight_sum = sum(w for _, w in components)
    composite = sum(v * w for v, w in components) / weight_sum

    # Agreement: count positive / negative components.
    pos = sum(1 for v, _ in components if v > 0.001)
    neg = sum(1 for v, _ in components if v < -0.001)
    if pos and neg:
        agreement = 0.4  # mixed directions — biggest penalty
    elif pos == n or neg == n:
        agreement = 1.0  # all agree
    else:
        agreement = 0.7  # some present, some neutral

    return composite, agreement, n


def _classify_direction(expected_return_pct: float) -> str:
    """Map an expected-return-% to a locked direction label."""

    if expected_return_pct >= _DIRECTION_THRESHOLD_STRONG_PCT:
        return DIRECTION_STRONG_UP
    if expected_return_pct >= _DIRECTION_THRESHOLD_SLIGHT_PCT:
        return DIRECTION_SLIGHT_UP
    if expected_return_pct <= -_DIRECTION_THRESHOLD_STRONG_PCT:
        return DIRECTION_STRONG_DOWN
    if expected_return_pct <= -_DIRECTION_THRESHOLD_SLIGHT_PCT:
        return DIRECTION_SLIGHT_DOWN
    return DIRECTION_FLAT


def _trailing_log_vol(closes: Sequence[float]) -> float:
    """Annualised volatility from the last 126 closes (6 months)."""

    tail = list(closes[-min(126, len(closes)):])
    if len(tail) < 2:
        return 0.0
    arr = np.asarray(tail, dtype=np.float64)
    log_returns = np.log(arr[1:] / arr[:-1])
    if log_returns.size < 2:
        return 0.0
    daily_sigma = float(np.std(log_returns, ddof=1))
    return daily_sigma * math.sqrt(DEFAULT_TRADING_DAYS_PER_YEAR)


def _build_lognormal_distribution(
    *,
    current_price: Decimal,
    drift_horizon: float,
    sigma_horizon: float,
    horizon_trading_days: int,
) -> tuple[Decimal, Decimal, Decimal, Decimal]:
    """Return ``(p10, p50, p90, prob_gain)`` for the lognormal."""

    if sigma_horizon <= 0.0:
        # Degenerate (flat) — distribution collapses to current.
        return (current_price, current_price, current_price, Decimal("0.50"))
    price_f = float(current_price)
    # Lognormal: ln(S_T/S_0) ~ N(drift - sigma²/2, sigma²)
    mu = drift_horizon - 0.5 * sigma_horizon * sigma_horizon
    p10_log = mu - 1.2816 * sigma_horizon
    p50_log = mu
    p90_log = mu + 1.2816 * sigma_horizon
    p10 = Decimal(repr(price_f * math.exp(p10_log)))
    p50 = Decimal(repr(price_f * math.exp(p50_log)))
    p90 = Decimal(repr(price_f * math.exp(p90_log)))
    # P(S_T > S_0) = Φ(mu / sigma) under the lognormal.
    z = mu / sigma_horizon
    prob_gain = Decimal(repr(0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))))
    return p10, p50, p90, prob_gain


class AnalystRevisionPredictor:
    """Predictor implementing the locked ``PredictorProtocol``.

    The universe is injected so the daily-scan worker can pre-build
    it once per cycle and re-use it across every candidate.
    ``predict()`` is pure: same inputs → same output.
    """

    def __init__(self, universe: AnalystRevisionUniverse | None = None):
        self._universe = universe

    @property
    def model_code(self) -> str:
        return MODEL_CODE

    @property
    def model_version(self) -> str:
        return MODEL_VERSION

    def predict(self, inputs: PredictorInputs) -> PredictionDistribution:
        # Cheap input validation first — same pattern as every other
        # predictor in the family.
        if inputs.current_price <= 0:
            return _blocked(
                inputs, BLOCKING_REASON_INVALID_CURRENT_PRICE
            )
        if inputs.horizon_trading_days <= 0:
            return _blocked(inputs, BLOCKING_REASON_INVALID_HORIZON)
        if len(inputs.historical_bars) < ANALYST_REVISION_MIN_BARS:
            return _blocked(inputs, BLOCKING_REASON_INSUFFICIENT_HISTORY)

        symbol = inputs.asset_metadata.get("symbol", "").strip()
        if self._universe is None or not symbol:
            return _blocked(inputs, BLOCKING_REASON_NO_ANALYST_DATA)
        entry = self._universe.entries.get(symbol)
        if entry is None:
            return _blocked(inputs, BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE)

        r_eps_3m = _safe_revision_ratio(
            entry.eps_current_estimate, entry.eps_estimate_3m_ago
        )
        r_eps_6m = _safe_revision_ratio(
            entry.eps_current_estimate, entry.eps_estimate_6m_ago
        )
        r_target_3m = _safe_revision_ratio(
            entry.target_price_current, entry.target_price_3m_ago
        )
        composite, agreement, n_components = _composite_score(
            r_eps_3m, r_eps_6m, r_target_3m
        )
        if n_components == 0:
            return _blocked(inputs, BLOCKING_REASON_NO_ANALYST_DATA)

        # Annualised drift = composite × MAX_ANNUAL_DRIFT_PCT.
        annual_drift_pct = MAX_ANNUAL_DRIFT_PCT * composite
        annual_drift_log = annual_drift_pct / 100.0
        horizon_years = inputs.horizon_trading_days / float(
            DEFAULT_TRADING_DAYS_PER_YEAR
        )
        drift_horizon = annual_drift_log * horizon_years

        closes = [float(bar.close_price) for bar in inputs.historical_bars]
        if any(c <= 0.0 for c in closes):
            return _blocked(inputs, BLOCKING_REASON_FLAT_HISTORY)
        sigma_annual = _trailing_log_vol(closes)
        if sigma_annual <= 0.0:
            return _blocked(inputs, BLOCKING_REASON_FLAT_HISTORY)
        sigma_horizon = sigma_annual * math.sqrt(horizon_years)

        p10, p50, p90, prob_gain = _build_lognormal_distribution(
            current_price=inputs.current_price,
            drift_horizon=drift_horizon,
            sigma_horizon=sigma_horizon,
            horizon_trading_days=inputs.horizon_trading_days,
        )

        # Expected return at the median (what the UI displays).
        if inputs.current_price > 0:
            expected_return_pct_f = (
                (float(p50) - float(inputs.current_price))
                / float(inputs.current_price)
                * 100.0
            )
        else:
            expected_return_pct_f = 0.0
        expected_return_pct = Decimal(repr(round(expected_return_pct_f, 4)))

        # Direction follows the *drift* signal magnitude, not the
        # median price-change. In a lognormal world the median can
        # be flat even with a meaningful positive drift because of
        # the ``-σ²/2`` adjustment; using drift_horizon directly
        # classifies the signal honestly.
        drift_horizon_pct = drift_horizon * 100.0
        direction = _classify_direction(drift_horizon_pct)
        prob_loss = Decimal("1") - prob_gain

        # Confidence: agreement × component coverage × base.
        # With 3/3 components agreeing → 0.85; with 1 component → 0.40.
        coverage = n_components / 3.0
        confidence_f = max(0.30, min(0.90, 0.30 + 0.55 * agreement * coverage))
        confidence_score = Decimal(repr(round(confidence_f, 4)))

        explanation = (
            f"Analist-revisie samengestelde score {composite:+.2f} "
            f"(EPS 3m={r_eps_3m if r_eps_3m is not None else 'n/a'}, "
            f"EPS 6m={r_eps_6m if r_eps_6m is not None else 'n/a'}, "
            f"target 3m={r_target_3m if r_target_3m is not None else 'n/a'}). "
            f"Implied jaarlijkse drift {annual_drift_pct:+.2f} %."
        )

        return PredictionDistribution(
            model_code=MODEL_CODE,
            model_version=MODEL_VERSION,
            horizon_trading_days=inputs.horizon_trading_days,
            current_price=inputs.current_price,
            p10_price=p10,
            p50_price=p50,
            p90_price=p90,
            prob_gain=prob_gain,
            prob_loss=prob_loss,
            expected_return_pct=expected_return_pct,
            direction=direction,
            confidence_score=confidence_score,
            status=STATUS_READY,
            blocking_reason=None,
            explanation_nl=explanation,
        )


def _blocked(inputs: PredictorInputs, reason: str) -> PredictionDistribution:
    """Build a quarantine record with the locked blocked-row shape."""

    return PredictionDistribution(
        model_code=MODEL_CODE,
        model_version=MODEL_VERSION,
        horizon_trading_days=max(inputs.horizon_trading_days, 1),
        current_price=inputs.current_price if inputs.current_price > 0 else Decimal("1"),
        p10_price=Decimal("0"),
        p50_price=Decimal("0"),
        p90_price=Decimal("0"),
        prob_gain=Decimal("0"),
        prob_loss=Decimal("0"),
        expected_return_pct=Decimal("0"),
        direction=DIRECTION_FLAT,
        confidence_score=Decimal("0"),
        status=STATUS_BLOCKED,
        blocking_reason=reason,
        explanation_nl="Analist-revisie predictor heeft onvoldoende invoer.",
    )


__all__ = [
    "ANALYST_REVISION_MIN_BARS",
    "BLOCKING_REASON_NO_ANALYST_DATA",
    "BLOCKING_REASON_SYMBOL_NOT_IN_UNIVERSE",
    "MAX_ANNUAL_DRIFT_PCT",
    "MODEL_CODE",
    "MODEL_VERSION",
    "AnalystRevisionEntry",
    "AnalystRevisionPredictor",
    "AnalystRevisionUniverse",
]
