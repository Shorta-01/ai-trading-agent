"""Task 126b — ``GET /ibkr/connection/audit`` route tests."""

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

from portfolio_outlook_api.main import app
from portfolio_outlook_api.status_routes import settings as api_settings

client = TestClient(app)

_BASE_TIME = datetime(2026, 5, 25, 12, 0, 0, tzinfo=UTC)


def _audit(
    *,
    audit_id: str,
    offset_seconds: int,
    event_type: str,
    ibkr_account_id: str = "DU1234567",
    account_mode_detected: str | None = "paper",
    connection_id: str | None = None,
    details: dict[str, object] | None = None,
) -> IbkrConnectionAuditRecord:
    return IbkrConnectionAuditRecord(
        audit_id=audit_id,
        event_at=_BASE_TIME + timedelta(seconds=offset_seconds),
        ibkr_account_id=ibkr_account_id,
        event_type=event_type,
        account_mode_detected=account_mode_detected,
        connection_id=connection_id,
        details_json=None if details is None else json.dumps(details),
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


def _patch_audit_rows(rows: tuple[IbkrConnectionAuditRecord, ...]) -> Any:
    def _fake_list(
        storage: object,  # noqa: ARG001
        *,
        limit: int,
        configured_account_id: str | None = None,  # noqa: ARG001
    ) -> tuple[IbkrConnectionAuditRecord, ...]:
        return rows[:limit]

    return patch(
        "portfolio_outlook_api.ibkr_connection_routes.list_connection_audit_rows",
        side_effect=_fake_list,
    )


def test_route_returns_rows_with_masked_account_id() -> None:
    rows = (
        _audit(audit_id="r2", offset_seconds=10, event_type="connect_success"),
        _audit(audit_id="r1", offset_seconds=0, event_type="connect_attempt"),
    )
    with _patch_audit_rows(rows):
        response = client.get("/ibkr/connection/audit")

    assert response.status_code == 200
    body = response.json()
    assert body["safe_for_action_drafts"] is False
    assert body["safe_for_orders"] is False
    assert len(body["items"]) == 2
    first = body["items"][0]
    assert first["id"] == "r2"
    assert first["ibkr_account_id"] == "DU•••4567"
    assert first["event_type"] == "connect_success"
    assert first["event_at"].startswith("2026-05-25T")


def test_route_respects_limit_query_param() -> None:
    rows = tuple(
        _audit(
            audit_id=f"r{i}",
            offset_seconds=i,
            event_type="connect_success",
        )
        for i in range(10)
    )
    with _patch_audit_rows(rows):
        response = client.get("/ibkr/connection/audit?limit=3")
    assert response.status_code == 200
    assert len(response.json()["items"]) == 3


def test_route_clamps_limit_to_locked_max() -> None:
    """``limit > 200`` is rejected as a validation error."""

    response = client.get("/ibkr/connection/audit?limit=999")
    assert response.status_code == 422


def test_route_clamps_limit_to_locked_min() -> None:
    """``limit < 1`` is rejected as a validation error."""

    response = client.get("/ibkr/connection/audit?limit=0")
    assert response.status_code == 422


def test_route_returns_503_with_dutch_body_when_storage_unavailable() -> None:
    with patch(
        "portfolio_outlook_api.ibkr_connection_routes.list_connection_audit_rows",
        side_effect=StorageConnectionError("down"),
    ):
        response = client.get("/ibkr/connection/audit")
    assert response.status_code == 503
    assert response.json() == {"detail": "Opslag is niet beschikbaar."}


def test_route_preserves_details_json_when_present() -> None:
    rows = (
        _audit(
            audit_id="r1",
            offset_seconds=0,
            event_type="connect_refused",
            details={"reason": "mode_check_disagreement"},
        ),
    )
    with _patch_audit_rows(rows):
        body = client.get("/ibkr/connection/audit").json()
    assert body["items"][0]["details_json"] is not None
    assert "mode_check_disagreement" in body["items"][0]["details_json"]
