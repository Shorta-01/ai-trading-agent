from datetime import UTC, datetime
from decimal import Decimal

from ai_trading_agent_storage import (
    IbkrAccountCashSnapshotRecord,
    IbkrPositionSnapshotRecord,
    IbkrSyncRunRecord,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


def _run() -> IbkrSyncRunRecord:
    return IbkrSyncRunRecord(
        sync_run_id="run-1",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        provider_code="ibkr",
        provider_environment="paper",
        account_mode="paper",
        readonly=True,
        status="completed",
        account_summary_status="ok",
        positions_status="ok",
        open_orders_status="ok",
        executions_status="ok",
        positions_count=1,
        cash_values_count=0,
        open_orders_count=0,
        executions_count=0,
        status_nl="Klaar",
        next_step_nl=None,
        help_nl=None,
        actions_allowed=False,
        order_submission_allowed=False,
        order_modification_allowed=False,
        order_cancellation_allowed=False,
        suggestions_allowed=False,
        stored_at=datetime.now(UTC),
    )


def _position() -> IbkrPositionSnapshotRecord:
    return IbkrPositionSnapshotRecord(
        snapshot_id="p-1",
        sync_run_id="run-1",
        account_ref="U1",
        conid="123",
        symbol="MSFT",
        security_type="STK",
        currency="USD",
        exchange="SMART",
        primary_exchange="NASDAQ",
        quantity=Decimal("2"),
        average_cost=Decimal("100"),
        received_at=datetime.now(UTC),
        stored_at=datetime.now(UTC),
    )


def test_storage_unavailable_returns_blocked(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    monkeypatch.setattr(api_settings.storage, "enabled", True)
    monkeypatch.setattr(api_settings.storage, "database_url", "sqlite+pysqlite:///dummy.db")
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=None,
            storage_help_nl="Storage niet beschikbaar.",
        ),
    )
    payload = client.get("/portfolio/valuation/readiness").json()
    assert payload["status"] == "storage_unavailable"
    assert payload["blocked"] is True
    assert payload["fx_snapshot_contract_status"] == "fx_snapshot_contract_available"


def test_no_latest_snapshot_returns_blocked(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    monkeypatch.setattr(api_settings.storage, "enabled", False)
    monkeypatch.setattr(api_settings.storage, "database_url", None)
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=None,
            storage_help_nl=None,
        ),
    )
    payload = client.get("/portfolio/valuation/readiness").json()
    assert payload["status"] == "no_latest_ibkr_snapshot"
    assert payload["suggestions_allowed"] is False
    assert payload["action_drafts_allowed"] is False
    assert payload["orders_allowed"] is False


