"""Endpoint tests for ``/settings/notifications`` + test-email."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from portfolio_outlook_api.main import app
from portfolio_outlook_api.notification_routes import (
    settings as api_settings,
)

client = TestClient(app)


def _reset() -> None:
    api_settings.smtp_host = None
    api_settings.smtp_port = 587
    api_settings.smtp_username = None
    api_settings.smtp_password = None
    api_settings.smtp_from = None
    api_settings.smtp_to = None
    api_settings.smtp_use_tls = True
    api_settings.notifications_email_enabled = False
    api_settings.notifications_email_real_client_enabled = False
    api_settings.notification_send_on_nav_drop = True
    api_settings.notification_send_on_position_drop = True
    api_settings.notification_send_on_high_confidence_sell = True
    api_settings.storage.enabled = False
    api_settings.storage.database_url = None
    api_settings.storage.writes_enabled = False


def setup_function() -> None:
    _reset()


def teardown_function() -> None:
    _reset()


def test_get_returns_defaults_when_storage_disabled() -> None:
    r = client.get("/settings/notifications")
    assert r.status_code == 200
    body = r.json()
    assert body["smtp_host"] is None
    assert body["smtp_port"] == 587
    assert body["smtp_password_set"] is False
    assert body["notifications_email_enabled"] is False
    # The master safety switch is independently env-controlled and
    # always reflects the API settings singleton.
    assert body["notifications_email_real_client_enabled"] is False


def test_get_password_set_is_true_when_settings_has_password() -> None:
    api_settings.smtp_host = "smtp.example.com"
    api_settings.smtp_password = "secret"
    r = client.get("/settings/notifications")
    body = r.json()
    assert body["smtp_password_set"] is True
    # The response NEVER includes the value itself.
    assert "smtp_password" not in body


def test_test_email_returns_config_missing_when_host_blank() -> None:
    r = client.post("/settings/notifications/test-email")
    body = r.json()
    assert body["sent"] is False
    assert body["status"] == "config_missing"


def test_test_email_returns_stubbed_when_real_client_disabled() -> None:
    api_settings.smtp_host = "smtp.example.com"
    api_settings.smtp_from = "bot@example.com"
    api_settings.smtp_to = "operator@example.com"
    api_settings.notifications_email_real_client_enabled = False
    r = client.post("/settings/notifications/test-email")
    body = r.json()
    assert body["sent"] is False
    assert body["status"] == "stubbed"
    assert body["used_host"] == "smtp.example.com"


def test_test_email_sent_when_real_client_enabled(monkeypatch) -> None:
    api_settings.smtp_host = "smtp.example.com"
    api_settings.smtp_from = "bot@example.com"
    api_settings.smtp_to = "operator@example.com"
    api_settings.smtp_username = "user"
    api_settings.smtp_password = "pwd"
    api_settings.notifications_email_real_client_enabled = True

    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=smtp_instance))

    r = client.post("/settings/notifications/test-email")
    body = r.json()
    assert body["sent"] is True
    assert body["status"] == "sent"
    smtp_instance.login.assert_called_once_with("user", "pwd")
    smtp_instance.send_message.assert_called_once()


def test_put_rejects_invalid_port() -> None:
    api_settings.storage.enabled = True
    api_settings.storage.database_url = "postgresql://fake"

    r = client.put(
        "/settings/notifications",
        json={
            "smtp_host": "smtp.example.com",
            "smtp_port": 99999,
            "smtp_username": "u",
            "smtp_password": "p",
            "smtp_from": "bot@example.com",
            "smtp_to": "op@example.com",
            "smtp_use_tls": True,
            "notifications_email_enabled": False,
            "notification_send_on_nav_drop": True,
            "notification_send_on_position_drop": True,
            "notification_send_on_high_confidence_sell": True,
        },
    )
    assert r.status_code == 422
    assert "1 en 65535" in r.json()["detail"]
