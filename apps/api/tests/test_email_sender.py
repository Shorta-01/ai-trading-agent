"""Tests for the SMTP-backed email sender."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock

import pytest

from portfolio_outlook_api.email_sender import (
    SmtpTransportConfig,
    send_email,
)


def _config(**overrides) -> SmtpTransportConfig:
    defaults = dict(
        host="smtp.example.com",
        port=587,
        username="user@example.com",
        password="secret",
        from_address="bot@example.com",
        to_address="operator@example.com",
        use_tls=True,
    )
    defaults.update(overrides)
    return SmtpTransportConfig(**defaults)


def test_returns_config_missing_when_config_is_none() -> None:
    result = send_email(
        config=None,
        subject="x",
        body_plain="y",
        real_client_enabled=True,
    )
    assert result.sent is False
    assert result.status == "config_missing"


def test_returns_stubbed_when_real_client_disabled() -> None:
    result = send_email(
        config=_config(),
        subject="Test",
        body_plain="Body",
        real_client_enabled=False,
    )
    assert result.sent is False
    assert result.status == "stubbed"
    # Stub mode never reaches the SMTP layer; ``used_host`` carries
    # the configured value so the API can echo it back in the response.
    assert result.used_host == "smtp.example.com"


def test_calls_smtp_login_and_send_when_real_client_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    smtp_cls = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr(smtplib, "SMTP", smtp_cls)

    result = send_email(
        config=_config(),
        subject="Test",
        body_plain="Plain",
        body_html="<p>Html</p>",
        real_client_enabled=True,
    )

    smtp_cls.assert_called_once_with("smtp.example.com", 587, timeout=10)
    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with(
        "user@example.com", "secret"
    )
    smtp_instance.send_message.assert_called_once()
    assert result.sent is True
    assert result.status == "sent"


def test_uses_smtp_ssl_on_port_465(monkeypatch: pytest.MonkeyPatch) -> None:
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    smtp_ssl_cls = MagicMock(return_value=smtp_instance)
    plain_smtp_cls = MagicMock()  # must not be called
    monkeypatch.setattr(smtplib, "SMTP_SSL", smtp_ssl_cls)
    monkeypatch.setattr(smtplib, "SMTP", plain_smtp_cls)

    send_email(
        config=_config(port=465),
        subject="x",
        body_plain="y",
        real_client_enabled=True,
    )

    smtp_ssl_cls.assert_called_once_with("smtp.example.com", 465, timeout=10)
    plain_smtp_cls.assert_not_called()
    # ``starttls`` is wrong on port 465 (already SSL); the sender skips it.
    smtp_instance.starttls.assert_not_called()


def test_skips_login_when_no_credentials_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=smtp_instance))

    send_email(
        config=_config(username=None, password=None),
        subject="x",
        body_plain="y",
        real_client_enabled=True,
    )

    smtp_instance.login.assert_not_called()
    smtp_instance.send_message.assert_called_once()


def test_returns_smtp_error_on_smtplib_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    smtp_instance.send_message.side_effect = smtplib.SMTPRecipientsRefused({})
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=smtp_instance))

    result = send_email(
        config=_config(),
        subject="x",
        body_plain="y",
        real_client_enabled=True,
    )
    assert result.sent is False
    assert result.status == "smtp_error"
    assert "SMTP" in result.detail_nl


def test_returns_smtp_error_on_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    smtp_cls = MagicMock(side_effect=OSError("connection refused"))
    monkeypatch.setattr(smtplib, "SMTP", smtp_cls)

    result = send_email(
        config=_config(),
        subject="x",
        body_plain="y",
        real_client_enabled=True,
    )
    assert result.sent is False
    assert result.status == "smtp_error"
    assert "connection refused" in result.detail_nl


def test_html_alternative_is_attached_when_body_html_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=smtp_instance))

    send_email(
        config=_config(),
        subject="x",
        body_plain="plain",
        body_html="<p>html</p>",
        real_client_enabled=True,
    )

    # The send_message call's first arg is the EmailMessage; assert it
    # carries an HTML alternative.
    sent_message = smtp_instance.send_message.call_args[0][0]
    payload_types = {
        part.get_content_type() for part in sent_message.walk()
    }
    assert "text/html" in payload_types
    assert "text/plain" in payload_types
