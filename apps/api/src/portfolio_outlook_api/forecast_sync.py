"""Forecast sync orchestrator.

Reads the latest IBKR position snapshots and the latest market-data snapshots,
fetches historical bars from EODHD per position, runs the deterministic
baseline GBM forecaster (``packages/portfolio/baseline_forecast``), and
persists the resulting forecasts. All persisted rows have
``safe_for_analysis``/``safe_for_suggestions``/``safe_for_action_drafts``
set to ``False`` — this slice produces forecasts but no suggestions.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from ai_trading_agent_storage import (
    AssetForecastRecord,
    IbkrPositionSnapshotRecord,
    MarketDataBarRecord,
    MarketDataLatestSnapshotRecord,
)
from portfolio_outlook_portfolio import (
    BASELINE_FORECAST_MODEL_CODE,
    BASELINE_FORECAST_MODEL_VERSION,
    BaselineForecast,
    HistoricalBar,
    compute_baseline_forecast,
)

from portfolio_outlook_api.eodhd_client import (
    EodhdAuthError,
    EodhdBar,
    EodhdClientError,
    EodhdHistoricalProvider,
    EodhdNotFoundError,
    EodhdRateLimitError,
)
from portfolio_outlook_api.market_data_sync import (
    PROVIDER_CODE_EODHD,
    map_ibkr_exchange_to_eodhd,
)

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ForecastSyncReport:
    requested_at: datetime
    completed_at: datetime
    model_code: str
    model_version: str
    horizon_trading_days: int
    asset_total: int
    asset_success: int
    asset_skipped_unknown_exchange: int
    asset_skipped_missing_market_data: int
    asset_failed: int
    forecasts_persisted: int
    bars_persisted: int
    failures: tuple[dict[str, str], ...]
    status_nl: str
    help_nl: str


class _MarketDataBarRepoProtocol(Protocol):
    def save_market_data_bars(
        self, records: list[MarketDataBarRecord]
    ) -> object: ...


class _AssetForecastRepoProtocol(Protocol):
    def save_asset_forecast(self, record: AssetForecastRecord) -> object: ...


def _explanation_nl_for_bar(symbol: str, suffix: str) -> str:
    return (
        f"EODHD historische bar ({symbol}.{suffix}); read-only opslag, "
        "geen analysevrijgave, geen suggesties, geen orders."
    )


def _build_bar_record(
    *,
    position: IbkrPositionSnapshotRecord,
    bar: EodhdBar,
    suffix: str,
    received_at: datetime,
    stored_at: datetime,
) -> MarketDataBarRecord | None:
    if bar.close_price is None:
        return None
    return MarketDataBarRecord(
        bar_id=f"md_bar_eodhd_{uuid4().hex}",
        ibkr_conid=position.conid or "",
        symbol=position.symbol,
        currency=position.currency,
        exchange=position.exchange,
        primary_exchange=position.primary_exchange,
        provider_code=PROVIDER_CODE_EODHD,
        bar_date=bar.bar_date,
        interval_code="1day",
        open_price=bar.open_price,
        high_price=bar.high_price,
        low_price=bar.low_price,
        close_price=bar.close_price,
        adjusted_close_price=bar.adjusted_close,
        volume=bar.volume,
        provider_as_of=None,
        received_at=received_at,
        stored_at=stored_at,
        source_type="eodhd_eod",
        explanation_nl=_explanation_nl_for_bar(position.symbol, suffix),
    )


def _build_forecast_record(
    *,
    position: IbkrPositionSnapshotRecord,
    forecast: BaselineForecast,
    generated_at: datetime,
    valid_until: datetime,
) -> AssetForecastRecord:
    return AssetForecastRecord(
        forecast_id=f"forecast_{uuid4().hex}",
        ibkr_conid=position.conid or "",
        symbol=position.symbol,
        currency=position.currency,
        model_code=BASELINE_FORECAST_MODEL_CODE,
        model_version=BASELINE_FORECAST_MODEL_VERSION,
        horizon_days=forecast.horizon_days,
        generated_at=generated_at,
        valid_until=valid_until,
        data_points_used=forecast.data_points_used,
        history_first_bar_date=forecast.history_first_bar_date,
        history_last_bar_date=forecast.history_last_bar_date,
        current_price=forecast.current_price,
        expected_return_pct=forecast.expected_return_pct,
        p10_price=forecast.p10_price,
        p50_price=forecast.p50_price,
        p90_price=forecast.p90_price,
        prob_gain=forecast.prob_gain,
        prob_loss=forecast.prob_loss,
        prob_loss_gt_5pct=forecast.prob_loss_gt_5pct,
        prob_loss_gt_10pct=forecast.prob_loss_gt_10pct,
        prob_gain_gt_5pct=forecast.prob_gain_gt_5pct,
        prob_gain_gt_10pct=forecast.prob_gain_gt_10pct,
        expected_volatility_annual=forecast.expected_volatility_annual,
        downside_risk_score=forecast.downside_risk_score,
        confidence_score=forecast.confidence_score,
        direction_label=forecast.direction_label,
        direction_label_nl=forecast.direction_label_nl,
        explanation_nl=forecast.explanation_nl,
        status=forecast.status,
        blocking_reason=forecast.blocking_reason,
    )


def _unique_positions(
    positions: Iterable[IbkrPositionSnapshotRecord], max_assets: int
) -> list[IbkrPositionSnapshotRecord]:
    seen: set[str] = set()
    unique: list[IbkrPositionSnapshotRecord] = []
    for position in positions:
        conid = (position.conid or "").strip()
        if not conid or conid in seen:
            continue
        seen.add(conid)
        unique.append(position)
        if len(unique) >= max_assets:
            break
    return unique


def sync_forecasts(
    *,
    provider: EodhdHistoricalProvider,
    bar_repo: _MarketDataBarRepoProtocol,
    forecast_repo: _AssetForecastRepoProtocol,
    positions: list[IbkrPositionSnapshotRecord],
    market_snapshots_by_conid: dict[str, MarketDataLatestSnapshotRecord],
    history_lookback_days: int,
    horizon_trading_days: int,
    minimum_bars_required: int,
    max_assets: int,
    valid_minutes: int,
) -> ForecastSyncReport:
    """Run one full forecast cycle and persist every successful row."""

    requested_at = datetime.now(UTC)
    asset_success = 0
    asset_failed = 0
    asset_skipped_unknown_exchange = 0
    asset_skipped_missing_market_data = 0
    forecasts_persisted = 0
    bars_persisted = 0
    failures: list[dict[str, str]] = []

    unique_positions = _unique_positions(positions, max_assets)
    today = requested_at.date()
    from_date = today - timedelta(days=history_lookback_days)

    for position in unique_positions:
        symbol = (position.symbol or "").strip()
        conid = (position.conid or "").strip()
        if not symbol or not conid:
            asset_failed += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "reason": "missing_symbol_or_conid",
                }
            )
            continue
        suffix = map_ibkr_exchange_to_eodhd(position.primary_exchange or position.exchange)
        if suffix is None:
            asset_skipped_unknown_exchange += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": symbol,
                    "primary_exchange": position.primary_exchange or position.exchange or "",
                    "reason": "unknown_exchange",
                }
            )
            continue

        market_snapshot = market_snapshots_by_conid.get(conid)
        current_price = market_snapshot.last_price if market_snapshot is not None else None
        if current_price is None or current_price <= 0:
            asset_skipped_missing_market_data += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": symbol,
                    "reason": "missing_current_price",
                }
            )
            continue

        eodhd_symbol = f"{symbol}.{suffix}"
        try:
            bars = provider.fetch_eod_bars(
                eodhd_symbol,
                from_date=from_date,
                to_date=today,
            )
        except EodhdAuthError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": eodhd_symbol,
                    "reason": "auth_error",
                    "detail": str(exc),
                }
            )
            break
        except EodhdRateLimitError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": eodhd_symbol,
                    "reason": "rate_limited",
                    "detail": str(exc),
                }
            )
            break
        except EodhdNotFoundError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": eodhd_symbol,
                    "reason": "not_found",
                    "detail": str(exc),
                }
            )
            continue
        except EodhdClientError as exc:
            asset_failed += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": eodhd_symbol,
                    "reason": "provider_error",
                    "detail": str(exc),
                }
            )
            continue

        if len(bars) < minimum_bars_required:
            asset_failed += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": eodhd_symbol,
                    "reason": "insufficient_history",
                    "detail": f"only {len(bars)} bars returned",
                }
            )
            continue

        received_at = datetime.now(UTC)
        bar_records: list[MarketDataBarRecord] = []
        for bar in bars:
            record = _build_bar_record(
                position=position,
                bar=bar,
                suffix=suffix,
                received_at=received_at,
                stored_at=received_at,
            )
            if record is not None:
                bar_records.append(record)
        if bar_records:
            bar_repo.save_market_data_bars(bar_records)
            bars_persisted += len(bar_records)

        historical_bars: list[HistoricalBar] = [
            HistoricalBar(
                bar_date=record.bar_date,
                close_price=record.adjusted_close_price or record.close_price,
            )
            for record in bar_records
        ]

        forecast = compute_baseline_forecast(
            bars=historical_bars,
            current_price=current_price,
            horizon_trading_days=horizon_trading_days,
            minimum_bars_required=minimum_bars_required,
        )

        generated_at = datetime.now(UTC)
        valid_until = generated_at + timedelta(minutes=valid_minutes)
        forecast_record = _build_forecast_record(
            position=position,
            forecast=forecast,
            generated_at=generated_at,
            valid_until=valid_until,
        )
        forecast_repo.save_asset_forecast(forecast_record)
        forecasts_persisted += 1
        if forecast.status == "ready":
            asset_success += 1
        else:
            asset_failed += 1
            failures.append(
                {
                    "kind": "forecast",
                    "conid": conid,
                    "symbol": eodhd_symbol,
                    "reason": forecast.blocking_reason or "forecast_blocked",
                }
            )

    completed_at = datetime.now(UTC)
    if forecasts_persisted == 0:
        status_nl = "Voorspellingssync zonder resultaat"
        help_nl = "Geen voorspellingen opgeslagen; controleer failures."
    elif asset_failed > 0 or asset_skipped_unknown_exchange > 0:
        status_nl = "Voorspellingssync gedeeltelijk voltooid"
        help_nl = (
            "Sommige assets konden geen voorspelling produceren; "
            "details staan in 'failures'."
        )
    else:
        status_nl = "Voorspellingssync voltooid"
        help_nl = "Alle vereiste voorspellingen zijn opgeslagen."

    return ForecastSyncReport(
        requested_at=requested_at,
        completed_at=completed_at,
        model_code=BASELINE_FORECAST_MODEL_CODE,
        model_version=BASELINE_FORECAST_MODEL_VERSION,
        horizon_trading_days=horizon_trading_days,
        asset_total=len(unique_positions),
        asset_success=asset_success,
        asset_skipped_unknown_exchange=asset_skipped_unknown_exchange,
        asset_skipped_missing_market_data=asset_skipped_missing_market_data,
        asset_failed=asset_failed,
        forecasts_persisted=forecasts_persisted,
        bars_persisted=bars_persisted,
        failures=tuple(failures),
        status_nl=status_nl,
        help_nl=help_nl,
    )


def serialize_forecast_for_response(record: AssetForecastRecord) -> dict[str, object]:
    """Serialise an ``AssetForecastRecord`` to a JSON-friendly dict for the
    ``/forecasts/*`` endpoints. ``Decimal`` is stringified to keep precision."""

    def _money(value: Decimal) -> str:
        return str(value)

    return {
        "forecast_id": record.forecast_id,
        "ibkr_conid": record.ibkr_conid,
        "symbol": record.symbol,
        "currency": record.currency,
        "model_code": record.model_code,
        "model_version": record.model_version,
        "horizon_days": record.horizon_days,
        "generated_at": record.generated_at.isoformat(),
        "valid_until": record.valid_until.isoformat(),
        "data_points_used": record.data_points_used,
        "history_first_bar_date": _iso_date_or_none(record.history_first_bar_date),
        "history_last_bar_date": _iso_date_or_none(record.history_last_bar_date),
        "current_price": _money(record.current_price),
        "expected_return_pct": _money(record.expected_return_pct),
        "p10_price": _money(record.p10_price),
        "p50_price": _money(record.p50_price),
        "p90_price": _money(record.p90_price),
        "prob_gain": _money(record.prob_gain),
        "prob_loss": _money(record.prob_loss),
        "prob_loss_gt_5pct": _money(record.prob_loss_gt_5pct),
        "prob_loss_gt_10pct": _money(record.prob_loss_gt_10pct),
        "prob_gain_gt_5pct": _money(record.prob_gain_gt_5pct),
        "prob_gain_gt_10pct": _money(record.prob_gain_gt_10pct),
        "expected_volatility_annual": _money(record.expected_volatility_annual),
        "downside_risk_score": _money(record.downside_risk_score),
        "confidence_score": _money(record.confidence_score),
        "direction_label": record.direction_label,
        "direction_label_nl": record.direction_label_nl,
        "explanation_nl": record.explanation_nl,
        "status": record.status,
        "blocking_reason": record.blocking_reason,
        "safe_for_analysis": False,
        "safe_for_suggestions": False,
        "safe_for_action_drafts": False,
    }


def _iso_date_or_none(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None
