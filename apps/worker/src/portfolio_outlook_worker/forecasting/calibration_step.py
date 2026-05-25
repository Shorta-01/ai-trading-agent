"""Task 130: scheduler-driven calibration step.

Called by the orchestrator on ``pre_briefing`` 06:00 fires. For each
forecast whose ``forecast_valid_until`` is in the past AND
``expired_at`` is still NULL:

1. Look up the close on the as-of-or-after target date.
2. Compute realized log-return = ln(realized_close / current_price).
3. Decide the locked ``hit_status`` from p10/p90.
4. Append one ``CalibrationDiaryEntry`` row.
5. Mark the forecast's ``expired_at`` so it doesn't re-evaluate.
"""

from __future__ import annotations

import logging
import math
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Protocol

from ai_trading_agent_storage import (
    CalibrationDiaryEntry,
    SqlAlchemyCalibrationDiaryRepository,
    SqlAlchemyForecastRepository,
)

logger = logging.getLogger(__name__)


class _RealizedCloseProviderProtocol(Protocol):
    """Storage adapter: returns the realized close on/after target_date."""

    def get_close_on_or_after(
        self, *, ibkr_conid: str, target_date: date
    ) -> Decimal | None: ...


@dataclass(frozen=True)
class _PerForecastResult:
    forecast_run_id: str
    written: bool
    hit_status: str | None
    error: str | None


@dataclass(frozen=True)
class CalibrationStepResult:
    forecasts_evaluated: int
    diary_rows_written: int
    per_forecast: tuple[_PerForecastResult, ...] = field(default_factory=tuple)

    def as_audit_dict(self) -> dict[str, object]:
        return {
            "forecasts_evaluated": self.forecasts_evaluated,
            "diary_rows_written": self.diary_rows_written,
        }


def _hit_status_for(
    *, realized: Decimal, p10: Decimal, p90: Decimal
) -> str:
    if realized > p90:
        return "realized_above_p90"
    if realized < p10:
        return "realized_below_p10"
    if p10 <= realized <= p90:
        return "realized_within_p10_p90"
    return "realized_outside_band"


def run_calibration_step(
    *,
    forecast_repo: SqlAlchemyForecastRepository,
    diary_repo: SqlAlchemyCalibrationDiaryRepository,
    realized_close_provider: _RealizedCloseProviderProtocol,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
    max_to_evaluate: int = 100,
) -> CalibrationStepResult:
    """Evaluate every expired forecast that hasn't been processed yet."""

    now = now_provider()
    pending = forecast_repo.list_expired_unprocessed(
        now=now, limit=max_to_evaluate
    )
    diary_rows_written = 0
    per_forecast: list[_PerForecastResult] = []

    for forecast in pending.records:
        try:
            target = forecast.forecast_valid_until.date()
            realized_close = realized_close_provider.get_close_on_or_after(
                ibkr_conid=forecast.conid, target_date=target
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "Failed to fetch realized close for %s", forecast.forecast_run_id
            )
            per_forecast.append(
                _PerForecastResult(
                    forecast_run_id=forecast.forecast_run_id,
                    written=False,
                    hit_status=None,
                    error=str(exc),
                )
            )
            continue
        if realized_close is None:
            per_forecast.append(
                _PerForecastResult(
                    forecast_run_id=forecast.forecast_run_id,
                    written=False,
                    hit_status=None,
                    error="realized_close_not_found",
                )
            )
            continue

        if forecast.current_price_local <= 0:
            per_forecast.append(
                _PerForecastResult(
                    forecast_run_id=forecast.forecast_run_id,
                    written=False,
                    hit_status=None,
                    error="current_price_local_not_positive",
                )
            )
            continue

        realized_log = Decimal(
            repr(
                math.log(
                    float(realized_close) / float(forecast.current_price_local)
                )
            )
        ).quantize(Decimal("0.0000000001"))
        hit_status = _hit_status_for(
            realized=realized_log,
            p10=forecast.p10_log_return,
            p90=forecast.p90_log_return,
        )

        try:
            diary_repo.append(
                CalibrationDiaryEntry(
                    forecast_run_id=forecast.forecast_run_id,
                    evaluated_at=now,
                    realized_log_return=realized_log,
                    hit_status=hit_status,
                    realized_close_price=realized_close,
                )
            )
            forecast_repo.mark_expired(
                forecast_run_id=forecast.forecast_run_id, expired_at=now
            )
            diary_rows_written += 1
            per_forecast.append(
                _PerForecastResult(
                    forecast_run_id=forecast.forecast_run_id,
                    written=True,
                    hit_status=hit_status,
                    error=None,
                )
            )
        except Exception as exc:  # noqa: BLE001 — boundary
            logger.exception(
                "Failed to persist calibration row for %s",
                forecast.forecast_run_id,
            )
            per_forecast.append(
                _PerForecastResult(
                    forecast_run_id=forecast.forecast_run_id,
                    written=False,
                    hit_status=hit_status,
                    error=str(exc),
                )
            )

    return CalibrationStepResult(
        forecasts_evaluated=len(pending.records),
        diary_rows_written=diary_rows_written,
        per_forecast=tuple(per_forecast),
    )


__all__ = [
    "CalibrationStepResult",
    "run_calibration_step",
]
