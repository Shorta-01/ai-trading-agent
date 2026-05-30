"""Ensemble forecast wiring for the live forecast-sync path.

Wires the doctrine-locked predictor ensemble (ADR-0003 / forecast-engine §1)
into the production forecaster. Today ``forecast_sync`` runs a single GBM
predictor; when ``FORECAST_ENSEMBLE_ENABLED`` is set it instead combines the
classical predictors (GBM + Momentum + Mean-reversion, and QVM when a
fundamentals universe is available) through ``compute_ensemble_forecast``.

AI-TS (predictor 6) is deliberately excluded: intent §7 puts LLM-as-forecaster
(case B) out of scope, and the current ``AiTsPredictor`` is exactly that
forbidden case-B path (see gap T-047 §1). It is not wired here.

The combiner emits the protocol ``PredictionDistribution`` (price quantiles +
a few summary stats). The live ``AssetForecastRecord`` carries richer fields
(tail probabilities, annualised volatility, downside-risk score, Dutch label).
``adapt_ensemble_to_forecast_record`` derives those from the combined quantiles
under the same lognormal model the GBM path uses, so a single-predictor GBM
ensemble reproduces the direct-GBM record (this is the adapter's correctness
oracle, asserted in tests).
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetForecastRecord,
    IbkrPositionSnapshotRecord,
    PredictorBacktestRunRecord,
)
from portfolio_outlook_portfolio import (
    DEFAULT_SHARPE_SLIGHT_THRESHOLD,
    DEFAULT_SHARPE_STRONG_THRESHOLD,
    EnsembleResult,
    GbmPredictor,
    HistoricalBar,
    MeanReversionPredictor,
    MomentumPredictor,
    PredictionDistribution,
    PredictorInputs,
    PredictorProtocol,
    QvmFactorPredictor,
    UniverseFundamentals,
    compute_ensemble_forecast,
)
from portfolio_outlook_portfolio.ensemble_combiner import (
    WEIGHT_STRATEGY_EQUAL,
)

ENSEMBLE_FORECAST_MODEL_CODE = "ensemble_v1"
ENSEMBLE_FORECAST_MODEL_VERSION = "v1.0.0"

# Standard-normal quantiles (mirrors baseline_forecast.Z_10 / Z_90).
_Z_10 = -1.2815515655446004
_Z_90 = 1.2815515655446004
_DEFAULT_TRADING_DAYS_PER_YEAR = 252


def build_ensemble_predictors(
    *,
    target_symbol: str,
    qvm_universe: UniverseFundamentals | None = None,
    sharpe_strong_threshold: float = DEFAULT_SHARPE_STRONG_THRESHOLD,
    sharpe_slight_threshold: float = DEFAULT_SHARPE_SLIGHT_THRESHOLD,
) -> list[PredictorProtocol]:
    """Assemble the doctrine-compliant classical predictor set.

    GBM + Momentum + Mean-reversion are always included (price-bars only).
    QVM is added only when a fundamentals universe is supplied; it blocks
    itself gracefully (insufficient_universe / symbol_not_in_universe) and the
    combiner then drops it, so a missing/small universe simply yields a
    3-predictor ensemble. AI-TS is intentionally excluded (intent §7).

    The Sharpe thresholds flow into the embedded ``GbmPredictor`` so the
    operator-tunable values reach the GBM direction-label logic.
    """

    predictors: list[PredictorProtocol] = [
        GbmPredictor(
            sharpe_strong_threshold=sharpe_strong_threshold,
            sharpe_slight_threshold=sharpe_slight_threshold,
        ),
        MomentumPredictor(),
        MeanReversionPredictor(),
    ]
    if qvm_universe is not None:
        predictors.append(
            QvmFactorPredictor(universe=qvm_universe, target_symbol=target_symbol)
        )
    return predictors


def _decimal(value: float, places: int = 6) -> Decimal:
    quant = Decimal(1).scaleb(-places)
    return Decimal(repr(value)).quantize(quant, rounding=ROUND_HALF_UP)


def _prob(value: float) -> Decimal:
    clamped = 0.0 if value < 0.0 else 1.0 if value > 1.0 else value
    return _decimal(clamped, places=6)


def _normal_cdf(z: float) -> float:
    return 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))


def ensemble_direction_label(expected_return_pct: float) -> tuple[str, str]:
    """Mirror of ``baseline_forecast._direction_label`` so ensemble records use
    the same label vocabulary (incl. the "neutral" middle band, not the
    protocol's "flat") as the GBM path. A parity test guards against drift."""

    if expected_return_pct >= 10.0:
        return "strong_up", "Sterke stijging verwacht"
    if expected_return_pct >= 2.0:
        return "slight_up", "Lichte stijging verwacht"
    if expected_return_pct > -2.0:
        return "neutral", "Geen duidelijke richting"
    if expected_return_pct > -10.0:
        return "slight_down", "Lichte daling verwacht"
    return "strong_down", "Duidelijke daling verwacht"


@dataclass(frozen=True)
class _LognormalMetrics:
    prob_gain: Decimal
    prob_loss: Decimal
    prob_loss_gt_5pct: Decimal
    prob_loss_gt_10pct: Decimal
    prob_gain_gt_5pct: Decimal
    prob_gain_gt_10pct: Decimal
    expected_volatility_annual: Decimal
    downside_risk_score: Decimal


def derive_lognormal_metrics(
    *,
    current_price: Decimal,
    p10_price: Decimal,
    p50_price: Decimal,
    p90_price: Decimal,
    horizon_trading_days: int,
    trading_days_per_year: int = _DEFAULT_TRADING_DAYS_PER_YEAR,
) -> _LognormalMetrics:
    """Fit a lognormal to the combined quantiles and derive the tail-risk
    fields the ensemble output doesn't carry. Same model family as the GBM
    path: ln(S_T/S0) ~ N(drift_log, diffusion_log^2)."""

    s0 = float(current_price)
    p10 = float(p10_price)
    p50 = float(p50_price)
    p90 = float(p90_price)

    drift_log = math.log(p50 / s0)
    # Symmetric spread estimate from the 10/90 band.
    diffusion_log = (math.log(p90 / s0) - math.log(p10 / s0)) / (_Z_90 - _Z_10)
    diffusion_log = max(diffusion_log, 1e-9)

    def _prob_below_ratio(ratio: float) -> float:
        return _normal_cdf((math.log(ratio) - drift_log) / diffusion_log)

    prob_loss = _prob_below_ratio(1.0)
    horizon_years = horizon_trading_days / float(trading_days_per_year)
    sigma_annual = diffusion_log / math.sqrt(horizon_years) if horizon_years > 0 else 0.0
    downside = max(0.0, (s0 - p10) / s0) * 100.0

    return _LognormalMetrics(
        prob_gain=_prob(1.0 - prob_loss),
        prob_loss=_prob(prob_loss),
        prob_loss_gt_5pct=_prob(_prob_below_ratio(0.95)),
        prob_loss_gt_10pct=_prob(_prob_below_ratio(0.90)),
        prob_gain_gt_5pct=_prob(1.0 - _prob_below_ratio(1.05)),
        prob_gain_gt_10pct=_prob(1.0 - _prob_below_ratio(1.10)),
        expected_volatility_annual=_decimal(sigma_annual, places=6),
        downside_risk_score=_decimal(downside, places=6),
    )


def _compose_explanation(ensemble: EnsembleResult) -> str:
    parts = [
        f"{c.model_code}={c.weight_normalised}" for c in ensemble.contributions
    ]
    blocked = ", ".join(ensemble.blocked_model_codes) or "geen"
    return (
        "Ensemble-voorspelling (gewogen gemiddelde). Deelnemers: "
        + ("; ".join(parts) if parts else "geen")
        + f". Geblokkeerd: {blocked}. Geen suggesties of orders gegenereerd."
    )


def run_ensemble_forecast(
    *,
    bars: list[HistoricalBar],
    current_price: Decimal,
    target_symbol: str,
    sector: str | None,
    horizon_trading_days: int,
    qvm_universe: UniverseFundamentals | None = None,
    weight_strategy: str = WEIGHT_STRATEGY_EQUAL,
    brier_history: dict[str, Decimal] | None = None,
    sharpe_strong_threshold: float = DEFAULT_SHARPE_STRONG_THRESHOLD,
    sharpe_slight_threshold: float = DEFAULT_SHARPE_SLIGHT_THRESHOLD,
) -> EnsembleResult:
    """Build the predictor set and combine it for one asset.

    ``weight_strategy="auto"`` consumes ``brier_history`` (per-predictor Brier
    scores, lower = better) via the combiner's inverse-Brier weighting, clipped
    to the doctrine's 10%/40% bounds. With no history it degrades to
    equal-weight, so auto is always safe.
    """

    predictors = build_ensemble_predictors(
        target_symbol=target_symbol,
        qvm_universe=qvm_universe,
        sharpe_strong_threshold=sharpe_strong_threshold,
        sharpe_slight_threshold=sharpe_slight_threshold,
    )
    metadata = {"symbol": target_symbol}
    if sector:
        metadata["sector"] = sector
    inputs = PredictorInputs(
        historical_bars=bars,
        current_price=current_price,
        horizon_trading_days=horizon_trading_days,
        asset_metadata=metadata,
    )
    return compute_ensemble_forecast(
        predictors,
        inputs,
        weight_strategy=weight_strategy,
        brier_history=brier_history,
    )


def latest_brier_by_model_code(
    records: Sequence[PredictorBacktestRunRecord],
) -> dict[str, Decimal]:
    """Most-recent succeeded backtest Brier score per predictor.

    ``records`` must be ordered most-recent-first. The newest run per
    ``model_code`` wins; if that run is skipped or has no Brier score, the
    predictor contributes no history (so it falls to the equal-weight floor).
    This is the cold-start weight source until live per-predictor outcomes
    accrue in the prediction diary.
    """

    latest: dict[str, Decimal] = {}
    seen: set[str] = set()
    for record in records:
        if record.model_code in seen:
            continue
        seen.add(record.model_code)
        if record.status == "succeeded" and record.brier_score is not None:
            latest[record.model_code] = record.brier_score
    return latest


def adapt_ensemble_to_forecast_record(
    *,
    position: IbkrPositionSnapshotRecord,
    ensemble: EnsembleResult,
    current_price: Decimal,
    bars: list[HistoricalBar],
    horizon_trading_days: int,
    generated_at: datetime,
    valid_until: datetime,
    trading_days_per_year: int = _DEFAULT_TRADING_DAYS_PER_YEAR,
) -> AssetForecastRecord:
    """Map an ``EnsembleResult`` onto the live ``AssetForecastRecord`` shape."""

    forecast: PredictionDistribution = ensemble.forecast
    first_date = bars[0].bar_date if bars else None
    last_date = bars[-1].bar_date if bars else None
    zero = Decimal("0")

    if forecast.status != "ready":
        return AssetForecastRecord(
            forecast_id=f"forecast_{uuid4().hex}",
            ibkr_conid=position.conid or "",
            symbol=position.symbol,
            currency=position.currency,
            model_code=ENSEMBLE_FORECAST_MODEL_CODE,
            model_version=ENSEMBLE_FORECAST_MODEL_VERSION,
            horizon_days=horizon_trading_days,
            generated_at=generated_at,
            valid_until=valid_until,
            data_points_used=len(bars),
            history_first_bar_date=first_date,
            history_last_bar_date=last_date,
            current_price=current_price,
            expected_return_pct=zero,
            p10_price=current_price,
            p50_price=current_price,
            p90_price=current_price,
            prob_gain=zero,
            prob_loss=zero,
            prob_loss_gt_5pct=zero,
            prob_loss_gt_10pct=zero,
            prob_gain_gt_5pct=zero,
            prob_gain_gt_10pct=zero,
            expected_volatility_annual=zero,
            downside_risk_score=zero,
            confidence_score=zero,
            direction_label="neutral",
            direction_label_nl="Geen duidelijke richting",
            explanation_nl=_compose_explanation(ensemble),
            status="blocked",
            blocking_reason=forecast.blocking_reason or "ensemble_blocked",
        )

    metrics = derive_lognormal_metrics(
        current_price=current_price,
        p10_price=forecast.p10_price,
        p50_price=forecast.p50_price,
        p90_price=forecast.p90_price,
        horizon_trading_days=horizon_trading_days,
        trading_days_per_year=trading_days_per_year,
    )
    label, label_nl = ensemble_direction_label(float(forecast.expected_return_pct))

    return AssetForecastRecord(
        forecast_id=f"forecast_{uuid4().hex}",
        ibkr_conid=position.conid or "",
        symbol=position.symbol,
        currency=position.currency,
        model_code=ENSEMBLE_FORECAST_MODEL_CODE,
        model_version=ENSEMBLE_FORECAST_MODEL_VERSION,
        horizon_days=horizon_trading_days,
        generated_at=generated_at,
        valid_until=valid_until,
        data_points_used=len(bars),
        history_first_bar_date=first_date,
        history_last_bar_date=last_date,
        current_price=current_price,
        expected_return_pct=forecast.expected_return_pct,
        p10_price=forecast.p10_price,
        p50_price=forecast.p50_price,
        p90_price=forecast.p90_price,
        prob_gain=metrics.prob_gain,
        prob_loss=metrics.prob_loss,
        prob_loss_gt_5pct=metrics.prob_loss_gt_5pct,
        prob_loss_gt_10pct=metrics.prob_loss_gt_10pct,
        prob_gain_gt_5pct=metrics.prob_gain_gt_5pct,
        prob_gain_gt_10pct=metrics.prob_gain_gt_10pct,
        expected_volatility_annual=metrics.expected_volatility_annual,
        downside_risk_score=metrics.downside_risk_score,
        confidence_score=forecast.confidence_score,
        direction_label=label,
        direction_label_nl=label_nl,
        explanation_nl=_compose_explanation(ensemble),
        status="ready",
        blocking_reason=None,
    )
