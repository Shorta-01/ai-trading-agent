from portfolio_outlook_api.config import Settings


def test_default_storage_settings_are_safe() -> None:
    settings = Settings()

    assert settings.storage.database_url is None
    assert settings.storage.enabled is False
    assert settings.storage.writes_enabled is False


def test_database_url_is_optional() -> None:
    settings = Settings()

    assert settings.storage.database_url is None


def test_storage_database_url_is_stored_only() -> None:
    database_url = "postgresql+psycopg://user:pass@localhost:5432/portfolio"
    settings = Settings(
        storage={
            "database_url": database_url,
        }
    )

    assert settings.storage.database_url == database_url
    assert settings.storage.enabled is False
    assert settings.storage.writes_enabled is False


def test_default_ibkr_settings_are_safe() -> None:
    settings = Settings()

    assert settings.ibkr_enabled is False
    assert settings.ibkr_expected_environment == "paper"
    assert settings.ibkr_account_id_hint is None
    assert settings.ibkr_gateway_url is None
    assert settings.ibkr_connection_timeout_seconds == 10
    assert settings.ibkr_status_check_enabled is False


def test_ibkr_optional_strings_and_timeout_validation() -> None:
    settings = Settings(
        ibkr_account_id_hint="   ",
        ibkr_gateway_url="  https://localhost:5000  ",
        ibkr_connection_timeout_seconds=20,
    )

    assert settings.ibkr_account_id_hint is None
    assert settings.ibkr_gateway_url == "https://localhost:5000"
    assert settings.ibkr_connection_timeout_seconds == 20
