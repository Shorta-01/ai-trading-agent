"""Configuration for the API service."""

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseModel):
    """Storage configuration flags for future runtime wiring."""

    database_url: str | None = None
    enabled: bool = False
    writes_enabled: bool = False




class ResearchUploadSettings(BaseModel):
    """Research source archive upload safety configuration."""

    enabled: bool = False
    archive_dir: str = "var/research-source-archive"
    max_file_size_bytes: int = 20 * 1024 * 1024
    allowed_extensions: tuple[str, ...] = (
        ".pdf",
        ".txt",
        ".md",
        ".csv",
        ".docx",
        ".xlsx",
        ".pptx",
    )
    allowed_content_types: tuple[str, ...] = (
        "application/pdf",
        "text/plain",
        "text/markdown",
        "text/csv",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    )

    @field_validator("archive_dir")
    @classmethod
    def _validate_archive_dir(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned == "":
            raise ValueError("research upload archive_dir must be non-empty")
        return cleaned

    @field_validator("max_file_size_bytes")
    @classmethod
    def _validate_max_size(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("research upload max_file_size_bytes must be positive")
        return value


class ResearchExtractionSettings(BaseModel):
    """Deterministic extracted-text runtime settings."""

    enabled: bool = False
    extracted_text_archive_dir: str = "var/research-extracted-text"
    max_input_file_size_bytes: int = 20 * 1024 * 1024
    max_output_characters: int = 2_000_000
    preview_max_characters: int = 1_000
    allowed_extensions: tuple[str, ...] = (".txt", ".md", ".csv")

    @field_validator("extracted_text_archive_dir")
    @classmethod
    def _validate_archive_dir(cls, value: str) -> str:
        cleaned = value.strip()
        if cleaned == "":
            raise ValueError("research extraction extracted_text_archive_dir must be non-empty")
        return cleaned

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
    ibkr_tws_readonly_adapter_enabled: bool = False
    ibkr_tws_readonly_runtime_enabled: bool = False
    ibkr_tws_readonly_real_client_enabled: bool = False
    ibkr_account_snapshot_preflight_enabled: bool = False
    ibkr_market_data_enabled: bool = False
    ibkr_market_data_host: str | None = None
    ibkr_market_data_port: int | None = None
    ibkr_market_data_client_id: int | None = None
    ibkr_market_data_readonly: bool = True
    ibkr_market_data_account_mode: str = "paper"
    ibkr_market_data_type: str = "delayed"
    ibkr_market_data_snapshot_timeout_seconds: int = 5
    ibkr_market_data_provider_code: str = "ibkr"
    ibkr_sync_enabled: bool = False
    ibkr_sync_host: str | None = None
    ibkr_sync_port: int | None = None
    ibkr_sync_client_id: int | None = None
    ibkr_sync_account_mode: str = "paper"
    ibkr_sync_readonly: bool = True
    ibkr_sync_timeout_seconds: int = 10
    ibkr_sync_provider_code: str = "ibkr"
    ibkr_sync_real_client_enabled: bool = False
    ibkr_sync_account_summary_tags: str = (
        "TotalCashValue,AvailableFunds,BuyingPower,NetLiquidation,GrossPositionValue"
    )
    market_data_provider: str = "none"
    market_data_sync_enabled: bool = False
    market_data_sync_max_assets: int = 50
    eodhd_enabled: bool = False
    eodhd_api_key: str | None = None
    eodhd_base_url: str = "https://eodhd.com/api"
    eodhd_request_timeout_seconds: int = 10
    fx_provider: str = "none"
    fx_sync_enabled: bool = False
    forecast_sync_enabled: bool = False
    forecast_history_lookback_days: int = 400
    forecast_horizon_trading_days: int = 21
    forecast_minimum_bars_required: int = 60
    forecast_max_assets_per_run: int = 50
    forecast_valid_minutes: int = 1440
    suggestions_sync_enabled: bool = False
    suggestions_risk_profile: str = "Gebalanceerd"
    suggestions_valid_minutes: int = 1440
    decision_packages_sync_enabled: bool = False
    decision_packages_valid_minutes: int = 1440
    action_drafts_sync_enabled: bool = False
    action_drafts_default_buy_value: str = "1000"
    action_drafts_top_up_pct: str = "0.25"
    action_drafts_reduce_pct: str = "0.25"
    research_upload: ResearchUploadSettings = Field(default_factory=ResearchUploadSettings)
    research_extraction: ResearchExtractionSettings = Field(
        default_factory=ResearchExtractionSettings
    )

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
