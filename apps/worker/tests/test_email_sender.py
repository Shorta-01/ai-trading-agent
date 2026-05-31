"""Tests for the worker-side SMTP email sender."""

from __future__ import annotations

import smtplib
from unittest.mock import MagicMock

import pytest

from portfolio_outlook_worker.email_sender import (
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
        config=None, subject="x", body_plain="y", real_client_enabled=True
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
    assert result.used_host == "smtp.example.com"


def test_sends_via_smtp_when_real_client_enabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    monkeypatch.setattr(smtplib, "SMTP", MagicMock(return_value=smtp_instance))

    result = send_email(
        config=_config(),
        subject="Test",
        body_plain="Plain",
        body_html="<p>Html</p>",
        real_client_enabled=True,
    )

    smtp_instance.starttls.assert_called_once()
    smtp_instance.login.assert_called_once_with(
        "user@example.com", "secret"
    )
    smtp_instance.send_message.assert_called_once()
    assert result.sent is True


def test_uses_smtp_ssl_on_port_465(monkeypatch: pytest.MonkeyPatch) -> None:
    smtp_instance = MagicMock()
    smtp_instance.__enter__.return_value = smtp_instance
    smtp_instance.__exit__.return_value = None
    smtp_ssl_cls = MagicMock(return_value=smtp_instance)
    monkeypatch.setattr(smtplib, "SMTP_SSL", smtp_ssl_cls)
    monkeypatch.setattr(smtplib, "SMTP", MagicMock())

    send_email(
        config=_config(port=465),
        subject="x",
        body_plain="y",
        real_client_enabled=True,
    )

    smtp_ssl_cls.assert_called_once_with("smtp.example.com", 465, timeout=10)
    smtp_instance.starttls.assert_not_called()


def test_returns_smtp_error_on_oserror(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        smtplib, "SMTP", MagicMock(side_effect=OSError("refused"))
    )
    result = send_email(
        config=_config(),
        subject="x",
        body_plain="y",
        real_client_enabled=True,
    )
    assert result.sent is False
    assert result.status == "smtp_error"


def test_public_surface_matches_api_copy() -> None:
    """The worker + api email senders are duplicated by design; this
    parity guard asserts the public symbol set + dataclass fields
    stay in sync so a divergence is caught in CI rather than at
    runtime.

    Skipped when the API package isn't installed: the worker CI job
    doesn't install ``apps/api`` (only storage), but the local dev
    venv usually has both, so the guard still fires locally.
    """

    pytest.importorskip("portfolio_outlook_api")
    from importlib import import_module

    api_module = import_module("portfolio_outlook_api.email_sender")
    worker_module = import_module("portfolio_outlook_worker.email_sender")
    api_public = set(api_module.__all__)
    worker_public = set(worker_module.__all__)
    assert api_public == worker_public, (
        f"Public surfaces diverged: api={api_public}, worker={worker_public}"
    )
    assert (
        api_module.SmtpTransportConfig.__dataclass_fields__.keys()
        == worker_module.SmtpTransportConfig.__dataclass_fields__.keys()
    )
