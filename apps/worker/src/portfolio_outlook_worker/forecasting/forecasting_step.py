"""Task 130 + 131: scheduler-driven multi-asset forecasting step.

Called by the orchestrator on ``morning_briefing`` 07:00 fires when
``mode_detected="normal"``. Task 131 expands the scope from one
pilot conid to the union of (confirmed watchlist + held positions)
for the configured account.

Per-asset failures don't crash the run. Each asset gets either a
successful ``ForecastEntry`` row or a ``Geblokkeerd`` row with one of
the locked Task 131 block_reasons:

* ``insufficient_history`` — fewer than ``MIN_CLOSES_FOR_FORECAST``
  of the last ``history_window_days`` trading days available.
* ``stale_market_data`` — latest snapshot older than 3 calendar days.
* ``missing_asset_listing`` — the close-provider returned no data
  for the conid (treated as a structural gap, not a transient error).
* ``computation_error`` — the bootstrap math raised unexpectedly.
* ``excessive_volatility`` — annualized vol > 100%, suggests data
  quality issue (split not applied, currency mix-up, etc.).

The step returns a ``ForecastingStepResult`` the orchestrator folds
into ``scheduled_run_audit.error_details_json``.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    BootstrapInsufficientHistoryError,
    ForecastEntry,
    SqlAlchemyForecastRepository,
)

from portfolio_outlook_worker.forecasting.asset_universe_resolver import (
    ConidWithContext,
    PositionUniverseProvider,
    WatchlistUniverseProvider,
    resolve_forecast_universe,
)
from portfolio_outlook_worker.forecasting.historical_bootstrap import (
    DEFAULT_BLOCK_SIZE,
    DEFAULT_HISTORY_WINDOW_DAYS,
    DEFAULT_HORIZON_DAYS,
    DEFAULT_NUM_RESAMPLES,
    MIN_CLOSES_FOR_FORECAST,
    compute_historical_bootstrap_forecast,
)
from portfolio_outlook_worker.forecasting.label_translator import (
    Freshness,
    derive_confidence,
    translate_to_label,
)

logger = logging.getLogger(__name__)

# Task 131 product lock §5: assets whose latest EOD snapshot is older
# than this many calendar days get blocked as ``stale_market_data``.
STALE_MARKET_DATA_THRESHOLD_DAYS = 3

# Task 131 product lock §5: implausibly high vol suggests a data quality
# issue (corporate action not applied, currency mismatch, etc.) — block
# rather than silently emit a noisy forecast.
EXCESSIVE_VOLATILITY_THRESHOLD = Decimal("1.00")


class _CloseProviderProtocol(Protocol):
    """Storage adapter: returns ascending list of recent Decimal closes."""

    def list_recent_closes(
        self, *, ibkr_conid: str, days: int
    ) -> tuple[tuple[date, Decimal], ...]: ...


@dataclass(frozen=True)
class _PerConidResult:
    conid: str
    forecast_run_id: str | None
    label: str
    block_reason: str | None
    error: str | None


@dataclass(frozen=True)
class ForecastingStepResult:
    """Task 131: summary the orchestrator folds into scheduled_run_audit.

    ``succeeded`` and ``blocked_by_reason`` count only **persisted** rows
    (``forecast_run_id is not None``). When ``forecast_repo.append``
    raises, the corresponding asset lands in ``persistence_failures``
    so the audit row makes the failure visible rather than reporting
    a false success.
    """

    total_attempted: int
    succeeded: int
    blocked_by_reason: dict[str, int] = field(default_factory=dict)
    per_conid: tuple[_PerConidResult, ...] = field(default_factory=tuple)
    wall_clock_ms: int = 0
    persistence_failures: int = 0

    @property
    def total_blocked(self) -> int:
        return sum(self.blocked_by_reason.values())

    def as_audit_dict(self) -> dict[str, object]:
        return {
            "total_attempted": self.total_attempted,
            "succeeded": self.succeeded,
            "total_blocked": self.total_blocked,
            "blocked_by_reason": dict(self.blocked_by_reason),
            "persistence_failures": self.persistence_failures,
            "wall_clock_ms": self.wall_clock_ms,
        }


def run_forecasting_step(
    *,
    ibkr_account_id: str,
    watchlist_provider: WatchlistUniverseProvider,
    position_provider: PositionUniverseProvider,
    close_provider: _CloseProviderProtocol,
    forecast_repo: SqlAlchemyForecastRepository,
    scheduled_run_id: str,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
    rng_seed: int | None = None,
    history_window_days: int = DEFAULT_HISTORY_WINDOW_DAYS,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    num_resamples: int = DEFAULT_NUM_RESAMPLES,
    block_size: int = DEFAULT_BLOCK_SIZE,
    override_conids: tuple[str, ...] | None = None,
) -> ForecastingStepResult:
    """Run one multi-asset forecasting cycle. Never raises."""

    started_ms = time.monotonic() * 1000.0
    universe = resolve_forecast_universe(
        ibkr_account_id=ibkr_account_id,
        watchlist_provider=watchlist_provider,
        position_provider=position_provider,
        override_conids=override_conids,
    )

    per_conid: list[_PerConidResult] = []
    succeeded = 0
    blocked_by_reason: dict[str, int] = {}
    persistence_failures = 0
    now = now_provider()

    for context in universe:
        result = _forecast_single_asset(
            context=context,
            now=now,
            close_provider=close_provider,
            forecast_repo=forecast_repo,
            scheduled_run_id=scheduled_run_id,
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            num_resamples=num_resamples,
            block_size=block_size,
            rng_seed=rng_seed,
        )
        per_conid.append(result)
        # ``forecast_run_id is None`` is the deterministic signal that
        # the row was NOT persisted (set only after a successful
        # ``forecast_repo.append``). Count those toward
        # ``persistence_failures`` so the audit makes the failure
        # visible rather than reporting a false success/block.
        if result.forecast_run_id is None:
            persistence_failures += 1
        elif result.label == "Geblokkeerd" and result.block_reason is not None:
            blocked_by_reason[result.block_reason] = (
                blocked_by_reason.get(result.block_reason, 0) + 1
            )
        elif result.label != "Geblokkeerd":
            succeeded += 1

    wall_ms = int(time.monotonic() * 1000.0 - started_ms)
    return ForecastingStepResult(
        total_attempted=len(universe),
        succeeded=succeeded,
        blocked_by_reason=blocked_by_reason,
        per_conid=tuple(per_conid),
        wall_clock_ms=wall_ms,
        persistence_failures=persistence_failures,
    )


def _forecast_single_asset(
    *,
    context: ConidWithContext,
    now: datetime,
    close_provider: _CloseProviderProtocol,
    forecast_repo: SqlAlchemyForecastRepository,
    scheduled_run_id: str,
    history_window_days: int,
    horizon_days: int,
    num_resamples: int,
    block_size: int,
    rng_seed: int | None,
) -> _PerConidResult:
    """Forecast a single asset. Returns success or one of the locked block reasons."""

    conid = context.conid

    try:
        closes_with_dates = close_provider.list_recent_closes(
            ibkr_conid=conid, days=history_window_days
        )
    except Exception as exc:  # noqa: BLE001 — boundary
        logger.exception("Failed to load closes for %s", conid)
        return _persist_blocked(
            conid=conid,
            now=now,
            scheduled_run_id=scheduled_run_id,
            forecast_repo=forecast_repo,
            block_reason="missing_asset_listing",
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            current_price=Decimal("0"),
            error=str(exc),
            history_closes_count=0,
        )

    if not closes_with_dates:
        return _persist_blocked(
            conid=conid,
            now=now,
            scheduled_run_id=scheduled_run_id,
            forecast_repo=forecast_repo,
            block_reason="missing_asset_listing",
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            current_price=Decimal("0"),
            error=None,
            history_closes_count=0,
        )

    closes = [c for (_d, c) in closes_with_dates]
    latest_date = closes_with_dates[-1][0]
    current_price = closes[-1]

    days_old = (now.date() - latest_date).days
    if days_old > STALE_MARKET_DATA_THRESHOLD_DAYS:
        return _persist_blocked(
            conid=conid,
            now=now,
            scheduled_run_id=scheduled_run_id,
            forecast_repo=forecast_repo,
            block_reason="stale_market_data",
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            current_price=current_price,
            error=None,
            history_closes_count=len(closes),
        )

    if len(closes) < MIN_CLOSES_FOR_FORECAST:
        return _persist_blocked(
            conid=conid,
            now=now,
            scheduled_run_id=scheduled_run_id,
            forecast_repo=forecast_repo,
            block_reason="insufficient_history",
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            current_price=current_price,
            error=None,
            history_closes_count=len(closes),
        )

    try:
        forecast = compute_historical_bootstrap_forecast(
            daily_closes=closes,
            horizon_days=horizon_days,
            num_resamples=num_resamples,
            block_size=block_size,
            rng_seed=rng_seed,
        )
    except BootstrapInsufficientHistoryError:
        return _persist_blocked(
            conid=conid,
            now=now,
            scheduled_run_id=scheduled_run_id,
            forecast_repo=forecast_repo,
            block_reason="insufficient_history",
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            current_price=current_price,
            error=None,
            history_closes_count=len(closes),
        )
    except Exception as exc:  # noqa: BLE001 — boundary
        logger.exception("Bootstrap failed for %s", conid)
        return _persist_blocked(
            conid=conid,
            now=now,
            scheduled_run_id=scheduled_run_id,
            forecast_repo=forecast_repo,
            block_reason="computation_error",
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            current_price=current_price,
            error=str(exc),
            history_closes_count=len(closes),
        )

    if forecast.expected_volatility_annualized > EXCESSIVE_VOLATILITY_THRESHOLD:
        return _persist_blocked(
            conid=conid,
            now=now,
            scheduled_run_id=scheduled_run_id,
            forecast_repo=forecast_repo,
            block_reason="excessive_volatility",
            history_window_days=history_window_days,
            horizon_days=horizon_days,
            current_price=current_price,
            error=None,
            history_closes_count=len(closes),
        )

    freshness: Freshness = "fresh" if days_old <= 1 else "stale"
    confidence = derive_confidence(
        history_closes_count=len(closes),
        gaps_in_last_60_days=0,
        expected_volatility_annualized=forecast.expected_volatility_annualized,
    )
    label_result = translate_to_label(
        forecast=forecast,
        user_holds_position=context.user_holds_position,
        freshness=freshness,
        confidence=confidence,
        history_closes_count=len(closes),
    )
    forecast_run_id = f"fcst_{uuid4().hex}"
    entry = ForecastEntry(
        forecast_run_id=forecast_run_id,
        conid=conid,
        generated_at=now,
        generated_by_scheduled_run_id=scheduled_run_id,
        horizon_trading_days=horizon_days,
        forecast_valid_until=now + timedelta(days=int(horizon_days * 1.4)),
        method="historical_bootstrap_v1",
        history_window_days=history_window_days,
        history_closes_count=len(closes),
        current_price_local=current_price,
        currency_local="EUR",
        p10_log_return=forecast.p10_log_return,
        p50_log_return=forecast.p50_log_return,
        p90_log_return=forecast.p90_log_return,
        prob_positive=forecast.prob_positive,
        prob_loss_gt_5pct=forecast.prob_loss_gt_5pct,
        expected_volatility_annualized=forecast.expected_volatility_annualized,
        confidence_level=confidence,
        label=label_result.label,
        block_reason=label_result.block_reason,
        expired_at=None,
    )
    try:
        forecast_repo.append(entry)
    except Exception as exc:  # noqa: BLE001 — boundary
        logger.exception("Failed to persist forecast for %s", conid)
        return _PerConidResult(
            conid=conid,
            forecast_run_id=None,
            label=label_result.label,
            block_reason=label_result.block_reason,
            error=str(exc),
        )
    return _PerConidResult(
        conid=conid,
        forecast_run_id=forecast_run_id,
        label=label_result.label,
        block_reason=label_result.block_reason,
        error=None,
    )


def _persist_blocked(
    *,
    conid: str,
    now: datetime,
    scheduled_run_id: str,
    forecast_repo: SqlAlchemyForecastRepository,
    block_reason: str,
    history_window_days: int,
    horizon_days: int,
    current_price: Decimal,
    error: str | None,
    history_closes_count: int,
) -> _PerConidResult:
    forecast_run_id = f"fcst_{uuid4().hex}"
    entry = ForecastEntry(
        forecast_run_id=forecast_run_id,
        conid=conid,
        generated_at=now,
        generated_by_scheduled_run_id=scheduled_run_id,
        horizon_trading_days=horizon_days,
        forecast_valid_until=now + timedelta(days=int(horizon_days * 1.4)),
        method="historical_bootstrap_v1",
        history_window_days=history_window_days,
        history_closes_count=history_closes_count,
        current_price_local=current_price,
        currency_local="EUR",
        p10_log_return=Decimal("0"),
        p50_log_return=Decimal("0"),
        p90_log_return=Decimal("0"),
        prob_positive=Decimal("0.5"),
        prob_loss_gt_5pct=Decimal("0"),
        expected_volatility_annualized=Decimal("0"),
        confidence_level="Laag",
        label="Geblokkeerd",
        block_reason=block_reason,
        expired_at=None,
    )
    persistence_error = error
    persisted_run_id: str | None = None
    try:
        forecast_repo.append(entry)
        persisted_run_id = forecast_run_id
    except Exception as exc:  # noqa: BLE001 — boundary
        logger.exception(
            "Failed to persist %s forecast for %s", block_reason, conid
        )
        persistence_error = str(exc)
    return _PerConidResult(
        conid=conid,
        forecast_run_id=persisted_run_id,
        label="Geblokkeerd",
        block_reason=block_reason,
        error=persistence_error,
    )


__all__ = [
    "EXCESSIVE_VOLATILITY_THRESHOLD",
    "ForecastingStepResult",
    "STALE_MARKET_DATA_THRESHOLD_DAYS",
    "run_forecasting_step",
]
