from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import ibkr_sync
from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_sync import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
    IbkrReadOnlyAdapter,
)
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)


class FakeAdapter(IbkrReadOnlyAdapter):
    def __init__(self) -> None:
        self.sync_calls = 0

    def sync_account_summary(self):
        self.sync_calls += 1
        return [
            IbkrCash(
                account_ref="paper",
                base_currency="USD",
                cash=Decimal("1000.25"),
                available_funds=Decimal("800.10"),
                buying_power=Decimal("1600.20"),
            )
        ]

    def sync_positions(self):
        return [
            IbkrPosition(
                account_ref="paper",
                symbol="MSFT",
                security_type="STK",
                currency="USD",
                quantity=Decimal("10"),
                average_cost=Decimal("200.50"),
            )
        ]

    def sync_open_orders(self):
        return [
            IbkrOpenOrder(
                account_ref="paper",
                ibkr_order_id=123,
                ibkr_perm_id=456,
                parent_order_id=None,
                client_id=7,
                symbol="MSFT",
                security_type="STK",
                currency="USD",
                exchange="SMART",
                primary_exchange="NASDAQ",
                action_side="BUY",
                order_type="LMT",
                quantity=Decimal("2"),
                limit_price=Decimal("300"),
                stop_price=None,
                tif="DAY",
                status="Submitted",
                filled_quantity=Decimal("0"),
                remaining_quantity=Decimal("2"),
                average_fill_price=None,
                last_status_at=datetime.now(UTC),
                raw_status_reference="raw",
            )
        ]

    def sync_executions(self):
        return [
            IbkrExecution(
                account_ref="paper",
                execution_id="E1",
                ibkr_order_id=123,
                ibkr_perm_id=456,
                symbol="MSFT",
                security_type="STK",
                currency="USD",
                exchange="SMART",
                primary_exchange="NASDAQ",
                side="BOT",
                quantity=Decimal("1"),
                price=Decimal("299.50"),
                execution_time=datetime.now(UTC),
                commission=None,
                commission_currency=None,
                realized_pnl=None,
                raw_execution_reference="raw",
            )
        ]


def setup_function() -> None:
    ibkr_sync.STORE.runs.clear()
    ibkr_sync.STORE.positions.clear()
    ibkr_sync.STORE.cash.clear()
    ibkr_sync.STORE.open_orders.clear()
    ibkr_sync.STORE.executions.clear()
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None


def _base_settings(**kwargs):
    return Settings(
        ibkr_sync_enabled=True,
        ibkr_sync_host="127.0.0.1",
        ibkr_sync_port=4002,
        ibkr_sync_client_id=7,
        **kwargs,
    )


def test_fake_adapter_stores_orders_and_executions() -> None:
    body = ibkr_sync.run_sync(_base_settings(), adapter=FakeAdapter())
    assert body["open_orders_count"] == 1
    assert body["executions_count"] == 1
    assert ibkr_sync.STORE.open_orders[0]["quantity"] == "2"
    assert ibkr_sync.STORE.executions[0]["price"] == "299.50"
    assert body["actions_allowed"] is False
    assert body["order_submission_allowed"] is False
    assert body["order_modification_allowed"] is False
    assert body["order_cancellation_allowed"] is False
    assert body["suggestions_allowed"] is False


def test_sync_returns_memory_fallback_when_storage_disabled() -> None:
    settings = _base_settings()
    settings.storage.enabled = False
    body = ibkr_sync.run_sync(settings, adapter=FakeAdapter())
    assert body["persistence_mode"] == "memory"
    assert body["persistence_status_nl"] == "Geheugenfallback actief"


