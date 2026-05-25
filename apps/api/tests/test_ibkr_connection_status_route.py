"""Task 126b — ``GET /ibkr/connection/status`` route tests.

Covers the three locked outcomes (connected, disconnected via
later terminator, refused), the account-ID masking, and the
HTTP 503 fail-closed contract when storage is unavailable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch

from ai_trading_agent_storage import (
    IbkrConnectionAuditRecord,
    StorageConnectionError,
)
from fastapi.testclient import TestClient

from portfolio_outlook_api.ibkr_connection_read_model import (
    mask_account_id,
    synthesise_connection_status,
)
from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_BASE_TIME = datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)


def _audit(
    *,
    audit_id: str,
    offset_seconds: int,
    ibkr_account_id: str,
    event_type: str,
    account_mode_detected: str | None = None,
    connection_id: str | None = None,
    details_json: str | None = None,
) -> IbkrConnectionAuditRecord:
    return IbkrConnectionAuditRecord(
        audit_id=audit_id,
        event_at=_BASE_TIME + timedelta(seconds=offset_seconds),
        ibkr_account_id=ibkr_account_id,
        event_type=event_type,
        account_mode_detected=account_mode_detected,
        connection_id=connection_id,
        details_json=details_json,
    )


def _reset_settings() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"
    api_settings.storage.writes_enabled = True
    api_settings.ibkr_account_id_hint = "DU1234567"


def setup_function() -> None:
    _reset_settings()


def teardown_function() -> None:
    api_settings.ibkr_account_id_hint = None
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None


# ---- masking ----------------------------------------------------


def test_mask_account_id_returns_prefix_and_last_four_chars() -> None:
    assert mask_account_id("DU1234567") == "DU•••4567"
    assert mask_account_id("U7654321") == "U7•••4321"


def test_mask_account_id_returns_short_id_as_is() -> None:
    assert mask_account_id("DU123") == "DU123"


def test_mask_account_id_returns_none_for_empty() -> None:
    assert mask_account_id(None) is None
    assert mask_account_id("") is None


# ---- synthesis --------------------------------------------------


def test_synthesise_returns_disconnected_when_no_rows() -> None:
    status = synthesise_connection_status(
        tuple(), configured_account_id="DU1234567"
    )
    assert status.connected is False
    assert status.account_mode == "unknown"
    assert status.account_id == "DU1234567"
    assert status.verified_at is None
    assert status.error_nl is None


def test_synthesise_returns_disconnected_when_connect_success_followed_by_disconnect() -> None:
    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            ibkr_account_id="DU1234567",
            event_type="connect_success",
            account_mode_detected="paper",
            connection_id="conn-1",
        ),
        _audit(
            audit_id="r2",
            offset_seconds=10,
            ibkr_account_id="DU1234567",
            event_type="disconnect",
            account_mode_detected="paper",
            connection_id="conn-1",
        ),
    )
    status = synthesise_connection_status(
        rows, configured_account_id="DU1234567"
    )
    # Note: the algorithm scans newest-first; the disconnect is
    # encountered before the success and so connected stays False.
    assert status.connected is False
    assert status.account_mode == "paper"
    assert status.verified_at == _BASE_TIME
    assert status.error_nl is not None
    assert "gesloten" in status.error_nl


def test_synthesise_returns_connected_when_only_success_row_present() -> None:
    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            ibkr_account_id="DU1234567",
            event_type="connect_success",
            account_mode_detected="paper",
            connection_id="conn-1",
        ),
    )
    status = synthesise_connection_status(
        rows, configured_account_id="DU1234567"
    )
    assert status.connected is True
    assert status.account_mode == "paper"
    assert status.error_nl is None


def test_synthesise_surfaces_refusal_when_only_refusal_present() -> None:
    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            ibkr_account_id="DU1234567",
            event_type="connect_refused",
            details_json=json.dumps({"reason": "mode_check_disagreement"}),
        ),
    )
    status = synthesise_connection_status(
        rows, configured_account_id="DU1234567"
    )
    assert status.connected is False
    assert status.account_mode == "unknown"
    assert status.error_nl is not None
    assert "geweigerd" in status.error_nl


def test_synthesise_returns_live_when_success_row_reports_live() -> None:
    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            ibkr_account_id="U7654321",
            event_type="connect_success",
            account_mode_detected="live",
            connection_id="conn-1",
        ),
    )
    status = synthesise_connection_status(
        rows, configured_account_id="U7654321"
    )
    assert status.connected is True
    assert status.account_mode == "live"


def test_synthesise_ignores_rows_from_other_accounts() -> None:
    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            ibkr_account_id="DU9999999",
            event_type="connect_success",
            account_mode_detected="paper",
        ),
    )
    status = synthesise_connection_status(
        rows, configured_account_id="DU1234567"
    )
    assert status.connected is False
    assert status.account_mode == "unknown"


# ---- route ------------------------------------------------------


def _patch_storage_read(rows: tuple[IbkrConnectionAuditRecord, ...]) -> Any:
    """Patch the route's storage path to return canned audit rows."""

    def _fake_read_connection_status(
        storage: object,  # noqa: ARG001
        *,
        configured_account_id: str | None,
        audit_limit: int = 200,  # noqa: ARG001
    ) -> object:
        return synthesise_connection_status(
            rows, configured_account_id=configured_account_id
        )

    return patch(
        "portfolio_outlook_api.ibkr_connection_routes.read_connection_status",
        side_effect=_fake_read_connection_status,
    )


def test_route_returns_connected_payload_with_masked_account_id() -> None:
    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            ibkr_account_id="DU1234567",
            event_type="connect_success",
            account_mode_detected="paper",
            connection_id="conn-1",
        ),
    )
    with _patch_storage_read(rows):
        response = client.get("/ibkr/connection/status")

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "connected": True,
        "account_id": "DU•••4567",
        "account_mode": "paper",
        "verified_at": _BASE_TIME.isoformat(),
        "error": None,
        "safe_for_action_drafts": False,
        "safe_for_orders": False,
    }


def test_route_returns_503_with_dutch_body_when_storage_unavailable() -> None:
    with patch(
        "portfolio_outlook_api.ibkr_connection_routes.read_connection_status",
        side_effect=StorageConnectionError("storage down"),
    ):
        response = client.get("/ibkr/connection/status")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


def test_route_returns_safe_for_orders_false_even_on_happy_path() -> None:
    """Manual approval gate stays: the status route never authorises orders."""

    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            ibkr_account_id="U7654321",
            event_type="connect_success",
            account_mode_detected="live",
        ),
    )
    api_settings.ibkr_account_id_hint = "U7654321"
    with _patch_storage_read(rows):
        body = client.get("/ibkr/connection/status").json()
    assert body["safe_for_orders"] is False
    assert body["safe_for_action_drafts"] is False
    assert body["account_mode"] == "live"
