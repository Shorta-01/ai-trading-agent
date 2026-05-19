from portfolio_outlook_worker.config import Settings


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
