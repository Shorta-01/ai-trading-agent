from datetime import UTC, datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from ibkr_sync_fixtures import (
    EmptyFixtureAdapter,
    InvalidFixtureAdapter,
    ProviderFailureFixtureAdapter,
    TimeoutFixtureAdapter,
    ValidFixtureAdapter,
)

from portfolio_outlook_api import ibkr_sync
from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_status import IbkrSessionStatusAdapterResult
from portfolio_outlook_api.ibkr_sync import IbkrReadOnlyAdapter
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


def setup_function() -> None:
    ibkr_sync.STORE.runs.clear()
    ibkr_sync.STORE.positions.clear()
    ibkr_sync.STORE.cash.clear()
    ibkr_sync.STORE.open_orders.clear()
    ibkr_sync.STORE.executions.clear()
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None


def _base_settings(**kwargs):
    values: dict[str, object] = {
        "ibkr_sync_enabled": True,
        "ibkr_sync_host": "127.0.0.1",
        "ibkr_sync_port": 4002,
        "ibkr_sync_client_id": 7,
        "ibkr_sync_account_mode": "paper",
        "ibkr_sync_readonly": True,
        "ibkr_enabled": True,
        "ibkr_status_check_enabled": True,
        "ibkr_gateway_url": "https://gateway.internal",
        "ibkr_account_id_hint": "DU123",
        "ibkr_expected_environment": "paper",
    }
    values.update(kwargs)
    return Settings(**values)


def test_fake_adapter_stores_orders_and_executions() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=ValidFixtureAdapter(),
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
        adapter=ValidFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["persistence_mode"] == "memory"
    assert body["persistence_status_nl"] == "Geheugenfallback actief"


def test_sync_runs_history_empty() -> None:
    response = client.get("/ibkr/sync/runs")
    assert response.status_code == 200
    body = response.json()
    assert body["items"] == []
    assert body["help_nl"] == "Nog geen read-only syncruns beschikbaar."
    assert body["actions_allowed"] is False
    assert body["safe_for_orders"] is False
    assert body["blocks_orders"] is True


def test_sync_runs_history_and_detail_after_valid_sync() -> None:
    run_body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=ValidFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    sync_run_id = str(run_body["sync_run_id"])
    history = client.get("/ibkr/sync/runs").json()
    assert len(history["items"]) == 1
    item = history["items"][0]
    assert item["sync_run_id"] == sync_run_id
    assert item["status"] == "paper_account_confirmed"
    assert item["positions_count"] == 1
    assert item["cash_values_count"] == 1
    assert item["payload_validation_status"] == "passed"
    assert item["actions_allowed"] is False
    detail = client.get(f"/ibkr/sync/runs/{sync_run_id}")
    assert detail.status_code == 200
    detail_body = detail.json()
    assert len(detail_body["positions"]) == 1
    assert len(detail_body["cash_values"]) == 1
    assert detail_body["order_submission_allowed"] is False


