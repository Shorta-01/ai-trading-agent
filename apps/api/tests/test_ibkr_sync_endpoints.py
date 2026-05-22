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

client = TestClient(app)


class FakeAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self):
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
