from datetime import UTC, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from portfolio_outlook_api import ibkr_sync
from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_status import IbkrSessionStatusAdapterResult
from portfolio_outlook_api.ibkr_sync import (
    IbkrCash,
    IbkrExecution,
    IbkrOpenOrder,
    IbkrPosition,
    IbkrReadOnlyAdapter,
)
from portfolio_outlook_api.ibkr_sync_readiness import build_ibkr_sync_readiness
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)




class FakeReadyPaperSessionStatusAdapter:
    def check_session_status(self, runtime_settings: Settings) -> IbkrSessionStatusAdapterResult:
        return IbkrSessionStatusAdapterResult(
            connection_status="connected_readonly",
            account_mode_status="match",
            account_mode="paper",
            session_check_source="test_fake_ready_paper_session",
            session_status_reason="test_ready",
        )


class RaisingSyncAdapter(IbkrReadOnlyAdapter):
    def sync_account_summary(self):
        raise AssertionError("sync adapter should not be called")

    def sync_positions(self):
        raise AssertionError("sync adapter should not be called")

    def sync_open_orders(self):
        raise AssertionError("sync adapter should not be called")

    def sync_executions(self):
        raise AssertionError("sync adapter should not be called")

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
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None


def _base_settings(**kwargs):
    values = {
        "ibkr_sync_enabled": True,
        "ibkr_sync_host": "127.0.0.1",
        "ibkr_sync_port": 4002,
        "ibkr_sync_client_id": 7,
    }
    values.update(kwargs)
    return Settings(**values)


