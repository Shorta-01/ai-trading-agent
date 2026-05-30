"""Tests for the editable IBKR connection + Claude AI settings API."""

from __future__ import annotations

import json
from decimal import Decimal

from ai_trading_agent_storage.metadata import metadata
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from portfolio_outlook_api.config import settings as api_settings
from portfolio_outlook_api.main import app
from portfolio_outlook_api.runtime_config_routes import (
    apply_runtime_config_overlay,
)

client = TestClient(app)

_SECRET_KEY = "sk-ant-super-secret-value-123"


def _reset() -> None:
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False
    # Restore the env defaults the GET-fallback test mutates, so this module
    # never leaks state into other tests sharing the settings singleton.
    api_settings.ibkr_account_id_hint = None
    api_settings.ai_explanation_enabled = False
    api_settings.claude_ai_api_key = None


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def _seed(tmp_path) -> None:  # type: ignore[no-untyped-def]
    db_url = f"sqlite+pysqlite:///{tmp_path / 'runtime_config.sqlite'}"
    api_settings.storage.enabled = True
    api_settings.storage.database_url = db_url
    api_settings.storage.writes_enabled = True
    engine = create_engine(db_url)
    with engine.begin() as conn:
        metadata.create_all(conn)
        conn.execute(
            text("CREATE TABLE alembic_version (version_num VARCHAR(32) NOT NULL)")
        )
        conn.execute(
            text(
                "INSERT INTO alembic_version (version_num) VALUES "
                "('0057_runtime_config_order_policy')"
            )
        )


