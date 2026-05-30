"""GBM predictor that implements :class:`PredictorProtocol` (Slice 14).

Thin wrapper around the existing :func:`compute_baseline_forecast`. The
math is unchanged; this module only adapts the output shape so the
ensemble combiner can treat GBM as one predictor among five.
"""

from __future__ import annotations

from .baseline_forecast import (
    DEFAULT_REGIME_SHIFT_THRESHOLD_PCT,
    DEFAULT_SHARPE_SLIGHT_THRESHOLD,
    DEFAULT_SHARPE_STRONG_THRESHOLD,
    MINIMUM_BARS_REQUIRED,
    compute_baseline_forecast,
)
from .baseline_forecast import (
    MODEL_CODE as GBM_MODEL_CODE,
)
from .baseline_forecast import (
    MODEL_VERSION as GBM_MODEL_VERSION,
)
from .predictor_protocol import (
    DIRECTION_FLAT,
    DIRECTION_SLIGHT_DOWN,
    DIRECTION_SLIGHT_UP,
    DIRECTION_STRONG_DOWN,
    DIRECTION_STRONG_UP,
    STATUS_BLOCKED,
    STATUS_READY,
    BacktestWindowScore,
    PredictionDistribution,
    PredictorInputs,
)

# The existing GBM uses ``"neutral"`` for the flat bucket — the protocol
# uses ``"flat"``. The other GBM labels map 1:1.
_GBM_DIRECTION_MAP: dict[str, str] = {
    "strong_up": DIRECTION_STRONG_UP,
    "slight_up": DIRECTION_SLIGHT_UP,
    "neutral": DIRECTION_FLAT,
    "slight_down": DIRECTION_SLIGHT_DOWN,
    "strong_down": DIRECTION_STRONG_DOWN,
}


def _map_direction(label: str) -> str:
    """Translate a GBM direction label into the locked protocol set.

    GBM emits ``"blocked"`` when the forecast itself is blocked; the
    protocol does not accept that as a direction (a blocked
    distribution still has to declare a numerical direction so the
    combiner can ignore it cleanly). We default to ``flat`` for any
    non-mapped label.
    """

    return _GBM_DIRECTION_MAP.get(label, DIRECTION_FLAT)


class GbmPredictor:
    """Lognormal-GBM predictor exposed via :class:`PredictorProtocol`.

    V1.1 Slice 27 adds three opt-in rebuild knobs locked by §22.5.
    Defaults preserve V1 behaviour exactly; the Slice 25 backtest +
    Slice 26 leaderboard surface whether enabling them actually
    improves the Brier-score on real bars.
    """

    def __init__(
        self,
        *,
        minimum_bars_required: int = MINIMUM_BARS_REQUIRED,
        drift_window_days: int | None = None,
        regime_shift_enabled: bool = False,
        regime_shift_threshold_pct: float = DEFAULT_REGIME_SHIFT_THRESHOLD_PCT,
        garch_enabled: bool = False,
        sharpe_strong_threshold: float = DEFAULT_SHARPE_STRONG_THRESHOLD,
        sharpe_slight_threshold: float = DEFAULT_SHARPE_SLIGHT_THRESHOLD,
    ) -> None:
        self._minimum_bars_required = minimum_bars_required
        self._drift_window_days = drift_window_days
        self._regime_shift_enabled = regime_shift_enabled
        self._regime_shift_threshold_pct = regime_shift_threshold_pct
        self._garch_enabled = garch_enabled
        self._sharpe_strong_threshold = sharpe_strong_threshold
        self._sharpe_slight_threshold = sharpe_slight_threshold

    @property
    def model_code(self) -> str:
        return GBM_MODEL_CODE

    @property
    def model_version(self) -> str:
        return GBM_MODEL_VERSION

    def predict(self, inputs: PredictorInputs) -> PredictionDistribution:
        forecast = compute_baseline_forecast(
            bars=inputs.historical_bars,
            current_price=inputs.current_price,
            horizon_trading_days=inputs.horizon_trading_days,
            minimum_bars_required=self._minimum_bars_required,
            drift_window_days=self._drift_window_days,
            regime_shift_enabled=self._regime_shift_enabled,
            regime_shift_threshold_pct=self._regime_shift_threshold_pct,
            garch_enabled=self._garch_enabled,
            sharpe_strong_threshold=self._sharpe_strong_threshold,
            sharpe_slight_threshold=self._sharpe_slight_threshold,
        )
        is_ready = forecast.status == "ready"
        return PredictionDistribution(
            model_code=GBM_MODEL_CODE,
            model_version=GBM_MODEL_VERSION,
            horizon_trading_days=forecast.horizon_days,
            current_price=forecast.current_price,
            p10_price=forecast.p10_price,
            p50_price=forecast.p50_price,
            p90_price=forecast.p90_price,
            prob_gain=forecast.prob_gain,
            prob_loss=forecast.prob_loss,
            expected_return_pct=forecast.expected_return_pct,
            direction=_map_direction(forecast.direction_label),
            confidence_score=forecast.confidence_score,
            status=STATUS_READY if is_ready else STATUS_BLOCKED,
            blocking_reason=None if is_ready else forecast.blocking_reason,
            explanation_nl=forecast.explanation_nl,
        )

    def backtest_window_score(
        self, inputs: PredictorInputs, *, window_days: int
    ) -> BacktestWindowScore:
        """V1.1 §22.5: walk-forward backtest helper. Hands off to the
        shared :func:`backtest_window_score_for_predictor` so every
        predictor scores against the same harness."""

        from .predictor_backtester import backtest_window_score_for_predictor

        return backtest_window_score_for_predictor(
            self, inputs, window_days=window_days
        )


__all__ = [
    "GBM_MODEL_CODE",
    "GBM_MODEL_VERSION",
    "GbmPredictor",
]
