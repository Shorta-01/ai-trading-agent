"""Task 130: read-only API surface for baseline forecasts + calibration.

Three routes back the Volglijst forecast column + the Dashboard
calibration badge:

* ``GET /forecast/latest?conid=…`` — latest valid forecast for one
  conid + EUR-converted price levels at display time.
* ``GET /forecast/by-account?account_id=…`` — latest valid forecast
  per pilot conid.
* ``GET /calibration/coverage?window_days=90`` — rolling calibration
  stats from the calibration diary.

All routes Pydantic v2; Decimal-as-string on the wire; HTTP 503 +
locked Dutch body when storage is unreachable.
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal

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


# ---- helpers -----------------------------------------------------


def _raise_storage_unavailable() -> None:
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


def _configured_account_id() -> str | None:
    hint = getattr(settings, "ibkr_account_id_hint", None)
    if hint is None:
        return None
    text = str(hint).strip()
    return text or None


def _serialize_forecast(
    forecast: ForecastEntry,
    fx_repo: SqlAlchemyFxRateRepository,
) -> dict[str, object]:
    """Build the full latest-forecast payload incl. price levels + FX."""

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
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
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
            forecast = forecast_repo.get_latest_valid_for_conid(
                conid=conid, now=datetime.now(UTC)
            )
            if forecast is None:
                raise HTTPException(
                    status_code=404,
                    detail="Geen geldige voorspelling voor dit asset.",
                )
            return _serialize_forecast(forecast, fx_repo)
    except StorageConnectionError:
        _raise_storage_unavailable()
    raise HTTPException(status_code=503, detail=STORAGE_UNAVAILABLE_DETAIL)


@router.get(
    "/forecast/by-account", response_model=ForecastByAccountResponse
)
def read_forecasts_by_account(
    account_id: str | None = Query(default=None),
) -> dict[str, object]:
    effective_account = account_id or _configured_account_id()
    if effective_account is None:
        return {
            "account_id": None,
            "items": [],
            "safe_for_action_drafts": False,
            "safe_for_orders": False,
        }
    pilot_conids_csv = getattr(settings, "forecast_pilot_conids", None)
    pilot_conids: tuple[str, ...]
    if pilot_conids_csv:
        pilot_conids = tuple(
            c.strip() for c in str(pilot_conids_csv).split(",") if c.strip()
        )
    else:
        pilot_conids = ("ASML.AS",)

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
            for conid in pilot_conids:
                latest = forecast_repo.get_latest_valid_for_conid(
                    conid=conid, now=now
                )
                if latest is None:
                    continue
                items.append(
                    {
                        "conid": latest.conid,
                        "label": latest.label,
                        "confidence_level": latest.confidence_level,
                        "generated_at": latest.generated_at.isoformat(),
                        "p50_log_return": str(latest.p50_log_return),
                        "prob_positive": str(latest.prob_positive),
                        # Position-held lookup is a follow-up; default
                        # False so the UI doesn't claim ownership it
                        # can't verify.
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
