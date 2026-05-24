"""Endpoint test for ``POST /market-data/sync``.

Covers the three short-circuit paths (provider not configured, storage not
writable, no IBKR sync run) and a successful end-to-end path where the
endpoint receives positions/cash from a fake IBKR repo, calls a fake EODHD
provider, persists fake market + FX records, and returns the expected
summary shape.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import status_routes
from portfolio_outlook_api.eodhd_client import EodhdFxRate, EodhdQuote
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _reset_settings() -> None:
    api_settings.market_data_sync_enabled = False
    api_settings.market_data_provider = "none"
    api_settings.eodhd_enabled = False
    api_settings.eodhd_api_key = None
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset_settings()


def teardown_function() -> None:
    _reset_settings()


def test_sync_returns_blocked_when_provider_not_configured() -> None:
    response = client.post("/market-data/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "market_data_provider_not_configured"
    assert body["market_snapshots_persisted"] == 0
    assert body["fx_snapshots_persisted"] == 0
    assert body["actions_allowed"] is False
    assert body["order_submission_allowed"] is False
    assert body["suggestions_allowed"] is False


def test_sync_returns_blocked_when_storage_not_writable(monkeypatch) -> None:
    api_settings.market_data_sync_enabled = True
    api_settings.market_data_provider = "eodhd"
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "k"
    # storage flags remain false → blocked

    response = client.post("/market-data/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "storage_not_writable"


def test_sync_runs_full_cycle_with_fake_provider_and_repos(monkeypatch) -> None:
    api_settings.market_data_sync_enabled = True
    api_settings.market_data_provider = "eodhd"
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "k"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    now = datetime(2025, 5, 24, 10, 0, tzinfo=UTC)

    # ---- fake IBKR repo, market repo, FX repo, storage context ----

    class _FakeIbkrPosition:
        def __init__(self, *, conid: str, symbol: str, primary: str, ccy: str) -> None:
            self.snapshot_id = f"pos_{conid}"
            self.sync_run_id = "ibkr-sync-test"
            self.account_ref = "DU12345"
            self.conid = conid
            self.symbol = symbol
            self.security_type = "STK"
            self.currency = ccy
            self.exchange = "SMART"
            self.primary_exchange = primary
            self.quantity = Decimal("5")
            self.average_cost = Decimal("100")
            self.received_at = now
            self.stored_at = now

    class _FakeCash:
        def __init__(self, ccy: str) -> None:
            self.snapshot_id = f"cash_{ccy}"
            self.sync_run_id = "ibkr-sync-test"
            self.account_ref = "DU12345"
            self.base_currency = ccy
            self.cash = Decimal("1000")
            self.available_funds = Decimal("1000")
            self.buying_power = Decimal("1000")
            self.received_at = now
            self.stored_at = now

    class _LatestRun:
        sync_run_id = "ibkr-sync-test"

    saved_market: list[object] = []
    saved_fx: list[object] = []

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return _LatestRun()

        def list_ibkr_position_snapshots(self, sync_run_id: str):
            assert sync_run_id == "ibkr-sync-test"
            return [
                _FakeIbkrPosition(conid="265598", symbol="AAPL", primary="NASDAQ", ccy="USD"),
                _FakeIbkrPosition(conid="100001", symbol="ASML", primary="AEB", ccy="EUR"),
            ]

        def list_ibkr_account_cash_snapshots(self, sync_run_id: str):
            return [_FakeCash("EUR")]

        def save_fx_rate_snapshot(self, record: object) -> None:
            saved_fx.append(record)

    class _FakeMarketRepo:
        def save_latest_market_data_snapshot(self, record: object) -> object:
            saved_market.append(record)
            return None

    class _FakeReadiness:
        pass

    class _FakeConnection:
        connection = "fake-conn"
        readiness = _FakeReadiness()

    class _FakeConnContext:
        def __enter__(self):
            return _FakeConnection()

        def __exit__(self, *exc):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k) -> None:
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _FakeConnContext()

    # Replace the repository constructors and connection provider used by the
    # route so no real database is needed.
    monkeypatch.setattr(
        status_routes,
        "StorageConnectionProvider",
        _FakeStorageProvider,
    )
    monkeypatch.setattr(
        status_routes,
        "build_database_connection_settings",
        lambda _url: object(),
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

    # Replace the provider factory with a stub that returns a fake EODHD
    # client (so we don't need an API key or HTTP layer).
    class _FakeProvider:
        def fetch_quote(self, eodhd_symbol: str) -> EodhdQuote:
            if eodhd_symbol == "AAPL.US":
                return EodhdQuote(
                    code="AAPL.US",
                    last_price=Decimal("181.40"),
                    open_price=None,
                    high_price=None,
                    low_price=None,
                    previous_close=Decimal("180.00"),
                    day_change_percent=Decimal("0.78"),
                    volume=None,
                    provider_as_of=now,
                )
            if eodhd_symbol == "ASML.AS":
                return EodhdQuote(
                    code="ASML.AS",
                    last_price=Decimal("780.50"),
                    open_price=None,
                    high_price=None,
                    low_price=None,
                    previous_close=Decimal("775.00"),
                    day_change_percent=Decimal("0.71"),
                    volume=None,
                    provider_as_of=now,
                )
            raise AssertionError(f"unexpected symbol: {eodhd_symbol}")

        def fetch_fx_rate(self, base: str, quote: str) -> EodhdFxRate:
            assert (base, quote) == ("USD", "EUR")
            return EodhdFxRate(
                pair_code="USDEUR.FOREX",
                base_currency="USD",
                quote_currency="EUR",
                rate=Decimal("0.9234"),
                previous_close=Decimal("0.9211"),
                provider_as_of=now,
            )

    monkeypatch.setattr(
        status_routes,
        "build_market_data_provider",
        lambda _settings: _FakeProvider(),
    )

    response = client.post("/market-data/sync")
    assert response.status_code == 200, response.json()
    body = response.json()
    assert body["status"] == "completed"
    assert body["provider_code"] == "eodhd"
    assert body["asset_total"] == 2
    assert body["asset_success"] == 2
    assert body["asset_failed"] == 0
    assert body["fx_total"] == 1
    assert body["fx_success"] == 1
    assert body["base_currency"] == "EUR"
    assert body["market_snapshots_persisted"] == 2
    assert body["fx_snapshots_persisted"] == 1
    assert body["actions_allowed"] is False
    assert body["suggestions_allowed"] is False
    assert body["safe_for_orders"] is False
    assert body["blocks_orders"] is True
    assert len(saved_market) == 2
    assert len(saved_fx) == 1


def test_sync_returns_blocked_when_no_ibkr_sync_run(monkeypatch) -> None:
    api_settings.market_data_sync_enabled = True
    api_settings.market_data_provider = "eodhd"
    api_settings.eodhd_enabled = True
    api_settings.eodhd_api_key = "k"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True

    class _FakeIbkrRepo:
        def get_latest_ibkr_sync_run(self):
            return None

    class _FakeConnection:
        connection = "fake-conn"
        readiness = object()

    class _FakeConnContext:
        def __enter__(self):
            return _FakeConnection()

        def __exit__(self, *exc):
            return None

    class _FakeStorageProvider:
        def __init__(self, *_a, **_k):
            pass

        def checked_connection(self, *_, require_writable: bool = False, **__):
            return _FakeConnContext()

    monkeypatch.setattr(status_routes, "StorageConnectionProvider", _FakeStorageProvider)
    monkeypatch.setattr(status_routes, "build_database_connection_settings", lambda _u: object())
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda *a, **k: _FakeIbkrRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataSnapshotRepository",
        lambda *a, **k: object(),
    )

    class _AlwaysReturnsProviderFactory:
        def __call__(self, _settings):
            class _NoopProvider:
                def fetch_quote(self, *_a, **_k):
                    raise AssertionError("must not be called when no sync run")

                def fetch_fx_rate(self, *_a, **_k):
                    raise AssertionError("must not be called when no sync run")

            return _NoopProvider()

    monkeypatch.setattr(
        status_routes,
        "build_market_data_provider",
        _AlwaysReturnsProviderFactory(),
    )

    response = client.post("/market-data/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "blocked"
    assert body["reason"] == "no_ibkr_sync_run"
