"""Configuration for the API service."""

from decimal import Decimal

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
    # Cadence (minutes) for the scheduled read-only IBKR sync that refreshes the
    # dashboard's positions/cash/valuation. Only used when the scheduler + sync
    # are enabled.
    ibkr_sync_interval_minutes: int = 15
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
    # Opt-in: combine the classical predictor ensemble (GBM + Momentum +
    # Mean-reversion, plus QVM when fundamentals are available) instead of the
    # single GBM baseline. Default off — flipping it changes live suggestions.
    forecast_ensemble_enabled: bool = False
    forecast_history_lookback_days: int = 400
    forecast_horizon_trading_days: int = 21
    forecast_minimum_bars_required: int = 60
    forecast_max_assets_per_run: int = 50
    forecast_valid_minutes: int = 1440
    # V1.1.0 Task 130: pilot conids whose baseline forecasts the
    # /forecast/by-account route surfaces. CSV-formatted env var
    # (e.g. ``ASML.AS,ASML.MI``). Defaults to ``ASML.AS`` per the
    # locked pilot-asset decision.
    forecast_pilot_conids: str = "ASML.AS"
    suggestions_sync_enabled: bool = False
    suggestions_risk_profile: str = "Gebalanceerd"
    suggestions_valid_minutes: int = 1440
    decision_packages_sync_enabled: bool = False
    decision_packages_valid_minutes: int = 1440
    action_drafts_sync_enabled: bool = False
    action_drafts_default_buy_value: str = "1000"
    action_drafts_top_up_pct: str = "0.25"
    action_drafts_reduce_pct: str = "0.25"
    ibkr_paper_order_submission_enabled: bool = False
    ibkr_paper_order_submission_real_client_enabled: bool = False
    ibkr_paper_order_submission_host: str | None = None
    ibkr_paper_order_submission_port: int | None = None
    ibkr_paper_order_submission_client_id: int | None = None
    ibkr_paper_order_submission_timeout_seconds: int = 10
    ibkr_paper_order_submission_provider_code: str = "ibkr"
    action_draft_approval_valid_minutes: int = 5
    reconciliation_sync_enabled: bool = False
    prediction_diary_sync_enabled: bool = False
    prediction_diary_inconclusive_tolerance_pct: str = "0.25"
    ai_explanation_enabled: bool = False
    ai_explanation_real_client_enabled: bool = False
    ai_explanation_provider_code: str = "stub"
    ai_explanation_max_output_chars: int = 2000
    # Optional path to an external Dutch system-prompt file (intent
    # ai-usage.md §2 Layer 1: prompt-as-data). When unset, the locked in-code
    # default is used and behaviour is unchanged; when set, the file is loaded
    # at provider-build time and a missing/empty file fails loudly.
    ai_explanation_prompt_path: str | None = None
    daily_briefing_sync_enabled: bool = False
    daily_briefing_lookback_hours: int = 24
    scheduler_enabled: bool = False
    scheduler_timezone: str = "Europe/Brussels"
    scheduler_daily_briefing_cron: str = "30 6 * * *"
    # Legacy flag: when False (the new default) the API stops owning
    # cron registration — the worker triggers /scheduler/runs/morning-chain
    # and /ibkr/sync/run via HTTP instead. This avoids the multi-replica
    # race on the lock-less scheduler_runs table. Operators that still
    # rely on the API-process cron must set this to True explicitly.
    scheduler_api_legacy_cron: bool = False
    universe_scan_sync_enabled: bool = False
    universe_scan_max_tickers_per_run: int = 50
    universe_scan_history_lookback_days: int = 400
    ai_ts_predictor_enabled: bool = False
    ai_ts_predictor_real_client_enabled: bool = False
    ai_ts_predictor_provider_code: str = "stub"
    # V1.1 Slice 30: daily-only invocation lock. When True (default)
    # the orchestrator only calls the real AI TS provider as part of
    # the scheduler-driven morning chain; on-demand routes fall back
    # to the stub.
    ai_ts_predictor_daily_only: bool = True
    ai_ts_predictor_max_tokens: int = 1024
    # V1.1 §22.2: monthly budget cap for real Anthropic Claude calls.
    # Wired by Slice 29 (real explanation provider) + Slice 30 (real TS
    # predictor); declared here so the env-var surface is documented from
    # Slice 23 onward. Default 50 EUR locked by §22.2.
    claude_ai_budget_monthly_eur: Decimal = Decimal("50")
    # V1.1 Slice 29: model + API key for the real Anthropic Claude
    # explanation provider. The key has no committed default; it must
    # come from the env. Claude Haiku 4.5 is the cheapest tier
    # suitable for the paraphrase task.
    claude_ai_explanation_model: str = "claude-haiku-4-5-20251001"
    claude_ai_api_key: str | None = None
    claude_ai_explanation_max_output_chars: int = 2000
    # V1.1 §22.4: operator-selectable universe set. Wired by Slice 31;
    # default `SP500` keeps V1 behaviour (the locked registry is a
    # subset of S&P 500 + the EU + Bel/AEX cross-listings).
    universe_set: str = "SP500"
    # V1.1 Slice 31: per-set EODHD-call cache TTL. When > 0 the
    # universe scan skips symbols whose latest persisted snapshot is
    # younger than the TTL — keeps EODHD call volume sane on
    # ``ALL_5K``. 0 disables caching (every fire fetches fresh).
    universe_scan_cache_ttl_hours: int = 24
    # V1.1 Slice 24 + 25: backtesting opt-in. Default False keeps the
    # morning chain running on the V1 predictors until Slice 26 wires
    # the auto-weight feedback loop.
    predictor_backtest_enabled: bool = False
    # V1.1 Slice 26: ensemble weight strategy.
    # `equal_weight` keeps V1 behaviour; `auto` reads the per-predictor
    # rolling Brier-score history and inverse-Brier-weights it (clipped
    # per-predictor to the locked band).
    ensemble_weight_strategy: str = "equal_weight"
    # V1.1 Slice 27 GBM rebuild knobs. Defaults preserve V1 behaviour
    # exactly; the operator opts into the rebuild via env var and the
    # Slice 26 leaderboard surfaces whether the rebuild actually
    # improves Brier-score on real bars.
    gbm_drift_window_days: int | None = None
    gbm_regime_shift_enabled: bool = False
    gbm_regime_shift_threshold_pct: Decimal = Decimal("5.0")
    gbm_garch_enabled: bool = False  # reserved; raises NotImplementedError if set True
    # V1.1 Slice 27 Momentum rebuild knobs.
    momentum_horizon_scaled_thresholds: bool = False
    momentum_skip_week_short_horizon: bool = False
    # V1.1 Slice 28 Mean-Rev rebuild knob.
    mean_reversion_hurst_asymmetric_target: bool = False
    # V1.1 Slice 28 QVM rebuild knobs. `qvm_min_universe_size`
    # defaults to the §22.5 30-entry floor; operators with smaller
    # universes can drop it for testing, but the leaderboard surface
    # will surface it as a skipped/blocked row by default.
    qvm_min_universe_size: int = 30
    qvm_sector_neutral_zscore: bool = False
    qvm_soft_clip_composite: bool = False
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