def test_get_returns_defaults_with_key_set_false_when_no_row(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    api_settings.ibkr_account_id_hint = "U7654321"
    api_settings.ai_explanation_enabled = True
    api_settings.claude_ai_api_key = None

    resp = client.get("/settings/connection")
    assert resp.status_code == 200
    body = resp.json()
    # Env/config defaults surface when no DB row exists.
    assert body["ibkr_account_id"] == "U7654321"
    assert body["ai_explanation_enabled"] is True
    # Worker-side display defaults.
    assert body["ibkr_host"] == "127.0.0.1"
    assert body["ibkr_port"] == 7497
    assert body["ibkr_client_id"] == 1
    # No stored key -> key_set false, and never the key value itself.
    assert body["claude_ai_api_key_set"] is False
    assert "claude_ai_api_key" not in body


def test_put_persists_get_reflects_and_key_never_returned(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    payload = {
        "ibkr_enabled": True,
        "ibkr_account_id": "DU1111111",
        "ibkr_host": "10.0.0.5",
        "ibkr_port": 4002,
        "ibkr_client_id": 7,
        "ai_explanation_enabled": True,
        "claude_ai_explanation_model": "claude-opus-4-7",
        "claude_ai_budget_monthly_eur": "75.50",
        "claude_ai_api_key": _SECRET_KEY,
    }
    put = client.put("/settings/connection", json=payload)
    assert put.status_code == 200
    saved = put.json()
    assert saved["ibkr_account_id"] == "DU1111111"
    assert saved["ibkr_port"] == 4002
    assert saved["claude_ai_explanation_model"] == "claude-opus-4-7"
    assert saved["claude_ai_budget_monthly_eur"] == "75.5"
    assert saved["claude_ai_api_key_set"] is True
    # The key value must never appear in any response.
    assert _SECRET_KEY not in json.dumps(saved)
    assert "claude_ai_api_key" not in saved

    # A fresh GET reflects the committed values and still masks the key.
    body = client.get("/settings/connection").json()
    assert body["ibkr_enabled"] is True
    assert body["ibkr_account_id"] == "DU1111111"
    assert body["ibkr_host"] == "10.0.0.5"
    assert body["ibkr_port"] == 4002
    assert body["ibkr_client_id"] == 7
    assert body["claude_ai_budget_monthly_eur"] == "75.5"
    assert body["claude_ai_api_key_set"] is True
    assert _SECRET_KEY not in json.dumps(body)


def test_put_without_key_preserves_existing_key(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    # First save WITH a key.
    first = {
        "ibkr_enabled": True,
        "ibkr_account_id": "DU2222222",
        "ibkr_host": "127.0.0.1",
        "ibkr_port": 7497,
        "ibkr_client_id": 1,
        "ai_explanation_enabled": False,
        "claude_ai_explanation_model": "claude-haiku-4-5",
        "claude_ai_budget_monthly_eur": "50",
        "claude_ai_api_key": _SECRET_KEY,
    }
    assert client.put("/settings/connection", json=first).status_code == 200

    # Second save WITHOUT a key (omitted) must keep the stored one.
    second = {
        "ibkr_enabled": False,
        "ibkr_account_id": "DU2222222",
        "ibkr_host": "127.0.0.1",
        "ibkr_port": 7497,
        "ibkr_client_id": 1,
        "ai_explanation_enabled": True,
        "claude_ai_explanation_model": "claude-haiku-4-5",
        "claude_ai_budget_monthly_eur": "50",
    }
    resp = client.put("/settings/connection", json=second)
    assert resp.status_code == 200
    saved = resp.json()
    assert saved["claude_ai_api_key_set"] is True
    assert saved["ai_explanation_enabled"] is True
    assert _SECRET_KEY not in json.dumps(saved)

    body = client.get("/settings/connection").json()
    assert body["claude_ai_api_key_set"] is True
    assert _SECRET_KEY not in json.dumps(body)


def test_put_with_blank_key_preserves_existing_key(
    tmp_path,
) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    first = {
        "ibkr_enabled": True,
        "ibkr_account_id": "DU3333333",
        "ai_explanation_enabled": True,
        "claude_ai_api_key": _SECRET_KEY,
    }
    assert client.put("/settings/connection", json=first).status_code == 200

    # Explicit empty string must NOT clobber the stored key.
    second = {
        "ibkr_enabled": True,
        "ibkr_account_id": "DU3333333",
        "ai_explanation_enabled": True,
        "claude_ai_api_key": "",
    }
    resp = client.put("/settings/connection", json=second)
    assert resp.status_code == 200
    assert resp.json()["claude_ai_api_key_set"] is True


def test_put_invalid_type_returns_422(tmp_path) -> None:  # type: ignore[no-untyped-def]
    _seed(tmp_path)
    payload = {
        "ibkr_enabled": True,
        "ibkr_port": "not-a-number",
        "ai_explanation_enabled": True,
    }
    resp = client.put("/settings/connection", json=payload)
    assert resp.status_code == 422


class _DummySettings:
    """Stand-in for the settings singleton for the overlay unit test."""

    ibkr_account_id_hint: str | None = "ENV-ACCT"
    claude_ai_api_key: str | None = None
    claude_ai_explanation_model: str = "env-model"
    claude_ai_budget_monthly_eur: Decimal = Decimal("50")
    ai_explanation_enabled: bool = False


def test_apply_runtime_config_overlay_applies_non_null_values() -> None:
    from datetime import UTC, datetime

    from ai_trading_agent_storage import RuntimeConfigRecord

    dummy = _DummySettings()
    record = RuntimeConfigRecord(
        config_id="default",
        ibkr_enabled=True,
        ibkr_account_id="DB-ACCT",
        ibkr_host="127.0.0.1",
        ibkr_port=7497,
        ibkr_client_id=1,
        ai_explanation_enabled=True,
        claude_ai_explanation_model="db-model",
        claude_ai_budget_monthly_eur=Decimal("99"),
        claude_ai_api_key="db-key",
        updated_at=datetime.now(UTC),
    )
    apply_runtime_config_overlay(dummy, record)

    assert dummy.ibkr_account_id_hint == "DB-ACCT"
    assert dummy.claude_ai_api_key == "db-key"
    assert dummy.claude_ai_explanation_model == "db-model"
    assert dummy.claude_ai_budget_monthly_eur == Decimal("99")
    assert dummy.ai_explanation_enabled is True


def test_apply_runtime_config_overlay_keeps_defaults_on_null_values() -> None:
    from datetime import UTC, datetime

    from ai_trading_agent_storage import RuntimeConfigRecord

    dummy = _DummySettings()
    record = RuntimeConfigRecord(
        config_id="default",
        ibkr_enabled=False,
        ibkr_account_id=None,
        ibkr_host=None,
        ibkr_port=None,
        ibkr_client_id=None,
        ai_explanation_enabled=False,
        claude_ai_explanation_model=None,
        claude_ai_budget_monthly_eur=None,
        claude_ai_api_key=None,
        updated_at=datetime.now(UTC),
    )
    apply_runtime_config_overlay(dummy, record)

    # Null DB values must not clobber the env defaults...
    assert dummy.ibkr_account_id_hint == "ENV-ACCT"
    assert dummy.claude_ai_api_key is None
    assert dummy.claude_ai_explanation_model == "env-model"
    assert dummy.claude_ai_budget_monthly_eur == Decimal("50")
    # ...but the non-null boolean column always wins.
    assert dummy.ai_explanation_enabled is False
