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
    # Cadence for the submission + cancel sweeps. The earlier
    # implementation hard-coded 60s; surfacing it as config lets
    # operators slow the sweep down when an IBKR session is sluggish
    # and the per-cycle work isn't completing fast enough to keep the
    # next tick from queueing behind it.
    sweep_interval_seconds: int = 60
    # Persistent-failure alerting: a single sweep error is normal IBKR
    # noise; N consecutive error ticks should reach the operator. When
    # the count hits this threshold the worker writes a SystemEvent so
    # /systeemmeldingen surfaces the problem instead of it living
    # only in the log file. Reset on the next non-error tick.
    sweep_alert_after_consecutive_errors: int = 3


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

    # Worker-side triggers for jobs that previously lived in the API
    # process. They POST to existing API endpoints so the worker stays
    # the single source of cron truth while the API serves HTTP only —
    # multi-replica API deploys no longer race on `scheduler_runs`.
    api_base_url: str | None = None
    # Daily morning-chain trigger (POST /scheduler/runs/morning-chain).
    morning_chain_trigger_enabled: bool = False
    morning_chain_cron: str = "30 6 * * *"
    # When true, the morning chain is fired inline at the end of the
    # 06:00 pre-briefing run instead of via a separate cron. This is
    # the signal-chain delivery — no clock gap between pre-briefing
    # and morning chain, so a slow pre-briefing can't let the morning
    # chain run against stale state.
    morning_chain_after_pre_briefing: bool = False
    # IBKR read-only sync trigger (POST /ibkr/sync/run).
    ibkr_sync_trigger_enabled: bool = False
    ibkr_sync_interval_minutes: int = 15
    # HTTP timeout for the API-trigger calls. The morning chain can
    # legitimately take minutes; tune for the longest expected run.
    api_request_timeout_seconds: float = 300.0


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
