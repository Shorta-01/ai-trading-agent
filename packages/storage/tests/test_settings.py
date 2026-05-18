from ai_trading_agent_storage.settings import (
    build_database_connection_settings,
    redact_database_url,
)


def test_redact_none_returns_not_configured() -> None:
    assert redact_database_url(None) == "Niet ingesteld"


def test_build_settings_none_not_configured() -> None:
    settings = build_database_connection_settings(None)
    assert settings.database_url_configured is False
    assert settings.safe_database_label == "Niet ingesteld"
    assert "nog geen actieve databaseverbinding" in settings.explanation_nl


def test_redact_hides_password() -> None:
    redacted = redact_database_url("postgresql://user:supersecret@localhost:5432/ai_trading_agent")
    assert redacted == "postgresql://user:***@localhost:5432/ai_trading_agent"
    assert "supersecret" not in redacted


def test_redact_keeps_username_without_invented_password() -> None:
    redacted = redact_database_url("postgresql://user@localhost:5432/ai_trading_agent")
    assert redacted == "postgresql://user@localhost:5432/ai_trading_agent"
    assert ":***@" not in redacted


def test_safe_label_never_contains_raw_password() -> None:
    raw_url = "postgresql://user:rawpass@localhost:5432/ai_trading_agent"
    settings = build_database_connection_settings(raw_url)
    assert "rawpass" not in settings.safe_database_label
