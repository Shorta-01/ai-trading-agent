"""Configuration for the worker service."""

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseModel):
    """Storage configuration flags for future runtime wiring."""

    database_url: str | None = None
    enabled: bool = False
    writes_enabled: bool = False


class Settings(BaseSettings):
    service_name: str = "Portfolio Outlook Manager Worker"
    environment: str = "development"
    paper_only_mode: bool = True
    storage: StorageSettings = StorageSettings()

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()
