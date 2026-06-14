"""Endpoint tests for ``POST /forecasts/compute`` and ``GET /forecasts/latest``.

We patch the storage repository constructors and the provider factory used by
``status_routes`` so the route exercises its full pipeline without a real
database, real network, or real ``ibapi`` connection.
"""

from __future__ import annotations

import math
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.eodhd_client import EodhdBar
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset() -> None:
    api_settings.forecast_sync_enabled = False
    api_settings.market_data_sync_enabled = False
    api_settings.market_data_provider = "none"
    api_settings.eodhd_enabled = False
    api_settings.eodhd_api_key = None
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    api_settings.forecast_history_lookback_days = 400
    api_settings.forecast_horizon_trading_days = 21
    api_settings.forecast_minimum_bars_required = 60
    api_settings.forecast_max_assets_per_run = 50
    api_settings.forecast_valid_minutes = 1440


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_compute_blocked_when_disabled() -> None:
    r = client.post("/forecasts/compute")
    body = r.json()
    assert r.status_code == 200
    assert body["status"] == "blocked"
    assert body["reason"] == "forecast_sync_disabled"
    assert body["safe_for_orders"] is False


def test_compute_blocked_when_provider_not_configured() -> None:
    api_settings.forecast_sync_enabled = True
    r = client.post("/forecasts/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "market_data_provider_not_configured"


def test_compute_blocked_when_storage_not_writable() -> None:
    api_settings.forecast_sync_enabled = True
    api_settings.market_data_sync_enabled = True
    api_settings.market_data_provider = "eodhd"
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "k"
    r = client.post("/forecasts/compute")
    body = r.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def _realistic_bars(n: int) -> list[EodhdBar]:
    closes = [100.0]
    mu = 0.08 / 252
    sigma = 0.20 / math.sqrt(252)
    offsets = (1.4142, -1.4142, 0.7071, -0.7071, 0.0)
    for i in range(1, n):
        closes.append(closes[-1] * math.exp(mu + sigma * offsets[(i - 1) % 5]))
    start = date(2025, 1, 1)
    return [
        EodhdBar(
            bar_date=start + timedelta(days=i),
            open_price=Decimal(repr(c)),
            high_price=Decimal(repr(c)),
            low_price=Decimal(repr(c)),
            close_price=Decimal(repr(c)),
            adjusted_close=Decimal(repr(c)),
            volume=Decimal("1000000"),
        )
        for i, c in enumerate(closes)
    ]


def test_compute_runs_full_cycle_with_fake_repos_and_provider(monkeypatch) -> None:
    api_settings.forecast_sync_enabled = True
    api_settings.market_data_sync_enabled = True
    api_settings.market_data_provider = "eodhd"
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "k"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    now = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)

    class _Pos:
        def __init__(self, conid: str, symbol: str, primary: str, currency: str = "USD") -> None:
            self.snapshot_id = f"pos_{conid}"
            self.sync_run_id = "ibkr-sync-test"
            self.account_ref = "DU12345"
            self.conid = conid
            self.symbol = symbol
            self.security_type = "STK"
            self.currency = currency
            self.exchange = "SMART"
            self.primary_exchange = primary
            self.quantity = Decimal("5")
            self.average_cost = Decimal("100")
            self.received_at = now
            self.stored_at = now

    class _Snap:
        def __init__(self, conid: str, last_price: str) -> None:
            self.snapshot_id = f"md_{conid}"
            self.ibkr_conid = conid
            self.last_price = Decimal(last_price)

    class _LatestRun:
        sync_run_id = "ibkr-sync-test"

    class _MarketRepoListResult:
        def __init__(self, records: list[object]) -> None:
            self.records = records

    saved_bars: list[object] = []
    saved_forecasts: list[object] = []

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return _LatestRun()

        def list_ibkr_position_snapshots(self, _sync_run_id: str):
            return [_Pos("265598", "AAPL", "NASDAQ"), _Pos("100001", "ASML", "AEB", "EUR")]

        def list_ibkr_account_cash_snapshots(self, _sync_run_id: str):
            return []

    class _FakeMarketRepo:
        def list_latest_market_data_snapshots_by_conids(self, conids: tuple[str, ...]):
            assert "265598" in conids
            return _MarketRepoListResult(
                [_Snap("265598", "180"), _Snap("100001", "750")]
            )

        def list_latest_market_data_snapshots_by_symbols(
            self, _symbols: tuple[str, ...]
        ):
            return _MarketRepoListResult([])

    class _FakeWatchlistPrefRepo:
        def list_for_account(
            self, *, ibkr_account_ref: str, kind: str
        ):
            return _MarketRepoListResult([])

    class _FakeBarRepo:
        def save_market_data_bars(self, records: list[object]) -> object:
            saved_bars.extend(records)
            return None

    class _FakeForecastRepo:
        def save_asset_forecast(self, record: object) -> object:
            saved_forecasts.append(record)
            return None

    class _Connection:
        connection = "fake"
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkrRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataSnapshotRepository",
        lambda *a, **k: _FakeMarketRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataBarRepository",
        lambda *a, **k: _FakeBarRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetForecastRepository",
        lambda *a, **k: _FakeForecastRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyWatchlistPreferenceRepository",
        lambda *a, **k: _FakeWatchlistPrefRepo(),
    )

    bars = _realistic_bars(120)

    class _Provider:
        def fetch_eod_bars(
            self, eodhd_symbol: str, *, from_date: date, to_date: date
        ) -> list[EodhdBar]:
            return bars

        # Market-data provider interface methods exist on EodhdClient but
        # are unused by the forecast route.
        def fetch_quote(self, *_a, **_k):  # pragma: no cover
            raise AssertionError("not used")

        def fetch_fx_rate(self, *_a, **_k):  # pragma: no cover
            raise AssertionError("not used")

    monkeypatch.setattr(status_routes, "build_market_data_provider", lambda _s: _Provider())

    response = client.post("/forecasts/compute")
    body = response.json()
    assert response.status_code == 200, body
    assert body["status"] == "completed"
    assert body["asset_total"] == 2
    assert body["asset_success"] == 2
    assert body["forecasts_persisted"] == 2
    assert body["bars_persisted"] == 240
    assert body["model_code"] == "baseline_gbm"
    assert body["safe_for_orders"] is False
    assert body["suggestions_allowed"] is False
    assert len(saved_forecasts) == 2
    assert len(saved_bars) == 240