def test_sync_uses_durable_repo_when_available(monkeypatch) -> None:
    calls: dict[str, int] = {"runs": 0, "cash": 0, "positions": 0, "orders": 0, "executions": 0}

    class FakeCtx:
        def __exit__(self, *_args):
            return None

    class FakeRepo:
        def save_ibkr_sync_run(self, record):
            calls["runs"] += 1

        def save_ibkr_account_cash_snapshots(self, sync_run_id, records):
            calls["cash"] += len(records)

        def save_ibkr_position_snapshots(self, sync_run_id, records):
            calls["positions"] += len(records)

        def save_ibkr_open_order_snapshots(self, sync_run_id, records):
            calls["orders"] += len(records)

        def save_ibkr_execution_snapshots(self, sync_run_id, records):
            calls["executions"] += len(records)

    monkeypatch.setattr(
        ibkr_sync,
        "_resolve_repo",
        lambda settings, require_writable: (FakeRepo(), FakeCtx(), ""),
    )
    body = ibkr_sync.run_sync(_base_settings(), adapter=FakeAdapter())
    assert body["persistence_mode"] == "durable"
    assert calls == {"runs": 1, "cash": 1, "positions": 1, "orders": 1, "executions": 1}


def test_status_and_read_endpoints_use_memory_when_storage_disabled() -> None:
    response = client.get("/ibkr/sync/status").json()
    assert response["actions_allowed"] is False
    assert response["suggestions_allowed"] is False
    assert client.get("/ibkr/orders/open").json()["actions_allowed"] is False
    assert client.get("/ibkr/executions").json()["actions_allowed"] is False


def test_sync_status_blocked_when_sync_disabled() -> None:
    payload = ibkr_sync.read_status(Settings())
    assert payload["sync_readiness_status"] == "blocked"
    assert payload["sync_readiness_status_nl"] == "Geblokkeerd"
    assert payload["manual_sync_allowed"] is False
    assert payload["actions_allowed"] is False
    assert payload["order_submission_allowed"] is False
    assert payload["suggestions_allowed"] is False


def test_run_sync_blocked_when_readonly_disabled() -> None:
    adapter = FakeAdapter()
    body = ibkr_sync.run_sync(
        _base_settings(ibkr_sync_readonly=False),
        adapter=adapter,
    )
    assert body["sync_readiness_status"] == "blocked"
    assert body["manual_sync_allowed"] is False
    assert adapter.sync_calls == 0


def test_run_sync_needs_control_when_status_check_disabled() -> None:
    adapter = FakeAdapter()
    body = ibkr_sync.run_sync(
        _base_settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=False,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        adapter=adapter,
    )
    assert body["sync_readiness_status"] == "needs_control"
    assert adapter.sync_calls == 0


def test_storage_enabled_but_not_configured_uses_memory_fallback() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = None
    response = client.get("/ibkr/sync/status").json()
    assert response["help_nl"] == "Geen duurzame IBKR-syncrun gevonden."


def test_storage_connection_error_falls_back_to_memory(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model

    api_settings.storage.enabled = True
    api_settings.storage.database_url = "sqlite+pysqlite:///missing"
    monkeypatch.setattr(
        ibkr_sync_read_model,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=None,
            storage_help_nl="Storage niet beschikbaar; geheugenfallback actief.",
        ),
    )
    response = client.get("/ibkr/sync/status").json()
    assert response["help_nl"] in {
        "Storage niet beschikbaar; geheugenfallback actief.",
        "Geen duurzame IBKR-syncrun gevonden.",
    }


def test_durable_no_run_returns_empty_items(monkeypatch) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model

    api_settings.storage.enabled = True
    api_settings.storage.database_url = "sqlite+pysqlite:///dummy.db"
    monkeypatch.setattr(
        ibkr_sync_read_model,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=None,
            storage_help_nl="Geen duurzame IBKR-syncrun gevonden.",
        ),
    )
    assert client.get("/ibkr/portfolio/positions").json()["items"] == []
    assert client.get("/ibkr/account/cash").json()["items"] == []
    assert client.get("/ibkr/orders/open").json()["items"] == []
    assert client.get("/ibkr/executions").json()["items"] == []
