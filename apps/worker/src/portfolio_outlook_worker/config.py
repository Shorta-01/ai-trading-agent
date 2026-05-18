"""Configuration for the worker service."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "Portfolio Outlook Manager Worker"
    environment: str = "development"
    paper_only_mode: bool = True

    model_config = SettingsConfigDict(env_prefix="WORKER_", extra="ignore")


settings = Settings()
