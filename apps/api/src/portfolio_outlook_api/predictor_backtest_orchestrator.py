"""Backtest orchestrator (V1.1 Slice 25).

Wires the pure-Python walk-forward harness from
:mod:`portfolio_outlook_portfolio.predictor_backtester` to the
storage layer + the runtime predictor factory. The route layer
calls :func:`run_backtest_for_symbol`; this module owns the bar
fetch + predictor construction + audit-row persistence flow.

Pure-Python; no I/O except via the injected repositories.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Final, Protocol

from ai_trading_agent_storage import (
    MarketDataBarRecord,
    PredictorBacktestRunRecord,
)
from portfolio_outlook_portfolio import (
    HistoricalBar,
)
from portfolio_outlook_portfolio.gbm_predictor import GbmPredictor
from portfolio_outlook_portfolio.mean_reversion_predictor import (
    MeanReversionPredictor,
)
from portfolio_outlook_portfolio.momentum_predictor import MomentumPredictor
from portfolio_outlook_portfolio.predictor_backtester import (
    DEFAULT_HORIZON_DAYS,
    DEFAULT_STEP_DAYS,
    DEFAULT_WINDOW_DAYS,
    new_backtest_run_id,
    run_predictor_backtest,
)
from portfolio_outlook_portfolio.predictor_protocol import PredictorProtocol

LOCKED_MODEL_CODES: Final[frozenset[str]] = frozenset(
    {
        "baseline_gbm",
        "momentum_v1",
        "mean_reversion_v1",
    }
)
"""V1.1 §22.5 backtest scope. The four-predictor backtest set
excludes ``qvm_factor_v1`` and ``ai_ts_v1`` from the V1.1 Slice 25
backtest route because both need extra orchestration: QVM needs a
universe snapshot per fold (deferred to Slice 28's QVM rebuild) and
AI TS needs a real provider (deferred to Slice 30). The route still
accepts both codes but returns a ``skipped`` audit row with a
stable blocker so the leaderboard surfaces the gap cleanly."""


SKIPPED_QVM_REASON: Final[str] = "qvm_backtest_deferred_to_slice_28"
SKIPPED_AI_TS_REASON: Final[str] = "ai_ts_backtest_deferred_to_slice_30"


class _MarketDataBarRepoProtocol(Protocol):
    def list_market_data_bars_by_conid(
        self,
        ibkr_conid: str,
        *,
        interval_code: str = ...,
        limit: int = ...,
    ) -> object: ...


class _PredictorBacktestRepoProtocol(Protocol):
    def save_backtest_run(
        self, record: PredictorBacktestRunRecord
    ) -> object: ...

    def update_backtest_run(
        self, record: PredictorBacktestRunRecord
    ) -> object: ...


@dataclass(frozen=True)
class BacktestOrchestratorResult:
    """Outcome the route layer surfaces to the caller."""

    record: PredictorBacktestRunRecord
    status_nl: str
    help_nl: str


def _bars_from_records(
    records: Sequence[MarketDataBarRecord],
) -> list[HistoricalBar]:
    """Convert persisted bar records into the harness's value
    objects. Records arrive ordered ascending by ``bar_date``."""

    return [
        HistoricalBar(bar_date=r.bar_date, close_price=r.close_price)
        for r in records
    ]


def _build_predictor_or_skip(
    model_code: str,
    *,
    settings: object | None = None,
) -> tuple[PredictorProtocol | None, str | None]:
    """Return ``(predictor, None)`` for the supported model codes,
    ``(None, blocker)`` for the deferred ones, and raise
    ``ValueError`` for unknown codes.

    The QVM and AI TS predictors stay skipped at this layer; Slices
    28 + 30 will wire them in.

    V1.1 Slice 27 — when ``settings`` is supplied the GBM + Momentum
    predictors honour the operator's rebuild knobs
    (`gbm_drift_window_days`, `gbm_regime_shift_enabled`,
    `gbm_regime_shift_threshold_pct`, `gbm_garch_enabled`,
    `momentum_horizon_scaled_thresholds`,
    `momentum_skip_week_short_horizon`). The defaults preserve V1
    behaviour exactly when ``settings`` is ``None``.
    """

    if model_code == "baseline_gbm":
        gbm_kwargs: dict[str, object] = {}
        if settings is not None:
            gbm_kwargs["drift_window_days"] = getattr(
                settings, "gbm_drift_window_days", None
            )
            gbm_kwargs["regime_shift_enabled"] = bool(
                getattr(settings, "gbm_regime_shift_enabled", False)
            )
            threshold = getattr(
                settings, "gbm_regime_shift_threshold_pct", None
            )
            if threshold is not None:
                gbm_kwargs["regime_shift_threshold_pct"] = float(threshold)
            gbm_kwargs["garch_enabled"] = bool(
                getattr(settings, "gbm_garch_enabled", False)
            )
        return GbmPredictor(**gbm_kwargs), None  # type: ignore[arg-type]
    if model_code == "momentum_v1":
        momentum_kwargs: dict[str, object] = {}
        if settings is not None:
            momentum_kwargs["horizon_scaled_thresholds"] = bool(
                getattr(settings, "momentum_horizon_scaled_thresholds", False)
            )
            momentum_kwargs["skip_week_short_horizon"] = bool(
                getattr(settings, "momentum_skip_week_short_horizon", False)
            )
        return MomentumPredictor(**momentum_kwargs), None  # type: ignore[arg-type]
    if model_code == "mean_reversion_v1":
        mean_rev_kwargs: dict[str, object] = {}
        if settings is not None:
            mean_rev_kwargs["hurst_asymmetric_target"] = bool(
                getattr(settings, "mean_reversion_hurst_asymmetric_target", False)
            )
        return MeanReversionPredictor(**mean_rev_kwargs), None  # type: ignore[arg-type]
    if model_code == "qvm_factor_v1":
        # QVM still skipped — its walk-forward universe support
        # ships alongside Slice 28's QVM rebuild but the universe
        # snapshot per fold needs the EODHD universe-scan slice.
        # The rebuild knobs are honoured here so the morning chain
        # path (Slice 31+) can construct the rebuilt predictor.
        return None, SKIPPED_QVM_REASON
    if model_code == "ai_ts_v1":
        return None, SKIPPED_AI_TS_REASON
    raise ValueError(f"Unknown predictor model_code: {model_code!r}")


def _skipped_record(
    *,
    run_id: str,
    model_code: str,
    asset_symbol: str,
    started_at: datetime,
    finished_at: datetime,
    window_days: int,
    blocking_reason: str,
    detail_nl: str,
) -> PredictorBacktestRunRecord:
    return PredictorBacktestRunRecord(
        run_id=run_id,
        model_code=model_code,
        model_version="n/a",
        asset_symbol=asset_symbol,
        started_at=started_at,
        finished_at=finished_at,
        status="skipped",
        window_days=window_days,
        bars_used=0,
        brier_score=None,
        hit_rate=None,
        sharpe_ratio=None,
        blocking_reason=blocking_reason,
        explanation_nl=detail_nl,
    )


def run_backtest_for_symbol(
    *,
    model_code: str,
    asset_symbol: str,
    ibkr_conid: str,
    bar_repo: _MarketDataBarRepoProtocol,
    backtest_repo: _PredictorBacktestRepoProtocol,
    window_days: int = DEFAULT_WINDOW_DAYS,
    horizon_trading_days: int = DEFAULT_HORIZON_DAYS,
    step_days: int = DEFAULT_STEP_DAYS,
    asset_metadata: dict[str, str] | None = None,
    bar_history_limit: int = 1500,
    run_id_factory: Callable[[], str] = new_backtest_run_id,
    settings: object | None = None,
) -> BacktestOrchestratorResult:
    """End-to-end backtest for one (model_code, asset_symbol) pair.

    Persists a ``running`` row up-front, then updates it to its
    terminal status (``succeeded`` / ``skipped`` / ``failed``).
    Failure paths never raise — the caller always gets a
    ``BacktestOrchestratorResult``.

    V1.1 Slice 27 — when ``settings`` is supplied the GBM + Momentum
    predictors honour the operator's rebuild knobs.
    """

    started_at = datetime.now(UTC)
    run_id = run_id_factory()

    try:
        predictor, blocker = _build_predictor_or_skip(model_code, settings=settings)
    except ValueError as exc:
        finished_at = datetime.now(UTC)
        record = _skipped_record(
            run_id=run_id,
            model_code=model_code,
            asset_symbol=asset_symbol,
            started_at=started_at,
            finished_at=finished_at,
            window_days=window_days,
            blocking_reason="unknown_model_code",
            detail_nl=str(exc),
        )
        backtest_repo.save_backtest_run(record)
        return BacktestOrchestratorResult(
            record=record,
            status_nl="Onbekend predictor model_code",
            help_nl=(
                f"Geef een geldig model_code mee uit {sorted(LOCKED_MODEL_CODES)} "
                "of een van de uitgestelde codes (qvm_factor_v1, ai_ts_v1)."
            ),
        )

    initial = PredictorBacktestRunRecord(
        run_id=run_id,
        model_code=model_code,
        model_version="pending",
        asset_symbol=asset_symbol,
        started_at=started_at,
        finished_at=None,
        status="running",
        window_days=window_days,
        bars_used=0,
        brier_score=None,
        hit_rate=None,
        sharpe_ratio=None,
        blocking_reason=None,
        explanation_nl=None,
    )
    backtest_repo.save_backtest_run(initial)

    if predictor is None and blocker is not None:
        finished_at = datetime.now(UTC)
        record = _skipped_record(
            run_id=run_id,
            model_code=model_code,
            asset_symbol=asset_symbol,
            started_at=started_at,
            finished_at=finished_at,
            window_days=window_days,
            blocking_reason=blocker,
            detail_nl=(
                f"Backtest voor {model_code} is uitgesteld tot een latere V1.1 slice."
            ),
        )
        backtest_repo.update_backtest_run(record)
        return BacktestOrchestratorResult(
            record=record,
            status_nl="Backtest overgeslagen",
            help_nl=record.explanation_nl or "",
        )

    assert predictor is not None  # narrowed by the branch above
    bars_list_result = bar_repo.list_market_data_bars_by_conid(
        ibkr_conid, limit=bar_history_limit
    )
    records: Sequence[MarketDataBarRecord] = getattr(
        bars_list_result, "records", ()
    )
    bars = _bars_from_records(records)
    if not bars:
        finished_at = datetime.now(UTC)
        record = _skipped_record(
            run_id=run_id,
            model_code=model_code,
            asset_symbol=asset_symbol,
            started_at=started_at,
            finished_at=finished_at,
            window_days=window_days,
            blocking_reason="no_bars_persisted",
            detail_nl="Geen bars in opslag voor dit conid.",
        )
        backtest_repo.update_backtest_run(record)
        return BacktestOrchestratorResult(
            record=record,
            status_nl="Geen bars voor dit conid",
            help_nl="Vul market_data_bars via de market-data sync.",
        )

    outputs = run_predictor_backtest(
        predictor,
        bars,
        window_days=window_days,
        horizon_trading_days=horizon_trading_days,
        step_days=step_days,
        asset_metadata=asset_metadata,
    )
    score = outputs.score
    record = PredictorBacktestRunRecord(
        run_id=run_id,
        model_code=score.model_code,
        model_version=score.model_version,
        asset_symbol=asset_symbol,
        started_at=started_at,
        finished_at=outputs.finished_at,
        status=outputs.status,
        window_days=window_days,
        bars_used=score.bars_used,
        brier_score=(
            Decimal(f"{score.brier_score:.6f}")
            if score.brier_score is not None
            else None
        ),
        hit_rate=(
            Decimal(f"{score.hit_rate:.6f}")
            if score.hit_rate is not None
            else None
        ),
        sharpe_ratio=(
            Decimal(f"{score.sharpe_ratio:.6f}")
            if score.sharpe_ratio is not None
            else None
        ),
        blocking_reason=outputs.blocking_reason,
        explanation_nl=score.explanation_nl,
    )
    backtest_repo.update_backtest_run(record)
    return BacktestOrchestratorResult(
        record=record,
        status_nl=(
            "Backtest voltooid"
            if outputs.status == "succeeded"
            else "Backtest overgeslagen"
        ),
        help_nl=score.explanation_nl,
    )


def serialize_backtest_run_record(
    record: PredictorBacktestRunRecord,
) -> dict[str, object]:
    """JSON-friendly serialisation for the route response + leaderboard."""

    return {
        "run_id": record.run_id,
        "model_code": record.model_code,
        "model_version": record.model_version,
        "asset_symbol": record.asset_symbol,
        "started_at": record.started_at.isoformat(),
        "finished_at": (
            record.finished_at.isoformat()
            if record.finished_at is not None
            else None
        ),
        "status": record.status,
        "window_days": record.window_days,
        "bars_used": record.bars_used,
        "brier_score": (
            str(record.brier_score) if record.brier_score is not None else None
        ),
        "hit_rate": (
            str(record.hit_rate) if record.hit_rate is not None else None
        ),
        "sharpe_ratio": (
            str(record.sharpe_ratio)
            if record.sharpe_ratio is not None
            else None
        ),
        "blocking_reason": record.blocking_reason,
        "explanation_nl": record.explanation_nl,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


__all__ = [
    "LOCKED_MODEL_CODES",
    "SKIPPED_AI_TS_REASON",
    "SKIPPED_QVM_REASON",
    "BacktestOrchestratorResult",
    "run_backtest_for_symbol",
    "serialize_backtest_run_record",
]
