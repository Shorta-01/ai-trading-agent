from fastapi.testclient import TestClient

from portfolio_outlook_api.config import Settings
from portfolio_outlook_api.ibkr_session_status import IbkrSessionStatusAdapterResult
from portfolio_outlook_api.ibkr_status import build_ibkr_status_placeholder
from portfolio_outlook_api.main import app

client = TestClient(app)


class FakeStatusAdapter:
    def __init__(self, result: IbkrSessionStatusAdapterResult) -> None:
        self._result = result
        self.calls = 0

    def check_session_status(self, runtime_settings: Settings) -> IbkrSessionStatusAdapterResult:
        self.calls += 1
        return self._result


class RaisingStatusAdapter:
    def check_session_status(self, runtime_settings: Settings) -> IbkrSessionStatusAdapterResult:
        raise RuntimeError("token=abc123 should-never-leak")


def test_ibkr_status_endpoint_disabled_default_response() -> None:
    payload = client.get("/broker/ibkr/status").json()

    assert payload["enabled"] is False
    assert payload["configured"] is False
    assert payload["connection_status"] == "disabled"
    assert payload["provider"] == "ibkr"
    assert payload["actions_allowed"] is False
    assert payload["order_submission_allowed"] is False
    assert payload["order_modification_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["can_submit_orders"] is False
    assert payload["blocks_orders"] is True
    assert payload["session_adapter_family"] == "default_safe"
    assert payload["tws_readonly_adapter_enabled"] is False


def test_ibkr_status_not_configured_response() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(ibkr_enabled=True, ibkr_status_check_enabled=True)
    )

    assert payload["connection_status"] == "not_configured"
    assert payload["configured"] is False
    assert payload["status_nl"] == "IBKR niet geconfigureerd"


def test_ibkr_status_configured_with_status_check_disabled() -> None:
    adapter = FakeStatusAdapter(
        IbkrSessionStatusAdapterResult(connection_status="connection_failed")
    )
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=False,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=adapter,
    )

    assert payload["configured"] is True
    assert payload["connection_status"] == "status_check_disabled"
    assert payload["session_check_attempted"] is False
    assert adapter.calls == 0
    assert payload["blocks_orders"] is True


def test_ibkr_status_default_adapter_no_network_safe_status() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        )
    )

    assert payload["configured"] is True
    assert payload["connection_status"] == "configured_not_connected"
    assert payload["session_check_attempted"] is True
    assert payload["blocks_orders"] is True




def test_ibkr_status_explicit_tws_setting_without_client_stays_blocked() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_tws_readonly_adapter_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        )
    )

    assert payload["session_adapter_family"] == "tws_readonly"
    assert payload["tws_readonly_adapter_enabled"] is True
    assert payload["tws_readonly_adapter_runtime_available"] is False
    assert payload["connection_status"] == "configured_not_connected"
    assert payload["actions_allowed"] is False
    assert payload["order_submission_allowed"] is False

def test_ibkr_status_wrong_account_mode_via_fake_adapter() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(
                connection_status="connected_wrong_account_mode",
                account_mode_status="mismatch",
                session_status_reason="account_mode_mismatch",
            )
        ),
    )

    assert payload["connection_status"] == "connected_wrong_account_mode"
    assert payload["blocks_orders"] is True
    assert payload["sync_allowed"] is False
    assert payload["actions_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["account_mode_status"] == "mismatch"
    assert payload["order_submission_allowed"] is False
    assert payload["order_modification_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["can_submit_orders"] is False
    assert payload["safe_for_orders"] is False
    assert payload["safe_for_sync"] is False


def test_ibkr_status_explicit_mismatch_without_account_mode_stays_mismatch() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(
                connection_status="configured_not_connected",
                account_mode_status="mismatch",
            )
        ),
    )

    assert payload["connection_status"] == "configured_not_connected"
    assert payload["account_mode_status"] == "mismatch"
    assert payload["sync_allowed"] is False
    assert payload["actions_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["order_submission_allowed"] is False
    assert payload["order_modification_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["can_submit_orders"] is False
    assert payload["safe_for_orders"] is False
    assert payload["safe_for_sync"] is False
    assert payload["blocks_orders"] is True


def test_ibkr_status_account_mode_match_via_fake_adapter() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
            ibkr_expected_environment="paper",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(
                connection_status="configured_not_connected",
                account_mode_status="unknown",
                account_mode="paper",
                session_status_reason="paper_mode_seen",
            )
        ),
    )

    assert payload["connection_status"] == "configured_not_connected"
    assert payload["account_mode_status"] == "match"
    assert payload["sync_allowed"] is False
    assert payload["safe_for_sync"] is False
    assert payload["safe_for_orders"] is False
    assert payload["blocks_orders"] is True