def test_compute_extends_universe_with_operator_favorites(monkeypatch) -> None:
    """V1.2 §BR: forecasts must run for operator favorites (CLAUDE.md §5)
    even when the symbol is not currently held. The route synthesises a
    quantity=0 position record from the latest market_data snapshot for
    each unheld favorite, and the EODHD provider receives the merged
    universe."""

    api_settings.forecast_sync_enabled = True
    api_settings.market_data_sync_enabled = True
    api_settings.market_data_provider = "eodhd"
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "k"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    now = datetime(2026, 5, 24, 10, 0, tzinfo=UTC)

    class _Pos:
        def __init__(self, conid: str, symbol: str) -> None:
            self.snapshot_id = f"pos_{conid}"
            self.sync_run_id = "ibkr-sync-test"
            self.account_ref = "DU12345"
            self.conid = conid
            self.symbol = symbol
            self.security_type = "STK"
            self.currency = "USD"
            self.exchange = "SMART"
            self.primary_exchange = "NASDAQ"
            self.quantity = Decimal("5")
            self.average_cost = Decimal("100")
            self.received_at = now
            self.stored_at = now

    class _MdSnap:
        def __init__(self, conid: str, symbol: str, last_price: str) -> None:
            self.snapshot_id = f"md_{conid}"
            self.ibkr_conid = conid
            self.symbol = symbol
            self.last_price = Decimal(last_price)
            self.currency = "EUR" if conid == "200002" else "USD"
            self.asset_class = "STK"
            self.exchange = "SMART"
            self.primary_exchange = "AEB" if conid == "200002" else "NASDAQ"

    class _LatestRun:
        sync_run_id = "ibkr-sync-test"

    class _ListResult:
        def __init__(self, records: list[object]) -> None:
            self.records = records

    class _Pref:
        def __init__(self, symbol: str) -> None:
            self.watchlist_preference_id = f"pref-{symbol}"
            self.symbol = symbol
            self.note = None
            self.kind = "favorite"
            self.ibkr_account_ref = "default"
            self.created_at = now

    seen_eodhd_symbols: list[str] = []
    saved_forecasts: list[object] = []
    saved_bars: list[object] = []
    requested_symbol_lookups: list[tuple[str, ...]] = []
    requested_conid_lookups: list[tuple[str, ...]] = []

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return _LatestRun()

        def list_ibkr_position_snapshots(self, _sync_run_id: str):
            return [_Pos("265598", "AAPL")]

        def list_ibkr_account_cash_snapshots(self, _sync_run_id: str):
            return []

    class _FakeMarketRepo:
        def list_latest_market_data_snapshots_by_conids(
            self, conids: tuple[str, ...]
        ):
            requested_conid_lookups.append(conids)
            return _ListResult(
                [
                    _MdSnap("265598", "AAPL", "180"),
                    _MdSnap("200002", "ASML", "750"),
                ]
            )

        def list_latest_market_data_snapshots_by_symbols(
            self, symbols: tuple[str, ...]
        ):
            requested_symbol_lookups.append(symbols)
            return _ListResult(
                [
                    _MdSnap("200002", "ASML", "750"),
                ]
            )

    class _FakeWatchlistPrefRepo:
        def list_for_account(
            self, *, ibkr_account_ref: str, kind: str
        ):
            assert ibkr_account_ref == "default"
            assert kind == "favorite"
            # ASML is a favorite, not held; AAPL is a favorite AND held —
            # the duplicate must be dropped (_unique_positions handles it).
            return _ListResult([_Pref("ASML"), _Pref("AAPL")])

    class _FakeBarRepo:
        def save_market_data_bars(self, records: list[object]) -> object:
            saved_bars.extend(records)
            return None

    class _FakeForecastRepo:
        def save_asset_forecast(self, record: object) -> object:
            saved_forecasts.append(record)
            return None

    class _Connection:
        connection = "fake"
        readiness = object()

    class _Ctx:
        def __enter__(self):
            return _Connection()

        def __exit__(self, *_):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _Ctx()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(
        status_routes, "build_database_connection_settings", lambda _u: object()
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkrRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataSnapshotRepository",
        lambda *a, **k: _FakeMarketRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataBarRepository",
        lambda *a, **k: _FakeBarRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyAssetForecastRepository",
        lambda *a, **k: _FakeForecastRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyWatchlistPreferenceRepository",
        lambda *a, **k: _FakeWatchlistPrefRepo(),
    )

    bars = _realistic_bars(120)

    class _Provider:
        def fetch_eod_bars(
            self, eodhd_symbol: str, *, from_date: date, to_date: date
        ) -> list[EodhdBar]:
            seen_eodhd_symbols.append(eodhd_symbol)
            return bars

        def fetch_quote(self, *_a, **_k):  # pragma: no cover
            raise AssertionError("not used")

        def fetch_fx_rate(self, *_a, **_k):  # pragma: no cover
            raise AssertionError("not used")

    monkeypatch.setattr(status_routes, "build_market_data_provider", lambda _s: _Provider())

    response = client.post("/forecasts/compute")
    body = response.json()
    assert response.status_code == 200, body
    assert body["status"] == "completed"
    # AAPL held + ASML favorite-synthesised = 2; AAPL is also a
    # favorite but dedupes against the held row.
    assert body["asset_total"] == 2, body
    assert len(saved_forecasts) == 2
    # Both unique symbols were forwarded to EODHD.
    assert "AAPL.US" in seen_eodhd_symbols
    assert "ASML.AS" in seen_eodhd_symbols
    # The favorites lookup was scoped to "ASML" only — AAPL was held
    # already, so the symbol-set lookup omitted it.
    assert requested_symbol_lookups == [("ASML",)]


def test_latest_returns_status_when_storage_unconfigured() -> None:
    response = client.get("/forecasts/latest")
    body = response.json()
    assert response.status_code == 200
    assert body["status"] == "not_configured"
    assert body["items"] == []
    assert body["safe_for_orders"] is False
