from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import ibkr_sync
from portfolio_outlook_api.ibkr_sync import (
    IbkrExecution,
    IbkrOpenOrder,
    IbkrReadOnlyAdapter,
)
from portfolio_outlook_api.main import app

client = TestClient(app)


class FakeAdapter(IbkrReadOnlyAdapter):
    def fetch_positions(self):
        return []

    def fetch_account_cash(self):
        return []

    def fetch_open_orders(self):
        return [
            IbkrOpenOrder(
                account_ref="paper",
                ibkr_order_id=101,
                symbol="MSFT",
                security_type="STK",
                currency="USD",
                quantity=Decimal("10"),
                status="Submitted",
                filled_quantity=Decimal("2"),
                remaining_quantity=Decimal("8"),
                limit_price=Decimal("200.50"),
                action_side="BUY",
                order_type="LMT",
            )
        ]

    def fetch_executions(self):
        return [
            IbkrExecution(
                account_ref="paper",
                execution_id="E-1",
                symbol="MSFT",
                security_type="STK",
                currency="USD",
                side="BUY",
                quantity=Decimal("2"),
                price=Decimal("200.50"),
                execution_time="2026-05-20T10:00:00Z",
                ibkr_order_id=101,
            )
        ]


class BrokenAdapter(IbkrReadOnlyAdapter):
    def fetch_positions(self):
        raise RuntimeError("boom")

    def fetch_account_cash(self):
        return []

    def fetch_open_orders(self):
        return []

    def fetch_executions(self):
        return []


def setup_function() -> None:
    ibkr_sync.STORE.runs.clear()
    ibkr_sync.STORE.positions.clear()
    ibkr_sync.STORE.cash.clear()
    ibkr_sync.STORE.open_orders.clear()
    ibkr_sync.STORE.executions.clear()


def test_ibkr_sync_status_not_configured() -> None:
    body = client.get("/ibkr/sync/status").json()
    assert body["configured"] is False
    assert body["open_orders_count"] == 0
    assert body["executions_count"] == 0


def test_ibkr_sync_run_returns_failed_when_not_configured() -> None:
    body = client.post("/ibkr/sync/run").json()
    assert body["status"] == "failed"


def test_ibkr_snapshot_endpoints_empty_without_sync_data() -> None:
    assert client.get("/ibkr/portfolio/positions").json()["items"] == []
    assert client.get("/ibkr/account/cash").json()["items"] == []
    assert client.get("/ibkr/orders/open").json()["items"] == []
    assert client.get("/ibkr/executions").json()["items"] == []


def test_run_sync_stores_open_orders_and_executions() -> None:
    result = ibkr_sync.run_sync(
        ibkr_sync.Settings(
            ibkr_enabled=True, ibkr_gateway_url="x", ibkr_account_id_hint="y"
        ),
        adapter=FakeAdapter(),
    )
    assert result["open_orders_saved"] == 1
    assert result["executions_saved"] == 1
    order = ibkr_sync.STORE.open_orders[0]
    assert order["quantity"] == "10"
    assert order["limit_price"] == "200.50"
    execution = ibkr_sync.STORE.executions[0]
    assert execution["price"] == "200.50"


def test_run_sync_failure_safe_status() -> None:
    result = ibkr_sync.run_sync(
        ibkr_sync.Settings(
            ibkr_enabled=True, ibkr_gateway_url="x", ibkr_account_id_hint="y"
        ),
        adapter=BrokenAdapter(),
    )
    assert result["status"] == "failed"


def test_sync_status_counts_after_sync() -> None:
    ibkr_sync.run_sync(
        ibkr_sync.Settings(
            ibkr_enabled=True, ibkr_gateway_url="x", ibkr_account_id_hint="y"
        ),
        adapter=FakeAdapter(),
    )
    body = ibkr_sync.read_status(
        ibkr_sync.Settings(
            ibkr_enabled=True, ibkr_gateway_url="x", ibkr_account_id_hint="y"
        )
    )
    assert body["open_orders_count"] == 1
    assert body["executions_count"] == 1