def test_sync_runs_history_timeout_status_uses_not_attempted_validation() -> None:
    ibkr_sync.run_sync(
        _base_settings(),
        adapter=TimeoutFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    history = client.get("/ibkr/sync/runs").json()
    assert len(history["items"]) == 1
    item = history["items"][0]
    assert item["status"] == "timeout"
    assert item["payload_validation_status"] == "not_attempted"


def test_sync_run_detail_unknown_id_returns_not_found() -> None:
    response = client.get("/ibkr/sync/runs/unknown-sync-run-id")
    assert response.status_code == 404


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
        adapter=ValidFixtureAdapter(),
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
    assert response["payload_validation_status"] == "not_attempted"
    assert response["safe_for_orders"] is False
    assert response["blocks_orders"] is True
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


def test_sync_status_no_longer_blocks_for_paper_only_relock() -> None:
    """V1 §21.1 relock: `version1_paper_only` is no longer a readiness
    blocker. With a mismatched mode the readiness still moves through
    its normal needs_control / blocked flow based on session / storage,
    not on an app-side paper-only flag."""

    response = ibkr_sync.read_status(
        _base_settings(ibkr_sync_account_mode="live", ibkr_expected_environment="paper")
    )
    assert response["sync_readiness_reason"] != "version1_paper_only"


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


def test_sync_run_no_longer_blocks_on_account_mode_mismatch() -> None:
    """V1 §21.1 relock: account-mode is reported, not gated.

    The previous ``account_mode_mismatch`` / ``version1_paper_only``
    readiness blockers are removed. With a ready paper session adapter
    the readiness status must no longer drop to ``blocked`` because of
    a paper-vs-live mismatch between the operator's
    `ibkr_sync_account_mode` setting and the session adapter's mode.
    """

    body = ibkr_sync.run_sync(
        _base_settings(ibkr_sync_account_mode="live", ibkr_expected_environment="paper"),
        adapter=RaisingSyncAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["sync_readiness_reason"] not in {
        "account_mode_mismatch",
        "version1_paper_only",
    }


def test_sync_run_no_longer_blocks_on_live_expected_environment() -> None:
    """Same V1 §21.1 relock: setting `ibkr_expected_environment=live`
    must no longer trigger a ``version1_paper_only`` blocker. The
    connected IBKR account is the authority on paper vs. live."""

    body = ibkr_sync.run_sync(
        _base_settings(ibkr_sync_account_mode="live", ibkr_expected_environment="live"),
        adapter=RaisingSyncAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["sync_readiness_reason"] != "version1_paper_only"


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
        adapter=ValidFixtureAdapter(),
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


def test_readiness_blocked_does_not_call_adapter_and_validation_not_attempted() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(ibkr_status_check_enabled=False), adapter=RaisingSyncAdapter()
    )
    assert body["sync_run_id"] is None
    assert body["payload_validation_status"] == "not_attempted"


def test_valid_adapter_sets_payload_validation_passed() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=ValidFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["payload_validation_status"] == "passed"
    assert body["payload_validation_error_count"] == 0


def test_invalid_payload_blocks_persistence_and_memory(monkeypatch) -> None:
    called = {"persist": 0}
    monkeypatch.setattr(
        ibkr_sync,
        "persist_ibkr_sync_payload",
        lambda *_args, **_kwargs: called.__setitem__("persist", called["persist"] + 1),
    )
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=InvalidFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["status"] == "payload_validation_failed"
    assert body["persistence_mode"] == "none"
    assert ibkr_sync.STORE.runs == []
    assert ibkr_sync.STORE.positions == []
    assert called["persist"] == 0
    assert body["actions_allowed"] is False
    assert body["suggestions_allowed"] is False


def test_status_before_any_run_has_not_attempted_validation() -> None:
    body = ibkr_sync.read_status(_base_settings())
    assert body["payload_validation_status"] == "not_attempted"


def test_durable_status_contract_includes_payload_validation_and_safety(
    monkeypatch,
) -> None:
    from portfolio_outlook_api import ibkr_sync_read_model, status_routes

    now = datetime.now(UTC)
    monkeypatch.setattr(api_settings.storage, "enabled", True)
    monkeypatch.setattr(api_settings.storage, "database_url", "sqlite+pysqlite:///dummy.db")
    monkeypatch.setattr(
        status_routes,
        "read_latest_ibkr_sync_run",
        lambda _s: ibkr_sync_read_model.DurableIbkrSyncReadResult(
            latest_run=SimpleNamespace(
                sync_run_id="sync-run-1",
                started_at=now,
                completed_at=now,
                provider_code="ibkr",
                provider_environment="paper",
                account_mode="paper",
                readonly=True,
                status="paper_account_confirmed",
                account_summary_status="account_summary_received",
                positions_status="positions_received",
                open_orders_status="no_open_orders",
                executions_status="no_executions",
                positions_count=1,
                cash_values_count=1,
                open_orders_count=0,
                executions_count=0,
                status_nl=None,
                next_step_nl=None,
                help_nl=None,
                actions_allowed=False,
                order_submission_allowed=False,
                order_modification_allowed=False,
                order_cancellation_allowed=False,
                suggestions_allowed=False,
            ),
            storage_help_nl=None,
        ),
    )

    response = client.get("/ibkr/sync/status").json()
    assert response["payload_validation_status"] == "not_available"
    assert response["payload_validation_status_nl"] == "Niet beschikbaar"
    assert response["payload_validation_error_count"] == 0
    assert response["payload_validation_errors"] == []
    assert "payloadvalidatie-details" in response["payload_validation_help_nl"]
    assert response["actions_allowed"] is False
    assert response["order_submission_allowed"] is False
    assert response["order_modification_allowed"] is False
    assert response["order_cancellation_allowed"] is False
    assert response["suggestions_allowed"] is False
    assert response["can_submit_orders"] is False
    assert response["safe_for_orders"] is False
    assert response["blocks_orders"] is True


def test_empty_adapter_is_supported_with_conservative_status() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=EmptyFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["status"] == "partial_data"
    assert body["payload_validation_status"] == "passed"
    assert body["positions_count"] == 0
    assert body["cash_values_count"] == 0
    assert body["open_orders_count"] == 0
    assert body["executions_count"] == 0


def test_timeout_adapter_failure_is_not_validation_failure() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=TimeoutFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["status"] == "timeout"
    assert body["payload_validation_status"] == "not_attempted"
    assert body["payload_validation_errors"] == []


def test_provider_adapter_failure_is_not_validation_failure() -> None:
    body = ibkr_sync.run_sync(
        _base_settings(),
        adapter=ProviderFailureFixtureAdapter(),
        session_status_adapter=FakeReadyPaperSessionStatusAdapter(),
    )
    assert body["status"] == "provider_error"
    assert body["payload_validation_status"] == "not_attempted"
    assert body["payload_validation_errors"] == []


def test_route_invokes_factory_and_passes_adapter_to_run_sync(monkeypatch) -> None:
    """The route must call the factory, pass the resulting adapter to run_sync,
    and call ``close()`` on it afterwards (even when readiness blocks the sync).
    """

    from portfolio_outlook_api import status_routes

    factory_calls: list[bool] = []
    close_calls: list[bool] = []
    captured_adapter: list[object] = []

    class _StubAdapter:
        def sync_account_summary(self):  # pragma: no cover - never reached here
            return []

        def sync_positions(self):  # pragma: no cover
            return []

        def sync_open_orders(self):  # pragma: no cover
            return []

        def sync_executions(self):  # pragma: no cover
            return []

        def close(self) -> None:
            close_calls.append(True)

    def _spy_factory(settings, *, app=None):
        factory_calls.append(True)
        return _StubAdapter()

    def _capture_run_sync(s, adapter=None, **_kwargs):
        captured_adapter.append(adapter)
        return {"status": "captured", "captured": True}

    monkeypatch.setattr(status_routes, "build_real_sync_adapter", _spy_factory)
    monkeypatch.setattr(status_routes, "run_sync", _capture_run_sync)

    response = client.post("/ibkr/sync/run")
    assert response.status_code == 200
    assert factory_calls == [True]
    assert len(captured_adapter) == 1
    assert isinstance(captured_adapter[0], _StubAdapter)
    # The context manager must call close() after run_sync returns.
    assert close_calls == [True]


def test_route_passes_none_when_factory_returns_none(monkeypatch) -> None:
    """When the factory returns None (real-client disabled or misconfigured),
    the route must still call run_sync, with ``adapter=None``."""

    from portfolio_outlook_api import status_routes

    captured_adapter: list[object] = []

    monkeypatch.setattr(status_routes, "build_real_sync_adapter", lambda s, app=None: None)
    monkeypatch.setattr(
        status_routes,
        "run_sync",
        lambda s, adapter=None, **_k: captured_adapter.append(adapter) or {"status": "ok"},
    )

    response = client.post("/ibkr/sync/run")
    assert response.status_code == 200
    assert captured_adapter == [None]