def test_fake_adapter_stores_orders_and_executions() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=FakeAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
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
    body = ibkr_sync.run_sync(
        settings,
        adapter=FakeAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
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
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=FakeAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["persistence_mode"] == "durable"
    assert calls == {"runs": 1, "cash": 1, "positions": 1, "orders": 1, "executions": 1}


def test_status_and_read_endpoints_use_memory_when_storage_disabled() -> None:
    response = client.get("/ibkr/sync/status").json()
    assert response["sync_readiness_status"] == "blocked"
    assert response["sync_readiness_status_nl"] == "Geblokkeerd"
    assert response["manual_sync_allowed"] is False
    assert response["actions_allowed"] is False
    assert response["suggestions_allowed"] is False
    assert client.get("/ibkr/orders/open").json()["actions_allowed"] is False
    assert client.get("/ibkr/executions").json()["actions_allowed"] is False


def test_storage_enabled_but_not_configured_uses_memory_fallback() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = None
    response = client.get("/ibkr/sync/status").json()
    assert response["help_nl"] == "Geen duurzame IBKR-syncrun gevonden."


def test_sync_status_blocked_for_missing_sync_config() -> None:
    response = ibkr_sync.read_status(Settings(ibkr_sync_enabled=True))
    assert response["sync_readiness_status"] == "blocked"
    assert response["sync_readiness_reason"] == "missing_sync_config"


def test_sync_status_blocked_for_readonly_disabled() -> None:
    response = ibkr_sync.read_status(_base_settings(ibkr_sync_readonly=False))
    assert response["sync_readiness_status"] == "blocked"
    assert response["sync_readiness_reason"] == "readonly_required"


def test_sync_status_blocked_for_version1_paper_only() -> None:
    response = ibkr_sync.read_status(
        _base_settings(ibkr_sync_account_mode="live", ibkr_expected_environment="paper")
    )
    assert response["sync_readiness_status"] == "blocked"
    assert response["sync_readiness_reason"] == "version1_paper_only"
    assert response["manual_sync_allowed"] is False


def test_sync_status_needs_control_when_status_check_disabled() -> None:
    response = build_ibkr_sync_readiness(
        _base_settings(),
        {"connection_status": "status_check_disabled", "account_mode_status": "unknown"},
    )
    assert response["sync_readiness_status"] == "needs_control"
    assert response["manual_sync_allowed"] is False


def test_sync_status_ready_for_explicit_readonly_paper_status() -> None:
    response = build_ibkr_sync_readiness(
        _base_settings(ibkr_expected_environment="paper", ibkr_sync_account_mode="paper"),
        {
            "connection_status": "connected_readonly",
            "account_mode_status": "match",
            "session_check_attempted": True,
            "status_check_enabled": True,
        },
    )
    assert response["sync_readiness_status"] == "ready_for_manual_readonly_sync"
    assert response["manual_sync_allowed"] is True
    assert response["actions_allowed"] is False
    assert response["order_submission_allowed"] is False
    assert response["order_modification_allowed"] is False
    assert response["order_cancellation_allowed"] is False
    assert response["suggestions_allowed"] is False


def test_sync_run_blocked_when_sync_disabled() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(ibkr_sync_enabled=False),
        adapter=RaisingSyncAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["status"] == "sync_readiness_blocked"
    assert body["sync_readiness_status"] == "blocked"
    assert body["manual_sync_allowed"] is False
    assert body["sync_allowed"] is False
    assert body["sync_run_id"] is None
    assert body["persistence_mode"] == "none"
    assert len(ibkr_sync.STORE.runs) == 0
    assert body["actions_allowed"] is False
    assert body["suggestions_allowed"] is False


def test_sync_run_needs_control_blocks_manual_execution() -> None:
    body = ibkr_sync.run_sync(_base_settings(), adapter=RaisingSyncAdapter())
    assert body["status"] == "sync_readiness_needs_control"
    assert body["sync_readiness_status"] == "needs_control"
    assert body["manual_sync_allowed"] is False
    assert body["sync_run_id"] is None
    assert body["positions_count"] == 0
    assert len(ibkr_sync.STORE.runs) == 0


def test_sync_run_blocked_for_wrong_account_mode() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(ibkr_sync_account_mode="live", ibkr_expected_environment="paper"),
        adapter=RaisingSyncAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["sync_readiness_status"] == "blocked"
    assert body["sync_readiness_reason"] in {"account_mode_mismatch", "version1_paper_only"}
    assert body["sync_run_id"] is None


def test_live_mode_blocked_even_with_ready_session_adapter() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(ibkr_sync_account_mode="live", ibkr_expected_environment="live"),
        adapter=RaisingSyncAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["sync_readiness_status"] == "blocked"
    assert body["sync_readiness_reason"] == "version1_paper_only"
    assert body["sync_run_id"] is None


def test_blocking_session_states_do_not_call_adapter() -> None:
    class SingleStateAdapter:
        def __init__(self, connection_status: str) -> None:
            self._connection_status = connection_status

        def check_session_status(
            self, runtime_settings: Settings
        ) -> IbkrSessionStatusAdapterResult:
            return IbkrSessionStatusAdapterResult(
                connection_status=self._connection_status,
                account_mode_status="unknown",
                account_mode="paper",
                session_check_source="test_state",
                session_status_reason="test_state",
            )

    for connection_status in [
        "connection_failed",
        "authentication_required",
        "pacing_limited",
        "unknown",
    ]:
        body = ibkr_sync.run_sync(
            _base_settings(),
            adapter=RaisingSyncAdapter(),
            session_status_adapter=SingleStateAdapter(connection_status),
        )
        assert body["sync_readiness_status"] == "blocked"
        assert body["sync_run_id"] is None


def test_explicit_ready_paper_session_allows_fake_adapter() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(ibkr_expected_environment="paper", ibkr_sync_account_mode="paper"),
        adapter=FakeAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["sync_readiness_status"] == "ready_for_manual_readonly_sync"
    assert body["sync_run_id"] is not None
    assert body["positions_count"] == 1
    assert body["cash_values_count"] == 1
    assert body["open_orders_count"] == 1
    assert body["executions_count"] == 1
    assert body["actions_allowed"] is False
    assert body["order_submission_allowed"] is False
    assert body["suggestions_allowed"] is False


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
