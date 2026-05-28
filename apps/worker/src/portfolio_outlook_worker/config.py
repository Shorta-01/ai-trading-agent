"""Configuration for the worker service.

Task 126 adds the IBKR connection surface (host/port/client/account
id) and the worker-wide ``ibkr_enabled`` master switch. The worker
is the only component that owns a long-lived TWS API session; the
API reads worker-persisted state via the storage layer rather than
making IBKR calls itself.
"""

from pydantic import BaseModel
from pydantic_settings import BaseSettings, SettingsConfigDict


class StorageSettings(BaseModel):
    """Storage configuration flags for future runtime wiring."""

    database_url: str | None = None
    enabled: bool = False
    writes_enabled: bool = False


class IbkrSettings(BaseModel):
    """Task 126 IBKR session configuration.

    Defaults preserve the Task 120 "disabled by default" lock — the
    worker does not open a TWS session until ``IBKR_ENABLED=true``.
    The default port matches paper-TWS (``7497``); the live-TWS port
    (``7496``) is settable. **The port is NOT a mode indicator** —
    the configured account ID's prefix + a behavioural check are the
    locked detection mechanism per Task 126 product lock §2.
    """

    enabled: bool = False
    host: str = "127.0.0.1"
    port: int = 7497
    client_id: int = 1
    account_id: str | None = None
    # Execution-layer activation (T-045 §1-3). Both default off: the order
    # sweeps only run when explicitly enabled AND a writable, paper-gated
    # order session has been opened. Turning these on is the deliberate
    # "go live on paper" switch. The order session uses its own client id so
    # it doesn't collide with the read-only sync session.
    submission_sweep_enabled: bool = False
    cancel_sweep_enabled: bool = False
    order_session_client_id: int = 2


class EodhdSettings(BaseModel):
    """Task 129 EODHD provider configuration.

    ``api_key=None`` is a valid configuration — the client returns
    :class:`EodhdNotConfiguredError` without touching the network.
    ``MARKET_DATA_FETCH_ENABLED`` keeps the orchestrator's
    market-data step inert until the operator opts in.
    """

    api_key: str | None = None
    base_url: str = "https://eodhd.com/api"
    rate_limit_per_second: int = 10
    fetch_enabled: bool = False


class SchedulerSettings(BaseModel):
    """Task 127 APScheduler configuration.

    Defaults preserve the Task 120 disabled-by-default lock — the
    worker process does not start any cron jobs until
    ``SCHEDULER_ENABLED=true``. Timezone is locked to Europe/Brussels
    per the §22.2 morning-chain doctrine.
    """

    enabled: bool = False
    timezone: str = "Europe/Brussels"
    heartbeat_interval_seconds: int = 60


class Settings(BaseSettings):
    service_name: str = "Portfolio Outlook Manager Worker"
    environment: str = "development"
    paper_only_mode: bool = True
    storage: StorageSettings = StorageSettings()
    ibkr: IbkrSettings = IbkrSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    eodhd: EodhdSettings = EodhdSettings()

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()