def test_missing_market_data_blocks_valuation(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    monkeypatch.setattr(api_settings.storage, "enabled", True)
    monkeypatch.setattr(api_settings.storage, "database_url", "sqlite+pysqlite:///dummy.db")
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=_run(),
            storage_help_nl=None,
        ),
    )

    class FakeRepo:
        def list_ibkr_position_snapshots(self, _sync_run_id: str):
            return [_position()]

        def list_ibkr_account_cash_snapshots(self, _sync_run_id: str):
            return []

        def list_latest_fx_rate_snapshots_by_pairs(self, _pairs: tuple[str, ...]):
            return []

    class FakeMarketRepo:
        def list_latest_market_data_snapshots_by_conids(self, _conids):
            return type("R", (), {"records": ()})()

    class Ctx:
        def __enter__(self):
            return type("Checked", (), {"connection": object(), "readiness": object()})()

        def __exit__(self, *_args):
            return None

    class FakeProvider:
        def checked_connection(self, require_writable: bool = False):
            return Ctx()

    monkeypatch.setattr(
        status_routes,
        "StorageConnectionProvider",
        lambda _settings: FakeProvider(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda _c, _r: FakeRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataSnapshotRepository",
        lambda _c, _r: FakeMarketRepo(),
    )
    payload = client.get("/portfolio/valuation/readiness").json()
    assert payload["status"] == "missing_market_data"
    assert payload["rows"][0]["market_value"] is None
    assert payload["rows"][0]["market_price"] is None


def _cash(currency: str = "USD") -> IbkrAccountCashSnapshotRecord:
    return IbkrAccountCashSnapshotRecord(
        snapshot_id="c-1",
        sync_run_id="run-1",
        account_ref="U1",
        base_currency=currency,
        cash=Decimal("50.10"),
        available_funds=Decimal("40.00"),
        buying_power=Decimal("80.00"),
        received_at=datetime.now(UTC),
        stored_at=datetime.now(UTC),
    )


def test_cash_snapshot_exposed_decimal_safe(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    monkeypatch.setattr(api_settings.storage, "enabled", True)
    monkeypatch.setattr(api_settings.storage, "database_url", "sqlite+pysqlite:///dummy.db")
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=_run(),
            storage_help_nl=None,
        ),
    )

    class FakeRepo:
        def list_ibkr_position_snapshots(self, _sync_run_id: str):
            return [_position()]

        def list_ibkr_account_cash_snapshots(self, _sync_run_id: str):
            return [_cash("USD")]

        def list_latest_fx_rate_snapshots_by_pairs(self, _pairs: tuple[str, ...]):
            return []

    class FakeMarketRepo:
        def list_latest_market_data_snapshots_by_conids(self, _conids):
            return type("R", (), {"records": ()})()

    class Ctx:
        def __enter__(self):
            return type("Checked", (), {"connection": object(), "readiness": object()})()

        def __exit__(self, *_args):
            return None

    class FakeProvider:
        def checked_connection(self, require_writable: bool = False):
            return Ctx()

    monkeypatch.setattr(
        status_routes,
        "StorageConnectionProvider",
        lambda _settings: FakeProvider(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda _c, _r: FakeRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataSnapshotRepository",
        lambda _c, _r: FakeMarketRepo(),
    )

    payload = client.get("/portfolio/valuation/readiness").json()
    assert payload["cash_readiness_status"] == "cash_available"
    assert payload["cash_values"][0]["cash"] == "50.10"
    assert payload["fx_required"] is False
    assert payload["fx_readiness_status"] == "fx_not_required"
    assert payload["fx_snapshot_contract_available"] is True
    assert payload["missing_fx_pairs"] == []
    assert "fx_rates" not in payload["missing_total_value_inputs"]


def test_multi_currency_without_fx_rates_is_blocked(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    monkeypatch.setattr(api_settings.storage, "enabled", True)
    monkeypatch.setattr(api_settings.storage, "database_url", "sqlite+pysqlite:///dummy.db")
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=_run(),
            storage_help_nl=None,
        ),
    )

    class FakeRepo:
        def list_ibkr_position_snapshots(self, _sync_run_id: str):
            row = _position()
            return [row]

        def list_ibkr_account_cash_snapshots(self, _sync_run_id: str):
            return [_cash("EUR")]

        def list_latest_fx_rate_snapshots_by_pairs(self, _pairs: tuple[str, ...]):
            return []

    class FakeMarketRepo:
        def list_latest_market_data_snapshots_by_conids(self, _conids):
            return type("R", (), {"records": ()})()

    class Ctx:
        def __enter__(self):
            return type("Checked", (), {"connection": object(), "readiness": object()})()

        def __exit__(self, *_args):
            return None

    class FakeProvider:
        def checked_connection(self, require_writable: bool = False):
            return Ctx()

    monkeypatch.setattr(
        status_routes,
        "StorageConnectionProvider",
        lambda _settings: FakeProvider(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda _c, _r: FakeRepo(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyMarketDataSnapshotRepository",
        lambda _c, _r: FakeMarketRepo(),
    )

    payload = client.get("/portfolio/valuation/readiness").json()
    assert payload["fx_required"] is True
    assert payload["fx_readiness_status"] == "fx_snapshot_missing"
    assert payload["fx_snapshot_contract_status"] == "fx_snapshot_contract_available"
    assert payload["fx_snapshot_data_available"] is False
    assert payload["total_portfolio_value_available"] is False


def test_no_positions_single_currency_cash_fx_not_required(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    monkeypatch.setattr(api_settings.storage, "enabled", True)
    monkeypatch.setattr(api_settings.storage, "database_url", "sqlite+pysqlite:///dummy.db")
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=_run(),
            storage_help_nl=None,
        ),
    )

    class FakeRepo:
        def list_ibkr_position_snapshots(self, _sync_run_id: str):
            return []

        def list_ibkr_account_cash_snapshots(self, _sync_run_id: str):
            return [_cash("USD")]

        def list_latest_fx_rate_snapshots_by_pairs(self, _pairs: tuple[str, ...]):
            return []

    class Ctx:
        def __enter__(self):
            return type("Checked", (), {"connection": object(), "readiness": object()})()

        def __exit__(self, *_args):
            return None

    class FakeProvider:
        def checked_connection(self, require_writable: bool = False):
            return Ctx()

    monkeypatch.setattr(
        status_routes,
        "StorageConnectionProvider",
        lambda _settings: FakeProvider(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda _c, _r: FakeRepo(),
    )

    payload = client.get("/portfolio/valuation/readiness").json()
    assert payload["status"] == "no_positions"
    assert payload["fx_required"] is False
    assert payload["fx_readiness_status"] == "fx_not_required"
    assert payload["missing_fx_pairs"] == []
    assert "fx_rates" not in payload["missing_total_value_inputs"]


def test_no_positions_multi_currency_cash_marks_fx_required(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    monkeypatch.setattr(api_settings.storage, "enabled", True)
    monkeypatch.setattr(api_settings.storage, "database_url", "sqlite+pysqlite:///dummy.db")
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=_run(),
            storage_help_nl=None,
        ),
    )

    class FakeRepo:
        def list_ibkr_position_snapshots(self, _sync_run_id: str):
            return []

        def list_ibkr_account_cash_snapshots(self, _sync_run_id: str):
            return [_cash("EUR"), _cash("USD")]

        def list_latest_fx_rate_snapshots_by_pairs(self, _pairs: tuple[str, ...]):
            return []

    class Ctx:
        def __enter__(self):
            return type("Checked", (), {"connection": object(), "readiness": object()})()

        def __exit__(self, *_args):
            return None

    class FakeProvider:
        def checked_connection(self, require_writable: bool = False):
            return Ctx()

    monkeypatch.setattr(
        status_routes,
        "StorageConnectionProvider",
        lambda _settings: FakeProvider(),
    )
    monkeypatch.setattr(
        status_routes,
        "SqlAlchemyIbkrSyncSnapshotRepository",
        lambda _c, _r: FakeRepo(),
    )

    payload = client.get("/portfolio/valuation/readiness").json()
    assert payload["status"] == "no_positions"
    assert payload["fx_required"] is True
    assert payload["fx_readiness_status"] == "fx_snapshot_missing"
    assert payload["fx_snapshot_contract_available"] is True
    assert payload["missing_fx_pairs"] == ["EUR/USD"]
    assert "fx_rates" in payload["missing_total_value_inputs"]
    assert payload["fx_rates_available"] is False
    assert payload["converted_totals_available"] is False
