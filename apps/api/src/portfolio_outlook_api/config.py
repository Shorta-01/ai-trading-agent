"""Configuration for the API service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    app_name: str = "Portfolio Outlook Manager API"
    version: str = "0.1.0"
    environment: str = "development"
    paper_only_mode: bool = True

    model_config = SettingsConfigDict(env_prefix="API_", extra="ignore")


settings = Settings()