def test_ibkr_status_infers_wrong_account_mode_from_adapter_account_mode() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
            ibkr_expected_environment="paper",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(
                connection_status="configured_not_connected",
                account_mode_status="unknown",
                account_mode="live",
            )
        ),
    )

    assert payload["connection_status"] == "connected_wrong_account_mode"
    assert payload["account_mode_status"] == "mismatch"
    assert payload["sync_allowed"] is False
    assert payload["actions_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["order_submission_allowed"] is False
    assert payload["order_modification_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["can_submit_orders"] is False
    assert payload["safe_for_orders"] is False
    assert payload["safe_for_sync"] is False
    assert payload["blocks_orders"] is True


def test_ibkr_status_unknown_without_account_mode_and_without_mismatch() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(
                connection_status="configured_not_connected",
                account_mode_status="unknown",
                account_mode=None,
            )
        ),
    )

    assert payload["account_mode_status"] == "unknown"
    assert payload["sync_allowed"] is False
    assert payload["actions_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["order_submission_allowed"] is False
    assert payload["order_modification_allowed"] is False
    assert payload["order_cancellation_allowed"] is False
    assert payload["can_submit_orders"] is False
    assert payload["safe_for_orders"] is False
    assert payload["safe_for_sync"] is False
    assert payload["blocks_orders"] is True


def test_ibkr_status_connection_failed_via_fake_adapter() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(
                connection_status="connection_failed",
                session_status_reason="gateway_unreachable",
            )
        ),
    )

    assert payload["connection_status"] == "connection_failed"
    assert payload["blocks_orders"] is True
    assert "gateway_unreachable" in str(payload)


def test_ibkr_status_authentication_required_via_fake_adapter() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(connection_status="authentication_required")
        ),
    )

    assert payload["connection_status"] == "authentication_required"
    assert payload["status_nl"] == "Aanmelding vereist"
    assert payload["blocks_orders"] is True
    assert payload["safe_for_sync"] is False
    assert payload["safe_for_orders"] is False


def test_ibkr_status_pacing_limited_via_fake_adapter() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(connection_status="pacing_limited")
        ),
    )

    assert payload["connection_status"] == "pacing_limited"
    assert payload["status_nl"] == "Snelheidslimiet actief"
    assert payload["blocks_orders"] is True
    assert payload["safe_for_sync"] is False
    assert payload["safe_for_orders"] is False


def test_ibkr_status_unknown_adapter_status_maps_to_unknown() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=FakeStatusAdapter(
            IbkrSessionStatusAdapterResult(connection_status="mystery_state")
        ),
    )

    assert payload["connection_status"] == "unknown"
    assert payload["status_nl"] == "IBKR-status onbekend"
    assert "geen actieve read-only sessie" not in payload["message_nl"]
    assert payload["sync_allowed"] is False
    assert payload["suggestions_allowed"] is False
    assert payload["blocks_orders"] is True


def test_ibkr_status_adapter_exception_maps_to_safe_blocked_status() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=True,
            ibkr_status_check_enabled=True,
            ibkr_gateway_url="https://gateway.internal",
            ibkr_account_id_hint="DU123",
        ),
        session_status_adapter=RaisingStatusAdapter(),
    )

    serialized = str(payload).lower()
    assert payload["connection_status"] == "connection_failed"
    assert payload["session_status_reason"] == "adapter_error"
    assert payload["blocks_orders"] is True
    assert "should-never-leak" not in serialized
    assert "token=abc123" not in serialized


def test_ibkr_status_endpoint_exposes_no_fake_broker_data() -> None:
    payload = client.get("/broker/ibkr/status").json()

    assert "cash" not in payload
    assert "positions" not in payload
    assert "orders" not in payload
    assert "executions" not in payload
    assert "balances" not in payload


def test_ibkr_status_endpoint_exposes_no_secrets() -> None:
    payload = client.get("/broker/ibkr/status").json()
    serialized = str(payload).lower()

    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized
    assert "database_url" not in serialized
    assert "postgres" not in serialized


def test_ibkr_session_status_endpoint_available() -> None:
    response = client.get("/ibkr/session/status")

    assert response.status_code == 200
    assert response.json()["connection_status"] == "disabled"


def test_broker_and_session_status_endpoints_both_available() -> None:
    broker_response = client.get("/broker/ibkr/status")
    session_response = client.get("/ibkr/session/status")

    assert broker_response.status_code == 200
    assert session_response.status_code == 200


def test_ibkr_status_diagnostics_default_codes_and_nl_fields() -> None:
    payload = build_ibkr_status_placeholder(Settings())

    assert payload["session_adapter_status_nl"] == "Veilige standaardadapter actief"
    assert payload["runtime_connection_allowed"] is False
    assert payload["runtime_connection_blocked_reason"] == "ibkr_not_configured"
    assert payload["manual_status_check_allowed"] is False
    assert payload["session_diagnostics_ready"] is True


def test_ibkr_status_no_secret_like_keys_in_response() -> None:
    payload = build_ibkr_status_placeholder(Settings())
    serialized = str(payload).lower()

    assert "password" not in serialized
    assert "token" not in serialized
    assert "secret" not in serialized


def test_ibkr_status_check_enabled_only_keeps_safe_default_adapter() -> None:
    payload = build_ibkr_status_placeholder(
        Settings(
            ibkr_enabled=False,
            ibkr_status_check_enabled=True,
        )
    )

    assert payload["session_adapter_family"] == "default_safe"
    assert payload["tws_readonly_adapter_enabled"] is False
    assert payload["runtime_connection_allowed"] is False
