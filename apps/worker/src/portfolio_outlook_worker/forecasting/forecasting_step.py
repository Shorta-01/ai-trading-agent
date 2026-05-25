"""Task 130: scheduler-driven forecasting step.

Called by the orchestrator on ``morning_briefing`` 07:00 fires (only)
when ``mode_detected="normal"``. For each pilot conid:

1. Pull the last ``history_window_days`` EOD closes from
   ``market_data_eod_snapshots`` via the storage repo.
2. Compute the historical-bootstrap forecast.
3. Determine if the user holds the position.
4. Derive freshness from the most-recent snapshot's date.
5. Derive confidence from data-quality checks.
6. Translate to a Dutch label.
7. Append the ``ForecastEntry`` row.

The step never raises: any per-conid failure is folded into the
result so the orchestrator can persist it in the run's audit row.
"""

from __future__ import annotations

import logging
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

from portfolio_outlook_worker.forecasting.historical_bootstrap import (
    DEFAULT_BLOCK_SIZE,
    DEFAULT_HISTORY_WINDOW_DAYS,
    DEFAULT_HORIZON_DAYS,
    DEFAULT_NUM_RESAMPLES,
    compute_historical_bootstrap_forecast,
)
from portfolio_outlook_worker.forecasting.label_translator import (
    Freshness,
    derive_confidence,
    translate_to_label,
)

logger = logging.getLogger(__name__)


class _CloseProviderProtocol(Protocol):
    """Storage adapter: returns ascending list of recent Decimal closes."""

    def list_recent_closes(
        self, *, ibkr_conid: str, days: int
    ) -> tuple[tuple[date, Decimal], ...]: ...


class _HoldingsProtocol(Protocol):
    """Storage adapter: True iff the configured account holds the conid."""

    def holds_conid(
        self, *, ibkr_account_id: str, ibkr_conid: str
    ) -> bool: ...


@dataclass(frozen=True)
class _PerConidResult:
    conid: str
    forecast_run_id: str | None
    label: str
    block_reason: str | None
    error: str | None


@dataclass(frozen=True)
class ForecastingStepResult:
    """Summary the orchestrator folds into scheduled_run_audit."""

    pilot_conids_attempted: int
    forecasts_written: int
    per_conid: tuple[_PerConidResult, ...] = field(default_factory=tuple)

    def as_audit_dict(self) -> dict[str, object]:
        return {
            "pilot_conids_attempted": self.pilot_conids_attempted,
            "forecasts_written": self.forecasts_written,
            "blocked_count": sum(
                1 for r in self.per_conid if r.label == "Geblokkeerd"
            ),
        }


def run_forecasting_step(
    *,
    ibkr_account_id: str,
    pilot_conids: tuple[str, ...],
    close_provider: _CloseProviderProtocol,
    holdings: _HoldingsProtocol,
    forecast_repo: SqlAlchemyForecastRepository,
    scheduled_run_id: str,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
    rng_seed: int | None = None,
    history_window_days: int = DEFAULT_HISTORY_WINDOW_DAYS,
    horizon_days: int = DEFAULT_HORIZON_DAYS,
    num_resamples: int = DEFAULT_NUM_RESAMPLES,
    block_size: int = DEFAULT_BLOCK_SIZE,
) -> ForecastingStepResult:
    """One forecast cycle. Never raises."""

    per_conid: list[_PerConidResult] = []
    forecasts_written = 0

    for conid in pilot_conids:
        try:
            closes_with_dates = close_provider.list_recent_closes(
                ibkr_conid=conid, days=history_window_days
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "Failed to load closes for %s", conid
            )
            per_conid.append(
                _PerConidResult(
                    conid=conid,
                    forecast_run_id=None,
                    label="Geblokkeerd",
                    block_reason="data_unavailable",
                    error=str(exc),
                )
            )
            continue

        # Closes empty → block on data-unavailable.
        if not closes_with_dates:
            per_conid.append(
                _PerConidResult(
                    conid=conid,
                    forecast_run_id=None,
                    label="Geblokkeerd",
                    block_reason="data_unavailable",
                    error=None,
                )
            )
            continue

        closes = [c for (_d, c) in closes_with_dates]
        latest_date = closes_with_dates[-1][0]
        now = now_provider()

        # Freshness derivation (calendar-day proxy for trading-day SLA).
        today = now.date()
        days_old = (today - latest_date).days
        freshness: Freshness = (
            "fresh" if days_old <= 1 else "stale" if days_old <= 3 else "unavailable"
        )

        confidence = derive_confidence(
            history_closes_count=len(closes),
            gaps_in_last_60_days=0,  # placeholder: gap detection is a follow-up
            expected_volatility_annualized=Decimal("0.20"),
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
            forecast_run_id = f"fcst_{uuid4().hex}"
            current_price = closes[-1]
            entry = ForecastEntry(
                forecast_run_id=forecast_run_id,
                conid=conid,
                generated_at=now,
                generated_by_scheduled_run_id=scheduled_run_id,
                horizon_trading_days=horizon_days,
                forecast_valid_until=now
                + timedelta(days=int(horizon_days * 1.4)),  # ≈ calendar days
                method="historical_bootstrap_v1",
                history_window_days=history_window_days,
                history_closes_count=len(closes),
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
                block_reason="insufficient_history",
                expired_at=None,
            )
            try:
                forecast_repo.append(entry)
                forecasts_written += 1
                per_conid.append(
                    _PerConidResult(
                        conid=conid,
                        forecast_run_id=forecast_run_id,
                        label="Geblokkeerd",
                        block_reason="insufficient_history",
                        error=None,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "Failed to persist insufficient-history forecast for %s",
                    conid,
                )
                per_conid.append(
                    _PerConidResult(
                        conid=conid,
                        forecast_run_id=None,
                        label="Geblokkeerd",
                        block_reason="insufficient_history",
                        error=str(exc),
                    )
                )
            continue
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception("Bootstrap failed for %s", conid)
            per_conid.append(
                _PerConidResult(
                    conid=conid,
                    forecast_run_id=None,
                    label="Geblokkeerd",
                    block_reason="data_unavailable",
                    error=str(exc),
                )
            )
            continue

        # Translate to label.
        try:
            user_holds = holdings.holds_conid(
                ibkr_account_id=ibkr_account_id, ibkr_conid=conid
            )
        except Exception:  # noqa: BLE001 — boundary
            user_holds = False

        label_result = translate_to_label(
            forecast=forecast,
            user_holds_position=user_holds,
            freshness=freshness,
            confidence=confidence,
            history_closes_count=len(closes),
        )

        # Persist.
        forecast_run_id = f"fcst_{uuid4().hex}"
        current_price = closes[-1]
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
            forecasts_written += 1
            per_conid.append(
                _PerConidResult(
                    conid=conid,
                    forecast_run_id=forecast_run_id,
                    label=label_result.label,
                    block_reason=label_result.block_reason,
                    error=None,
                )
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception("Failed to persist forecast for %s", conid)
            per_conid.append(
                _PerConidResult(
                    conid=conid,
                    forecast_run_id=None,
                    label=label_result.label,
                    block_reason=label_result.block_reason,
                    error=str(exc),
                )
            )

    return ForecastingStepResult(
        pilot_conids_attempted=len(pilot_conids),
        forecasts_written=forecasts_written,
        per_conid=tuple(per_conid),
    )


__all__ = [
    "ForecastingStepResult",
    "run_forecasting_step",
]
