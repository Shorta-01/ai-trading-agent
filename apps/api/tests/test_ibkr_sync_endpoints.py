from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import ibkr_sync
from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_sync import IbkrCash, IbkrPosition, IbkrReadOnlyAdapter
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


def setup_function() -> None:
    ibkr_sync.STORE.runs.clear()
    ibkr_sync.STORE.positions.clear()
    ibkr_sync.STORE.cash.clear()


def _base_settings(**kwargs):
    return Settings(
        ibkr_sync_enabled=True,
        ibkr_sync_host="127.0.0.1",
        ibkr_sync_port=4002,
        ibkr_sync_client_id=7,
        **kwargs,
    )


def test_ibkr_sync_status_disabled_by_default() -> None:
    body = client.get("/ibkr/sync/status").json()
    assert body["status"] == "disabled"
    assert body["actions_allowed"] is False


def test_run_sync_not_configured() -> None:
    body = ibkr_sync.run_sync(Settings(ibkr_sync_enabled=True))
    assert body["status"] == "not_configured"


def test_run_sync_wrong_account_mode() -> None:
    body = ibkr_sync.run_sync(_base_settings(ibkr_sync_account_mode="live"))
    assert body["status"] == "wrong_account_mode"


def test_fake_adapter_stores_positions_and_cash() -> None:
    body = ibkr_sync.run_sync(_base_settings(), adapter=FakeAdapter())
    assert body["status"] == "paper_account_confirmed"
    assert ibkr_sync.STORE.positions[0]["quantity"] == "10"
    assert ibkr_sync.STORE.cash[0]["cash"] == "1000.25"
    assert body["order_submission_allowed"] is False
    assert body["suggestions_allowed"] is False
