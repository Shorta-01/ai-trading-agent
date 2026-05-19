"""Configuration for the API service."""

from pydantic import BaseModel, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseModel):
    """Storage configuration flags for future runtime wiring."""

    database_url: str | None = None
    enabled: bool = False
    writes_enabled: bool = False


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "Portfolio Outlook Manager API"
    version: str = "0.1.0"
    environment: str = "development"
    paper_only_mode: bool = True
    storage: StorageSettings = StorageSettings()
    ibkr_enabled: bool = False
    ibkr_expected_environment: str = "paper"
    ibkr_account_id_hint: str | None = None
    ibkr_gateway_url: str | None = None
    ibkr_connection_timeout_seconds: int = 10
    ibkr_status_check_enabled: bool = False

    @field_validator("ibkr_expected_environment")
    @classmethod
    def _normalize_expected_environment(cls, value: str) -> str:
        normalized = value.strip().lower()
        return normalized or "paper"

    @field_validator("ibkr_account_id_hint", "ibkr_gateway_url", mode="before")
    @classmethod
    def _normalize_optional_string(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("ibkr_connection_timeout_seconds")
    @classmethod
    def _validate_timeout(cls, value: int) -> int:
        if value <= 0 or value > 120:
            raise ValueError("ibkr_connection_timeout_seconds must be between 1 and 120")
        return value

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()
