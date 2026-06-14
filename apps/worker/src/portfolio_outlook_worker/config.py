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
    # In-tick retry-with-backoff: when ``.tick()`` returns
    # ``mode="error"`` (the existing transient-failure shape) the
    # scheduler immediately re-attempts the sweep up to
    # ``sweep_retry_max_attempts`` times, sleeping
    # ``sweep_retry_backoff_seconds * 2**(attempt-1)`` between
    # attempts. With the defaults a transient IBKR hiccup is recovered
    # within one tick (~6s of waiting) instead of waiting a full
    # ``sweep_interval_seconds`` for the next scheduled fire.
    sweep_retry_max_attempts: int = 3
    sweep_retry_backoff_seconds: float = 2.0
    # GAPS.md P2-4 — Pass C ``awaiting_reply_timeout`` escalatie naar
    # manual-review. De doctrine-lock op 24u (Task 135) is nu de
    # default; operator kan dit verkorten (b.v. 4u) zodat stuck
    # drafts niet 24u in limbo blijven voordat ze de manual-review
    # queue raken. Range 1-72 uur; verder verandert het reconciler-
    # gedrag niet.
    reconciler_pass_c_timeout_hours: int = 24


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

    # AI morning explanation batch — fires after the daily morning
    # chain so Claude's Dutch paraphrase is ready for every held-
    # position Decision Package before the operator opens the
    # dashboard. Disabled by default; the API-side opt-in
    # (``ai_explanation_morning_batch_enabled``) is the second gate.
    # Default cron: 06:45 local time, ~15 min after the chain trigger
    # so Decision Packages have had time to land.
    morning_explanation_batch_trigger_enabled: bool = False
    morning_explanation_batch_cron: str = "45 6 * * *"

    # SELL-signal sweep trigger (POST /sell-signals/sweep) — V1.2 §BI.
    # CLAUDE.md §6.3 + §11 vraagt dat de SELL-monitoring blijft
    # draaien, OOK tijdens software-pauze. De sweep zelf bypasst de
    # pauze-flag bewust (`sell_signal_sweep.py:431`), maar tot deze
    # cron werd de sweep helemaal nooit automatisch getriggerd.
    # Default cron: elke 10 minuten tijdens kantoor-uren weekdagen
    # — globaal venster dat US + Euronext market-hours dekt. Operator
    # kan dit verfijnen via env-var of runtime-config.
    sell_signal_sweep_trigger_enabled: bool = False
    sell_signal_sweep_cron: str = "*/10 7-22 * * mon-fri"

    # Monthly report PDF auto-archive trigger — V1.2 §BN.
    # CLAUDE.md §13: "elke 1e van de maand wordt een PDF
    # gegenereerd en opgeslagen in /rapporten/archief". Tot deze cron
    # bestond geen scheduler die dit deed; operator moest manueel
    # ``POST /rapporten/archief/generate`` aanroepen voor elke
    # maand. Default cron: 1e van elke maand 00:15 local time —
    # vroeg genoeg dat de PDF beschikbaar is wanneer de operator 's
    # ochtends het dashboard opent.
    monthly_archive_auto_generate_enabled: bool = False
    monthly_archive_auto_generate_cron: str = "15 0 1 * *"

    # Macro feed refresh trigger — V1.2 §BT / GAPS.md P1-10.
    # CLAUDE.md §7.2 macro-regime gate vereist verse VIX + S&P 500
    # bars. Tot deze cron werd ``sync_macro_feed`` alleen handmatig
    # aangeroepen. Default cron: dagelijks 17:30 Europe/Brussels —
    # net na Euronext close, vóór 18:00 EU/US-overlap waar VIX nog
    # actief beweegt. Werkdag-only.
    macro_feed_refresh_enabled: bool = False
    macro_feed_refresh_cron: str = "30 17 * * mon-fri"

    # Market-aware scheduler (replaces the legacy ``hour="7-21"`` dumb
    # cadence). When ``per_market_close_digest_enabled`` is True the
    # worker registers one cron fire per active market (see
    # ``market_hours.resolve_active_market_sessions``), each producing
    # a market-close digest a few minutes after that market's close.
    # ``universe_scan_index_codes`` is the operator's selected list of
    # market index codes, overlaid from runtime_config at worker startup.
    per_market_close_digest_enabled: bool = True
    per_market_open_alerts_enabled: bool = False
    universe_scan_index_codes: str = ""


class NotificationSettings(BaseModel):
    """Operator email notification config + per-trigger preferences.

    Mirrors the API-side ``runtime_config`` columns (PR K). Overlaid at
    worker startup via ``apply_worker_runtime_config_overlay`` so the
    digest runner picks up the operator's saved values without an env
    change. ``real_client_enabled`` stays env-var-only — a fresh deploy
    is in stub mode regardless of saved SMTP credentials.
    """

    real_client_enabled: bool = False
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None
    smtp_to: str | None = None
    smtp_use_tls: bool = True
    email_enabled: bool = False
    send_on_nav_drop: bool = True
    send_on_position_drop: bool = True
    send_on_high_confidence_sell: bool = True
    # PR 2 — AI-composed email summary header. When ON the worker's
    # digest + morning-alerts runners POST the rendered template body
    # to ``/notifications/compose-summary`` and prepend Claude's Dutch
    # paraphrase to the email. Default OFF so a misconfigured Claude
    # provider can never block the operationally-critical digest mail.
    # The runners reuse ``SchedulerSettings.api_base_url`` /
    # ``api_request_timeout_seconds`` for the HTTP call — the worker
    # has one API host today, no need for a second.
    ai_email_summary_enabled: bool = False


class Settings(BaseSettings):
    service_name: str = "Portfolio Outlook Manager Worker"
    environment: str = "development"
    paper_only_mode: bool = True
    storage: StorageSettings = StorageSettings()
    ibkr: IbkrSettings = IbkrSettings()
    scheduler: SchedulerSettings = SchedulerSettings()
    eodhd: EodhdSettings = EodhdSettings()
    notifications: NotificationSettings = NotificationSettings()

    model_config = SettingsConfigDict(
        env_prefix="WORKER_",
        env_nested_delimiter="__",
        extra="ignore",
    )


settings = Settings()
