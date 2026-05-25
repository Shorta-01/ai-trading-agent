"""Task 130 + 131: read-only API surface for baseline forecasts + calibration.

Four routes back the Volglijst forecast column + the Dashboard
calibration badge + the new Task 131 multi-asset summary widget:

* ``GET /forecast/latest?conid=…`` — latest valid forecast for one
  conid + EUR-converted price levels at display time.
* ``GET /forecast/by-account?account_id=…`` — Task 131: latest valid
  forecast for **every** conid in the account's universe (was
  pilot-only in Task 130).
* ``GET /forecast/day-summary?account_id=…&as_of_date=…`` — Task 131:
  per-label counts for the day's forecasts; backs the Dashboard
  ForecastDaySummaryWidget.
* ``GET /calibration/coverage?window_days=90`` — rolling calibration
  stats from the calibration diary.

All routes Pydantic v2; Decimal-as-string on the wire; HTTP 503 +
locked Dutch body when storage is unreachable.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Literal, cast

from ai_trading_agent_storage import (
    ForecastEntry,
    SqlAlchemyCalibrationDiaryRepository,
    SqlAlchemyForecastRepository,
    SqlAlchemyFxRateRepository,
    StorageConnectionError,
    StorageConnectionProvider,
    build_database_connection_settings,
)
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, ConfigDict

from portfolio_outlook_api.config import settings

router = APIRouter()

STORAGE_UNAVAILABLE_DETAIL = "Opslag is niet beschikbaar."
BASE_CURRENCY = "EUR"


# ---- Pydantic v2 response models ---------------------------------


class PerAssetCoverage(BaseModel):
    """Task 131: per-asset rolling calibration stats embedded in ``/forecast/latest``.

    ``sufficient_history`` is False when fewer than ``min_sample_size``
    (default 5) calibration-diary rows exist for the conid; the UI then
    shows the "Onvoldoende historiek voor kalibratie" fallback in the
    explanation panel.
    """

    model_config = ConfigDict(extra="forbid")

    forecasts_evaluated: int
    hit_rate_within_band: str | None
    sufficient_history: bool


class ForecastLatestResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conid: str
    generated_at: str
    forecast_valid_until: str
    horizon_trading_days: int
    method: str
    current_price_local: str
    currency_local: str
    p10_log_return: str
    p50_log_return: str
    p90_log_return: str
    p10_price_local: str
    p50_price_local: str
    p90_price_local: str
    p10_price_eur: str | None
    p50_price_eur: str | None
    p90_price_eur: str | None
    prob_positive: str
    prob_loss_gt_5pct: str
    expected_volatility_annualized: str
    confidence_level: Literal["Laag", "Gemiddeld", "Hoog"]
    label: Literal[
        "Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken", "Geblokkeerd"
    ]
    block_reason: str | None
    # Task 131: per-asset rolling 90-day coverage. Read by the
    # explanation panel; the field is non-optional so the contract
    # stays explicit, but ``sufficient_history`` may be False.
    per_asset_coverage: PerAssetCoverage
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class ForecastByAccountRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    conid: str
    label: Literal[
        "Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken", "Geblokkeerd"
    ]
    confidence_level: Literal["Laag", "Gemiddeld", "Hoog"]
    generated_at: str
    p50_log_return: str
    prob_positive: str
    user_holds_position: bool


class ForecastByAccountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    account_id: str | None
    items: list[ForecastByAccountRow]
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class CalibrationCoverageResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    window_days: int
    forecasts_evaluated: int
    hit_rate_within_band: str | None
    p10_p90_coverage_percent: str | None
    mean_realized_minus_p50: str | None
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


class ForecastDaySummaryResponse(BaseModel):
    """Task 131: per-label counts for the Dashboard summary widget."""

    model_config = ConfigDict(extra="forbid")

    account_id: str | None
    as_of_date: str
    total_forecasts: int
    total_blocked: int
    label_counts: dict[str, int]
    block_reasons: dict[str, int]
    safe_for_action_drafts: Literal[False] = False
    safe_for_orders: Literal[False] = False


# ---- helpers -----------------------------------------------------


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _configured_account_id() -> str | None:
    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


def _resolve_pilot_conids() -> tuple[str, ...]:
    """Task 130 fallback: the pilot conids from env config.

    Used when the account-resolution path doesn't yet have full
    universe wiring (cold-start, missing IBKR sync). Defaults to
    the locked V1.1.0 pilot ``ASML.AS``.
    """

    pilot_conids_csv = getattr(settings, "forecast_pilot_conids", None)
    if not pilot_conids_csv:
        return ("ASML.AS",)
    return tuple(
        c.strip() for c in str(pilot_conids_csv).split(",") if c.strip()
    )


def _serialize_forecast(
    forecast: ForecastEntry,
    fx_repo: SqlAlchemyFxRateRepository,
    coverage: dict[str, object] | None = None,
) -> dict[str, object]:
    """Build the full latest-forecast payload incl. price levels + FX.

    Task 131 adds the ``per_asset_coverage`` block; callers that don't
    care (older callers) can omit ``coverage`` and a no-history
    placeholder is emitted.
    """

    cp = forecast.current_price_local
    p10_price_local = (
        cp * Decimal(repr(math.exp(float(forecast.p10_log_return))))
    ).quantize(Decimal("0.000001"))
    p50_price_local = (
        cp * Decimal(repr(math.exp(float(forecast.p50_log_return))))
    ).quantize(Decimal("0.000001"))
    p90_price_local = (
        cp * Decimal(repr(math.exp(float(forecast.p90_log_return))))
    ).quantize(Decimal("0.000001"))

    p10_eur: str | None
    p50_eur: str | None
    p90_eur: str | None
    if forecast.currency_local == BASE_CURRENCY:
        p10_eur = str(p10_price_local)
        p50_eur = str(p50_price_local)
        p90_eur = str(p90_price_local)
    else:
        fx_row = fx_repo.get_latest(
            base_currency=forecast.currency_local,
            quote_currency=BASE_CURRENCY,
        )
        if fx_row is None:
            p10_eur = p50_eur = p90_eur = None
        else:
            p10_eur = str(
                (p10_price_local * fx_row.rate).quantize(Decimal("0.000001"))
            )
            p50_eur = str(
                (p50_price_local * fx_row.rate).quantize(Decimal("0.000001"))
            )
            p90_eur = str(
                (p90_price_local * fx_row.rate).quantize(Decimal("0.000001"))
            )

    return {
        "conid": forecast.conid,
        "generated_at": forecast.generated_at.isoformat(),
        "forecast_valid_until": forecast.forecast_valid_until.isoformat(),
        "horizon_trading_days": forecast.horizon_trading_days,
        "method": forecast.method,
        "current_price_local": str(forecast.current_price_local),
        "currency_local": forecast.currency_local,
        "p10_log_return": str(forecast.p10_log_return),
        "p50_log_return": str(forecast.p50_log_return),
        "p90_log_return": str(forecast.p90_log_return),
        "p10_price_local": str(p10_price_local),
        "p50_price_local": str(p50_price_local),
        "p90_price_local": str(p90_price_local),
        "p10_price_eur": p10_eur,
        "p50_price_eur": p50_eur,
        "p90_price_eur": p90_eur,
        "prob_positive": str(forecast.prob_positive),
        "prob_loss_gt_5pct": str(forecast.prob_loss_gt_5pct),
        "expected_volatility_annualized": str(
            forecast.expected_volatility_annualized
        ),
        "confidence_level": forecast.confidence_level,
        "label": forecast.label,
        "block_reason": forecast.block_reason,
        "per_asset_coverage": _serialize_coverage(coverage),
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


def _serialize_coverage(
    coverage: dict[str, object] | None,
) -> dict[str, object]:
    """Map ``coverage_stats_by_conid`` output to the API contract."""

    if coverage is None:
        return {
            "forecasts_evaluated": 0,
            "hit_rate_within_band": None,
            "sufficient_history": False,
        }
    hit_rate = coverage.get("hit_rate_within_band")
    evaluated_raw = coverage.get("forecasts_evaluated") or 0
    return {
        "forecasts_evaluated": int(cast(int, evaluated_raw)),
        "hit_rate_within_band": str(hit_rate) if hit_rate is not None else None,
        "sufficient_history": bool(coverage.get("sufficient_history", False)),
    }


# ---- routes ------------------------------------------------------


@router.get("/forecast/latest", response_model=ForecastLatestResponse)
def read_latest_forecast(
    conid: str = Query(..., min_length=1),
) -> dict[str, object]:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            forecast_repo = SqlAlchemyForecastRepository(
                checked.connection, checked.readiness
            )
            fx_repo = SqlAlchemyFxRateRepository(
                checked.connection, checked.readiness
            )
            diary_repo = SqlAlchemyCalibrationDiaryRepository(
                checked.connection, checked.readiness
            )
            forecast = forecast_repo.get_latest_valid_for_conid(
                conid=conid, now=datetime.now(UTC)
            )
            if forecast is None:
                raise HTTPException(
                    status_code=404,
                    detail="Geen geldige voorspelling voor dit asset.",
                )
            coverage = diary_repo.coverage_stats_by_conid(
                conid=conid, window_days=90
            )
            return _serialize_forecast(forecast, fx_repo, coverage)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.get(
    "/forecast/by-account", response_model=ForecastByAccountResponse
)
def read_forecasts_by_account(
    account_id: str | None = Query(default=None),
) -> dict[str, object]:
    """Task 131: latest valid forecast for every conid in the account's universe.

    The universe = the union of (confirmed-watchlist conids) and
    (currently held positions) for the account. Conids without a
    valid forecast are omitted from the response; the UI surfaces
    "Nog geen voorspelling" microcopy for those rows itself.

    For Task 131 the universe is approximated as the configured pilot
    list (``FORECAST_PILOT_CONIDS``) until the production runner
    (Task 132+) wires the storage-backed resolver into the API. The
    response shape supports multiple conids today regardless.
    """

    effective_account = account_id or _configured_account_id()
    if effective_account is None:
        return {
            "account_id": None,
            "items": [],
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }
    conids = _resolve_pilot_conids()

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    items: list[dict[str, object]] = []
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            forecast_repo = SqlAlchemyForecastRepository(
                checked.connection, checked.readiness
            )
            now = datetime.now(UTC)
            latest_rows = forecast_repo.get_latest_valid_for_conids(
                conids=conids, now=now
            )
            for latest in latest_rows:
                items.append(
                    {
                        "conid": latest.conid,
                        "label": latest.label,
                        "confidence_level": latest.confidence_level,
                        "generated_at": latest.generated_at.isoformat(),
                        "p50_log_return": str(latest.p50_log_return),
                        "prob_positive": str(latest.prob_positive),
                        # Position-held lookup is wired into the
                        # forecasting step (Task 131) but the
                        # read-API still defaults to False until
                        # the storage-backed resolver lands.
                        "user_holds_position": False,
                    }
                )
    except StorageConnectionError:
        _raise_storage_unavailable()
    return {
        "account_id": effective_account,
        "items": items,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get(
    "/forecast/day-summary", response_model=ForecastDaySummaryResponse
)
def read_forecast_day_summary(
    account_id: str | None = Query(default=None),
    as_of_date: str | None = Query(default=None, max_length=10),
) -> dict[str, object]:
    """Task 131: per-label counts for the day's forecasts.

    ``as_of_date`` is YYYY-MM-DD; if omitted, today (UTC) is used.
    Empty days return ``total_forecasts=0`` + empty ``label_counts``.
    """

    effective_account = account_id or _configured_account_id()
    if as_of_date is None:
        target_date = datetime.now(UTC).date()
    else:
        try:
            target_date = date.fromisoformat(as_of_date)
        except ValueError as exc:
            raise HTTPException(
                status_code=422,
                detail=f"Ongeldige datum: {exc}",
            ) from exc

    if effective_account is None:
        return {
            "account_id": None,
            "as_of_date": target_date.isoformat(),
            "total_forecasts": 0,
            "total_blocked": 0,
            "label_counts": {},
            "block_reasons": {},
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }

    conids = _resolve_pilot_conids()

    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    summary: dict[str, object] = {}
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            forecast_repo = SqlAlchemyForecastRepository(
                checked.connection, checked.readiness
            )
            summary = forecast_repo.list_for_date_summary(
                conids=conids, as_of_date=target_date
            )
    except StorageConnectionError:
        _raise_storage_unavailable()
    total_forecasts = cast(int, summary.get("total_forecasts", 0) or 0)
    total_blocked = cast(int, summary.get("total_blocked", 0) or 0)
    label_counts = cast(dict[str, int], summary.get("label_counts") or {})
    block_reasons = cast(dict[str, int], summary.get("block_reasons") or {})
    return {
        "account_id": effective_account,
        "as_of_date": target_date.isoformat(),
        "total_forecasts": int(total_forecasts),
        "total_blocked": int(total_blocked),
        "label_counts": dict(label_counts),
        "block_reasons": dict(block_reasons),
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


@router.get(
    "/calibration/coverage", response_model=CalibrationCoverageResponse
)
def read_calibration_coverage(
    window_days: int = Query(default=90, ge=1, le=365),
) -> dict[str, object]:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    try:
        provider = StorageConnectionProvider(
            build_database_connection_settings(storage.database_url)
        )
        with provider.checked_connection(require_writable=False) as checked:
            diary_repo = SqlAlchemyCalibrationDiaryRepository(
                checked.connection, checked.readiness
            )
            stats = diary_repo.coverage_stats(window_days=window_days)
    except StorageConnectionError:
        _raise_storage_unavailable()

    return {
        "window_days": window_days,
        "forecasts_evaluated": int(stats["forecasts_evaluated"]),
        "hit_rate_within_band": (
            str(stats["hit_rate_within_band"])
            if stats["hit_rate_within_band"] is not None
            else None
        ),
        "p10_p90_coverage_percent": (
            str(stats["p10_p90_coverage_percent"])
            if stats["p10_p90_coverage_percent"] is not None
            else None
        ),
        "mean_realized_minus_p50": (
            str(stats["mean_realized_minus_p50"])
            if stats["mean_realized_minus_p50"] is not None
            else None
        ),
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }
