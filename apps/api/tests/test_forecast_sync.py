"""Tests for the forecast sync orchestrator.

Fake EODHD provider + fake repos so no network or real DB is needed. We
verify every branch: unknown exchange skip, missing market price skip,
insufficient-history failure, auth error short-circuit, and the happy path
where a baseline forecast is computed and persisted with hard-False safety
booleans.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from ai_trading_agent_storage import (
    AssetForecastRecord,
    IbkrPositionSnapshotRecord,
    MarketDataBarRecord,
    MarketDataLatestSnapshotRecord,
)

from portfolio_outlook_api.eodhd_client import (
    EodhdAuthError,
    EodhdBar,
    EodhdNotFoundError,
)
from portfolio_outlook_api.forecast_sync import (
    serialize_forecast_for_response,
    sync_forecasts,
)

_NOW = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)


def _position(
    *,
    conid: str,
    symbol: str,
    primary: str | None,
    currency: str = "USD",
) -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id=f"pos_{conid}",
        sync_run_id="ibkr-sync-test",
        account_ref="DU12345",
        conid=conid,
        symbol=symbol,
        security_type="STK",
        currency=currency,
        exchange="SMART",
        primary_exchange=primary,
        quantity=Decimal("5"),
        average_cost=Decimal("100"),
        received_at=_NOW,
        stored_at=_NOW,
    )


def _market_snapshot(conid: str, last_price: str) -> MarketDataLatestSnapshotRecord:
    return MarketDataLatestSnapshotRecord(
        snapshot_id=f"md_{conid}",
        ibkr_conid=conid,
        symbol="X",
        currency="USD",
        asset_class="STK",
        exchange=None,
        primary_exchange=None,
        provider_code="eodhd",
        provider_environment="real",
        provider_account_mode="none",
        market_data_type="eod",
        requested_at=_NOW,
        received_at=_NOW,
        provider_as_of=_NOW,
        stored_at=_NOW,
        last_price=Decimal(last_price),
        bid_price=None,
        ask_price=None,
        close_price=Decimal(last_price),
        day_change_percent=None,
        status="snapshot_available",
        freshness_status="fresh",
        explanation_nl="test",
        request_log_id=None,
        provider_source_id=None,
        freshness_audit_id=None,
    )


def _realistic_bars(
    *,
    initial: float,
    annual_drift: float,
    annual_sigma: float,
    n_bars: int,
    end_date: date = date(2025, 5, 23),
    trading_days_per_year: int = 252,
) -> list[EodhdBar]:
    """Generate deterministic synthetic EOD bars with target moments."""

    mu = annual_drift / trading_days_per_year
    sigma = annual_sigma / math.sqrt(trading_days_per_year)
    offsets = (1.4142, -1.4142, 0.7071, -0.7071, 0.0)
    closes: list[float] = [initial]
    for i in range(1, n_bars):
        closes.append(closes[-1] * math.exp(mu + sigma * offsets[(i - 1) % 5]))
    start = end_date - timedelta(days=n_bars - 1)
    return [
        EodhdBar(
            bar_date=start + timedelta(days=i),
            open_price=Decimal(repr(close)),
            high_price=Decimal(repr(close)),
            low_price=Decimal(repr(close)),
            close_price=Decimal(repr(close)),
            adjusted_close=Decimal(repr(close)),
            volume=Decimal("1000000"),
        )
        for i, close in enumerate(closes)
    ]


class FakeBarRepo:
    def __init__(self) -> None:
        self.saved: list[MarketDataBarRecord] = []

    def save_market_data_bars(self, records: list[MarketDataBarRecord]) -> object:
        self.saved.extend(records)
        return None


class FakeForecastRepo:
    def __init__(self) -> None:
        self.saved: list[AssetForecastRecord] = []

    def save_asset_forecast(self, record: AssetForecastRecord) -> object:
        self.saved.append(record)
        return None


class FakeHistoricalProvider:
    def __init__(
        self,
        *,
        bars: dict[str, list[EodhdBar]] | None = None,
        errors: dict[str, Exception] | None = None,
    ) -> None:
        self.bars = bars or {}
        self.errors = errors or {}
        self.calls: list[tuple[str, date, date]] = []

    def fetch_eod_bars(
        self,
        eodhd_symbol: str,
        *,
        from_date: date,
        to_date: date,
    ) -> list[EodhdBar]:
        self.calls.append((eodhd_symbol, from_date, to_date))
        if eodhd_symbol in self.errors:
            raise self.errors[eodhd_symbol]
        if eodhd_symbol not in self.bars:
            raise EodhdNotFoundError(eodhd_symbol)
        return list(self.bars[eodhd_symbol])


def test_happy_path_persists_bars_and_forecasts_with_safety_booleans_false() -> None:
    bars = _realistic_bars(
        initial=100.0,
        annual_drift=0.08,
        annual_sigma=0.20,
        n_bars=120,
    )
    provider = FakeHistoricalProvider(bars={"AAPL.US": bars})
    bar_repo = FakeBarRepo()
    forecast_repo = FakeForecastRepo()
    positions = [_position(conid="265598", symbol="AAPL", primary="NASDAQ")]

    report = sync_forecasts(
        provider=provider,
        bar_repo=bar_repo,
        forecast_repo=forecast_repo,
        positions=positions,
        market_snapshots_by_conid={"265598": _market_snapshot("265598", "180")},
        history_lookback_days=400,
        horizon_trading_days=21,
        minimum_bars_required=60,
        max_assets=10,
        valid_minutes=1440,
    )

    assert report.asset_total == 1
    assert report.asset_success == 1
    assert report.asset_failed == 0
    assert report.forecasts_persisted == 1
    assert report.bars_persisted == 120
    assert len(forecast_repo.saved) == 1
    forecast = forecast_repo.saved[0]
    assert forecast.status == "ready"
    assert forecast.model_code == "baseline_gbm"
    assert forecast.safe_for_analysis is False
    assert forecast.safe_for_suggestions is False
    assert forecast.safe_for_action_drafts is False
    assert forecast.direction_label in {"slight_up", "neutral", "strong_up"}
    assert forecast.current_price == Decimal("180")
    assert forecast.horizon_days == 21


def test_unknown_exchange_skips_with_recorded_reason() -> None:
    provider = FakeHistoricalProvider(bars={})
    bar_repo = FakeBarRepo()
    forecast_repo = FakeForecastRepo()

    report = sync_forecasts(
        provider=provider,
        bar_repo=bar_repo,
        forecast_repo=forecast_repo,
        positions=[_position(conid="1", symbol="MYSTERY", primary="OTC")],
        market_snapshots_by_conid={"1": _market_snapshot("1", "10")},
        history_lookback_days=400,
        horizon_trading_days=21,
        minimum_bars_required=60,
        max_assets=10,
        valid_minutes=1440,
    )

    assert report.asset_skipped_unknown_exchange == 1
    assert report.forecasts_persisted == 0
    assert provider.calls == []
    assert any(f["reason"] == "unknown_exchange" for f in report.failures)


def test_missing_market_data_skips_with_recorded_reason() -> None:
    provider = FakeHistoricalProvider(bars={})
    bar_repo = FakeBarRepo()
    forecast_repo = FakeForecastRepo()

    report = sync_forecasts(
        provider=provider,
        bar_repo=bar_repo,
        forecast_repo=forecast_repo,
        positions=[_position(conid="1", symbol="AAPL", primary="NASDAQ")],
        market_snapshots_by_conid={},  # no snapshot
        history_lookback_days=400,
        horizon_trading_days=21,
        minimum_bars_required=60,
        max_assets=10,
        valid_minutes=1440,
    )

    assert report.asset_skipped_missing_market_data == 1
    assert provider.calls == []
    assert any(f["reason"] == "missing_current_price" for f in report.failures)


def test_insufficient_history_is_reported_as_failure_not_persisted() -> None:
    short_bars = _realistic_bars(
        initial=100.0,
        annual_drift=0.05,
        annual_sigma=0.18,
        n_bars=20,
    )
    provider = FakeHistoricalProvider(bars={"AAPL.US": short_bars})
    bar_repo = FakeBarRepo()
    forecast_repo = FakeForecastRepo()

    report = sync_forecasts(
        provider=provider,
        bar_repo=bar_repo,
        forecast_repo=forecast_repo,
        positions=[_position(conid="1", symbol="AAPL", primary="NASDAQ")],
        market_snapshots_by_conid={"1": _market_snapshot("1", "100")},
        history_lookback_days=400,
        horizon_trading_days=21,
        minimum_bars_required=60,
        max_assets=10,
        valid_minutes=1440,
    )

    assert report.asset_failed == 1
    assert report.forecasts_persisted == 0
    assert any(f["reason"] == "insufficient_history" for f in report.failures)


def test_auth_error_short_circuits_the_batch() -> None:
    provider = FakeHistoricalProvider(
        errors={"AAPL.US": EodhdAuthError("bad key")},
        bars={"MSFT.US": _realistic_bars(
            initial=100.0,
            annual_drift=0.05,
            annual_sigma=0.18,
            n_bars=80,
        )},
    )
    bar_repo = FakeBarRepo()
    forecast_repo = FakeForecastRepo()

    report = sync_forecasts(
        provider=provider,
        bar_repo=bar_repo,
        forecast_repo=forecast_repo,
        positions=[
            _position(conid="1", symbol="AAPL", primary="NASDAQ"),
            _position(conid="2", symbol="MSFT", primary="NASDAQ"),
        ],
        market_snapshots_by_conid={
            "1": _market_snapshot("1", "100"),
            "2": _market_snapshot("2", "200"),
        },
        history_lookback_days=400,
        horizon_trading_days=21,
        minimum_bars_required=60,
        max_assets=10,
        valid_minutes=1440,
    )

    assert provider.calls == [("AAPL.US", provider.calls[0][1], provider.calls[0][2])]
    assert report.forecasts_persisted == 0
    assert any(f["reason"] == "auth_error" for f in report.failures)


def test_serializer_renders_decimals_as_strings_and_strips_safe_flags() -> None:
    bars = _realistic_bars(
        initial=100.0, annual_drift=0.08, annual_sigma=0.20, n_bars=120
    )
    provider = FakeHistoricalProvider(bars={"AAPL.US": bars})
    bar_repo = FakeBarRepo()
    forecast_repo = FakeForecastRepo()
    sync_forecasts(
        provider=provider,
        bar_repo=bar_repo,
        forecast_repo=forecast_repo,
        positions=[_position(conid="1", symbol="AAPL", primary="NASDAQ")],
        market_snapshots_by_conid={"1": _market_snapshot("1", "180")},
        history_lookback_days=400,
        horizon_trading_days=21,
        minimum_bars_required=60,
        max_assets=10,
        valid_minutes=1440,
    )

    rendered = serialize_forecast_for_response(forecast_repo.saved[0])

    for key in (
        "current_price",
        "p10_price",
        "p50_price",
        "p90_price",
        "prob_gain",
        "prob_loss",
        "expected_return_pct",
        "expected_volatility_annual",
    ):
        assert isinstance(rendered[key], str)
    assert rendered["safe_for_analysis"] is False
    assert rendered["safe_for_suggestions"] is False
    assert rendered["safe_for_action_drafts"] is False
