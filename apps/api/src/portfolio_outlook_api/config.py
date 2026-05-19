"""Configuration for the API service."""

from pydantic import BaseModel
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

    model_config = SettingsConfigDict(
        env_prefix="API_",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()
