# Reality — API infrastructure and AI explanation cluster

**Scope.** This doc covers the non-IBKR / non-forecasting infrastructure of `apps/api`: the FastAPI app entry point, `pydantic-settings` configuration, the health probe, the status/settings/integration summary surface, the V1 daily-briefing scheduler + the Task-127 worker-scheduler read-only surface, the three system-event modules, the storage and online-storage status snapshots, the V1 / V1.1 release-readiness scorecard, the read-only request-audit surface, the portfolio-valuation readiness scorecard, and the Anthropic Claude AI explanation surface (provider, dispatcher, sync orchestrator, monthly EUR budget cap).

Sibling docs cover the rest of `apps/api`:

- `docs/reality/components/api-ibkr-connection-and-status.md`, `…-sync-and-snapshot.md`, `…-submission-and-watchlists.md` — IBKR cluster (T-004).
- `docs/reality/components/api-forecasting-and-market-data.md` and `…-actions-suggestions-and-watchlists.md` — forecast / market-data / actions / decision-package / watchlist / reconciliation cluster (T-005).

The worker AI surface (`apps/worker`) is out of scope and is covered by T-007.

Intent reference: `docs/ai-policy.md` (locked policy — the "AI is uitsluitend research- en uitleglaag" / "Python berekent, AI legt uit" doctrine).

## In-scope modules

All paths are under `apps/api/src/portfolio_outlook_api/`.

| Module | Lines | Role |
|---|---:|---|
| `main.py` | 131 | FastAPI app construction, lifespan, router includes, inline `/` + `/health` routes |
| `config.py` | 262 | `pydantic-settings` `Settings` + `StorageSettings` + `ResearchUploadSettings` + `ResearchExtractionSettings` |
| `health.py` | 13 | `HealthResponse` + `get_health_response()` |
| `status_models.py` | 110 | Pydantic models for the status / settings / AI usage / integrations / Dutch-labels surface |
| `status_builders.py` | 300 | Builder functions producing the placeholder envelopes for the status surface |
| `status_routes.py` | 4014 | The shared status APIRouter (mixed infrastructure + IBKR + forecast + actions routes — only the infra-flavoured routes are documented in detail here) |
| `scheduler.py` | 297 | APScheduler `BackgroundScheduler` factory + the V1 `daily_briefing` job + persistence helper |
| `scheduler_routes.py` | 190 | Task-127 worker-scheduler read-only surface (`/scheduler/v127/*`) |
| `system_event_recorder.py` | 154 | Single write path for system events |
| `system_event_reader.py` | 147 | Single read path for open system events |
| `system_event_mutations.py` | 153 | `resolve` / `archive` mutation surface |
| `storage_status.py` | 142 | Offline-only storage status synthesiser |
| `online_storage_status.py` | 105 | Live DB-probe storage status |
| `release_readiness.py` | 497 | V1 + V1.1 §22 readiness scorecard with 20 blocker codes |
| `request_audit.py` | 504 | Read-only audit router (`/audit/...`) over `request_logs` + `provider_sources` + `freshness_audits` |
| `portfolio_valuation_readiness.py` | 916 | Portfolio-valuation and reconciliation readiness builders |
| `anthropic_explanation_provider.py` | 280 | Anthropic Claude SDK-backed `ExplanationProvider` |
| `ai_explanation_provider.py` | 210 | `ExplanationProviderProtocol`, `StubExplanationProvider`, `build_explanation_provider` factory |
| `ai_explanation_sync.py` | 354 | `generate_explanation(...)` orchestrator + evidence-ledger writer |
| `claude_ai_budget.py` | 186 | Monthly EUR budget cap primitives (`assert_budget_available`, `compute_cost_eur`, `persist_call_cost`) |

Total in-scope: **8985 lines** across 20 modules (the per-module line counts above differ by 1–2 from the task spec because the agent re-counted).

## 1. FastAPI app construction (`main.py`)

### Imports + scheduler wiring

- `from portfolio_outlook_api.config import settings` (`main.py:22`).
- `from portfolio_outlook_api.scheduler import build_scheduler, install_default_jobs` (`main.py:44`).
- Storage primitives for the per-fire scheduler repo factory: `SqlAlchemySchedulerRunRepository`, `StorageConnectionError`, `StorageConnectionProvider`, `build_database_connection_settings` (`main.py:9-14`).
- Module logger: `logger = logging.getLogger(__name__)` (`main.py:54`).

### Scheduler-run repository factory

`_scheduler_repo_factory()` (`main.py:57-77`) returns a fresh `SqlAlchemySchedulerRunRepository` per scheduler fire, gated on `storage.enabled`, `storage.database_url`, and `storage.writes_enabled` (`main.py:66`). On `StorageConnectionError` it returns `None` (`main.py:76-77`) — the scheduler still runs but does not persist its run rows.

### Lifespan

The FastAPI app is constructed with a `@asynccontextmanager` lifespan (`main.py:80-97`):

1. `scheduler = build_scheduler(settings)` (`main.py:82`).
2. `install_default_jobs(scheduler, settings, repo_factory=_scheduler_repo_factory)` when the scheduler is not `None` (`main.py:84-88`).
3. `scheduler.start()` (`main.py:89-90`).
4. `app.state.scheduler = scheduler` (`main.py:91`).
5. On shutdown: `scheduler.shutdown(wait=False)` (`main.py:96-97`).

The app itself:

```python
app = FastAPI(title=settings.app_name, version=settings.version, lifespan=lifespan)
```

(`main.py:100`).

### Middleware / CORS / exception handlers

**None.** `main.py` does not call `app.add_middleware(...)`; there is no CORS configuration, no auth middleware, no global exception handler, and no `extra="forbid"` enforcement at the FastAPI app level. Forbidding extra fields is done per-Pydantic-model on the response side (e.g. `scheduler_routes.py:48, 61, 75`), not at the application boundary.

### Inline routes

`main.py` declares two routes itself rather than on a sub-router:

| Method | Path | Handler | File:line | Response model |
|---|---|---|---|---|
| GET | `/` | `read_root` | `main.py:103-108` | inline `{"name", "version"}` dict |
| GET | `/health` | `read_health` | `main.py:111-113` | `HealthResponse` |

### `include_router(...)` registrations

In declaration order:

| File:line | Router variable | Source module | Cluster owner |
|---|---|---|---|
| `main.py:116` | `status_router` | `status_routes` | mixed (infra + T-004 + T-005) |
| `main.py:117` | `research_sources_router` | `research_sources` | T-005 (research) |
| `main.py:118` | `asset_master_router` | `asset_master` | T-005 (asset master) |
| `main.py:119` | `asset_listings_router` | `asset_listings` | T-005 (asset listings) |
| `main.py:120` | `watchlist_router` | `watchlist` | T-005 (watchlist) |
| `main.py:121` | `request_audit_router` | `request_audit` | infrastructure (this doc) |
| `main.py:122` | `ibkr_connection_router` | `ibkr_connection_routes` | T-004 (IBKR) |
| `main.py:123` | `scheduler_v127_router` | `scheduler_routes` | infrastructure (this doc) |
| `main.py:124` | `watchlist_confirmation_router` | `watchlist_confirmation_routes` | T-005 (watchlist) |
| `main.py:125` | `market_data_runtime_router` | `market_data_runtime_routes` | T-005 (market-data) |
| `main.py:126` | `forecast_routes_router` | `forecast_routes` | T-005 (forecast) |
| `main.py:127` | `decision_package_routes_router` | `decision_package_routes` | T-005 (decision-package) |
| `main.py:128` | `action_draft_router` | `action_draft` | T-005 (actions) |
| `main.py:129` | `ibkr_submission_router` | `ibkr_submission` | T-004 (IBKR) |
| `main.py:130` | `reconciliation_router` | `reconciliation` | T-005 (reconciliation) |

Total: **15** `include_router(...)` calls. Verification: `grep -cE 'include_router' apps/api/src/portfolio_outlook_api/main.py` returns `15`.

## 2. Settings (`config.py`)

`Settings` is a single `BaseSettings` class (`config.py:78-258`) read once at import time as the module-level singleton `settings = Settings()` (`config.py:261`).

### Configuration of `Settings`

```python
model_config = SettingsConfigDict(
    env_prefix="API_",
    env_nested_delimiter="__",
    extra="ignore",
)
```

(`config.py:254-258`). Notably **`extra="ignore"`, not `"forbid"`** — unknown `API_*` env vars are silently dropped.

### Sub-classes (Pydantic v2 `BaseModel`)

#### `StorageSettings` (`config.py:9-14`)

- `database_url: str | None = None` (`config.py:12`)
- `enabled: bool = False` (`config.py:13`)
- `writes_enabled: bool = False` (`config.py:14`)

#### `ResearchUploadSettings` (`config.py:19-57`)

- `enabled: bool = False` (`config.py:22`)
- `archive_dir: str = "var/research-source-archive"` (`config.py:23`)
- `max_file_size_bytes: int = 20 * 1024 * 1024` (`config.py:24`)
- `allowed_extensions: tuple[str, ...]` — 7-tuple of doc/CSV/Office extensions (`config.py:25-33`)
- `allowed_content_types: tuple[str, ...]` — 7-tuple of MIME types (`config.py:34-42`)
- Validators: `_validate_archive_dir` non-empty after strip (`config.py:44-50`), `_validate_max_size > 0` (`config.py:52-57`).

#### `ResearchExtractionSettings` (`config.py:60-76`)

- `enabled: bool = False` (`config.py:63`)
- `extracted_text_archive_dir: str = "var/research-extracted-text"` (`config.py:64`)
- `max_input_file_size_bytes: int = 20 * 1024 * 1024` (`config.py:65`)
- `max_output_characters: int = 2_000_000` (`config.py:66`)
- `preview_max_characters: int = 1_000` (`config.py:67`)
- `allowed_extensions: tuple[str, ...] = (".txt", ".md", ".csv")` (`config.py:68`)
- Validator: `_validate_archive_dir` non-empty (`config.py:70-76`).

### `Settings` fields (top-level groups, with file:line anchors)

- **Identity / mode.** `app_name`, `version`, `environment`, `paper_only_mode=True`, `storage=StorageSettings()` (`config.py:81-85`).
- **IBKR connection / session.** Eight flags incl. `ibkr_enabled`, `ibkr_expected_environment="paper"`, `ibkr_tws_readonly_*` toggles, `ibkr_account_snapshot_preflight_enabled` (`config.py:86-95`).
- **IBKR market-data adapter.** Nine fields (`config.py:96-104`) — host/port/client_id/`readonly=True`/account_mode/market_data_type/provider_code/timeout.
- **IBKR sync.** Eleven fields incl. `ibkr_sync_enabled`, host/port/client_id/`readonly=True`, `ibkr_sync_account_summary_tags="TotalCashValue,AvailableFunds,BuyingPower,NetLiquidation,GrossPositionValue"` (`config.py:105-116`).
- **Market-data / FX / EODHD.** `market_data_provider="none"`, `eodhd_enabled=False`, `eodhd_api_key=None`, `eodhd_base_url`, `fx_provider="none"`, `fx_sync_enabled=False` (`config.py:117-125`).
- **Forecast.** `forecast_sync_enabled=False`, lookback/horizon/min-bars/max-assets/valid-minutes/pilot-conids (`config.py:126-136`).
- **Suggestions / decision-packages / action-drafts.** Eight flags incl. `action_drafts_default_buy_value="1000"`, `action_drafts_top_up_pct="0.25"`, `action_drafts_reduce_pct="0.25"` (`config.py:137-145`).
- **IBKR paper-order submission.** Eight fields incl. `ibkr_paper_order_submission_enabled=False`, `action_draft_approval_valid_minutes=5` (`config.py:146-153`).
- **Reconciliation / prediction diary.** `reconciliation_sync_enabled=False`, `prediction_diary_sync_enabled=False`, `prediction_diary_inconclusive_tolerance_pct="0.25"` (`config.py:154-156`).
- **AI explanation feature gates.** `ai_explanation_enabled=False`, `ai_explanation_real_client_enabled=False`, `ai_explanation_provider_code="stub"`, `ai_explanation_max_output_chars=2000` (`config.py:157-160`).
- **Daily briefing.** `daily_briefing_sync_enabled=False`, `daily_briefing_lookback_hours=24` (`config.py:161-162`).
- **Scheduler.** `scheduler_enabled=False`, `scheduler_timezone="Europe/Brussels"`, `scheduler_daily_briefing_cron="30 6 * * *"` (`config.py:163-165`).
- **Universe scan / AI TS predictor.** `universe_scan_sync_enabled=False`, `universe_scan_max_tickers_per_run=50`, `ai_ts_predictor_enabled=False`, `ai_ts_predictor_real_client_enabled=False`, `ai_ts_predictor_provider_code="stub"`, `ai_ts_predictor_daily_only=True`, `ai_ts_predictor_max_tokens=1024` (`config.py:166-177`).
- **Claude AI (V1.1 §22.2).** `claude_ai_budget_monthly_eur=Decimal("50")` (`config.py:182`), `claude_ai_explanation_model="claude-haiku-4-5-20251001"` (`config.py:187`), `claude_ai_api_key=None` (`config.py:188`), `claude_ai_explanation_max_output_chars=2000` (`config.py:189`).
- **Universe + V1.1 §22 rebuild knobs.** `universe_set="SP500"` (`config.py:193`), `universe_scan_cache_ttl_hours=24` (`config.py:198`), `predictor_backtest_enabled=False` (`config.py:202`), `ensemble_weight_strategy="equal_weight"` (`config.py:207`); GBM, momentum, mean-reversion, QVM toggles (`config.py:212-227`); `research_upload` + `research_extraction` (`config.py:228-231`).

### Validators

- `_normalize_expected_environment` — lowercases/strips `ibkr_expected_environment`, empty → `"paper"` (`config.py:233-237`).
- `_normalize_optional_string` (mode="before") — strips `ibkr_account_id_hint` + `ibkr_gateway_url`, empty → `None` (`config.py:239-245`).
- `_validate_timeout` — `ibkr_connection_timeout_seconds` ∈ `[1, 120]` (`config.py:247-252`).

## 3. Health (`health.py`)

`health.py` (13 lines) defines `HealthResponse(BaseModel)` (`health.py:6-8`) with `status: str` + `service: str`, and `get_health_response()` returning `HealthResponse(status="ok", service="api")` (`health.py:11-12`). The route itself (`GET /health`) is registered inline in `main.py:111-113`.

## 4. Status surface — models, builders, routes

### Pydantic models (`status_models.py`)

| Class | File:line | Built by |
|---|---|---|
| `ServiceStatusCard` | `status_models.py:9-17` | `build_system_status_summary` (list element) |
| `SystemStatusSummary` | `status_models.py:20-30` | `build_system_status_summary` (`status_builders.py:19`) |
| `SettingFieldHelp` | `status_models.py:33-35` | nested in `build_settings_summary` |
| `IbkrSettingsSection` | `status_models.py:38-44` | nested in `build_settings_summary` |
| `OpenAiSettingsSection` | `status_models.py:47-52` | nested in `build_settings_summary` |
| `AiBudgetSection` | `status_models.py:55-58` | nested in `build_settings_summary` |
| `SecretSafetySection` | `status_models.py:61-65` | nested in `build_settings_summary` |
| `SettingsSummary` | `status_models.py:68-74` | `build_settings_summary` (`status_builders.py:137`) |
| `AiUsageSummary` | `status_models.py:77-89` | `build_ai_usage_summary` (`status_builders.py:208`) |
| `IntegrationCard` | `status_models.py:92-99` | nested in `build_integrations_summary` |
| `IntegrationsSummary` | `status_models.py:102-105` | `build_integrations_summary` (`status_builders.py:227`) |
| `DutchLabelsSummary` | `status_models.py:108-109` | `build_dutch_labels_summary` (`status_builders.py:281`) |

The OpenAI / AI-usage models are a Phase 0 placeholder surface — they pre-date the Anthropic pivot. `AiUsageSummary.usage_available` is hard-coded to `False` and every token/cost field is `None` (`status_builders.py:208-224`); the budget status reported here does **not** read from the real `claude_ai_budget_usage` table.

### Builder functions (`status_builders.py`)

| Function | File:line | Purpose |
|---|---|---|
| `build_system_status_summary` | `status_builders.py:19-134` | Returns `SystemStatusSummary` with 11 hard-coded `ServiceStatusCard` rows (placeholder; not live status). |
| `build_settings_summary` | `status_builders.py:137-205` | Returns `SettingsSummary` placeholder with the four sub-sections; `SecretSafetySection` asserts no secrets returned/stored. |
| `build_ai_usage_summary` | `status_builders.py:208-224` | Returns `AiUsageSummary` with `usage_available=False`. |
| `build_integrations_summary` | `status_builders.py:227-278` | Returns `IntegrationsSummary` with 5 `IntegrationCard` rows (ibkr, openai, data_sources, scheduler, worker). |
| `build_dutch_labels_summary` | `status_builders.py:281-299` | Returns `DutchLabelsSummary` with 14 NL label key→value pairs. |

### Infrastructure-flavoured routes in `status_routes.py`

`status_routes.py` (4014 lines) is the shared `APIRouter` (`router = APIRouter()`, `status_routes.py:192`) and hosts a mix of infrastructure, IBKR (T-004), forecast / actions (T-005) routes. The infrastructure-flavoured routes:

| Method | Path | Handler | File:line | Response model |
|---|---|---|---|---|
| GET | `/system/status` | `read_system_status` | `status_routes.py:234-236` | `SystemStatusSummary` |
| GET | `/settings/summary` | `read_settings_summary` | `status_routes.py:239-241` | `SettingsSummary` |
| GET | `/settings/trading` | `read_trading_settings` | `status_routes.py:244-246` | `dict[str, object]` (no model) |
| PUT | `/settings/trading` | `update_trading_settings` | `status_routes.py:410-412` | `dict[str, object]` |
| GET | `/usage/ai/summary` | `read_ai_usage_summary` | `status_routes.py:249-251` | `AiUsageSummary` |
| GET | `/integrations/summary` | `read_integrations_summary` | `status_routes.py:254-256` | `IntegrationsSummary` |
| GET | `/ui/dutch-labels` | `read_dutch_labels` | `status_routes.py:259-261` | `DutchLabelsSummary` |
| GET | `/portfolio/setup/status` | `read_portfolio_setup_status` | `status_routes.py:343-345` | `dict[str, object]` |
| GET | `/portfolio/setup/defaults` | `read_portfolio_setup_defaults` | `status_routes.py:348-350` | `dict[str, object]` |
| POST | `/portfolio/setup/preview` | `preview_portfolio_setup` | `status_routes.py:353-364` | `dict[str, object]` (409/400) |
| GET | `/storage/status` | `read_storage_status` | `status_routes.py:367-369` | `StorageStatusResponse` |
| GET | `/storage/status/online` | `read_storage_status_online` | `status_routes.py:372-374` | `OnlineStorageStatusResponse` |
| GET | `/system/events/active` | `read_active_system_events` | `status_routes.py:377-379` | `ActiveSystemEventsResponse` |
| POST | `/system/events/{system_event_id}/resolve` | `resolve_system_event` | `status_routes.py:382-393` | `dict[str, object]` (404/409) |
| POST | `/system/events/{system_event_id}/archive` | `archive_system_event` | `status_routes.py:396-407` | `dict[str, object]` (404/409) |
| GET | `/scheduler/jobs` | `read_scheduler_jobs` | `status_routes.py:2978-3012` | `dict[str, object]` |
| GET | `/scheduler/runs/latest` | `read_latest_scheduler_run` | `status_routes.py:3015-3064` | `dict[str, object]` (optional `job_name`) |
| POST | `/scheduler/runs/morning-chain` | `run_morning_chain_manually` | `status_routes.py:3067-3205` | `dict[str, object]`; writes `SchedulerRunRecord(triggered_by="manual")`; gated on `scheduler_enabled` + writable storage |
| GET | `/ibkr/account/mode` | `read_ibkr_account_mode` | `status_routes.py:3208-3233` | `dict[str, object]`; reports paper/live mode from `ibkr_sync_account_mode` |
| GET | `/v1/release-readiness` | `read_v1_release_readiness` | `status_routes.py:3236-3278` | `dict[str, object]`; reads `SqlAlchemyClaudeAiBudgetUsageRepository` when storage reachable |
| GET | `/claude/budget/status` | `read_claude_budget_status` | `status_routes.py:3529-3589` | `dict[str, object]`; returns monthly cap + total + remaining vs. `claude_ai_budget_monthly_eur` |

Shared helper: `_build_sync_run_diagnostics` (`status_routes.py:195-231`) builds the cross-cluster sync-run diagnostics envelope used by `/ibkr/sync/runs*` (T-004) and by the morning-chain runner here.

### Other clusters' routes (counts only)

- **T-004 IBKR cluster.** 20 routes under `/ibkr/...` and `/broker/ibkr/...`, e.g. `/ibkr/session/status`, `/ibkr/sync/run`, `/ibkr/orders/open`, `/ibkr/watchlists/{watchlist_id}/import`, `/ibkr/contracts/{conid}/details` (see `docs/reality/components/api-ibkr-*.md`).
- **T-005 forecast / actions cluster.** 30 routes incl. `/portfolio/valuation/readiness`, `/market-data/readiness`, `/forecasts/compute`, `/suggestions/compute`, `/decision-packages/compute`, `/action-drafts/compute`, `/prediction-diary/evaluate`, `/briefings/daily/compute`, `/predictor/backtest/run`, `/universe/scan/run` (see `docs/reality/components/api-forecasting-and-market-data.md` and `…-actions-suggestions-and-watchlists.md`).

## 5. Scheduler

### V1 daily-briefing scheduler (`scheduler.py`)

`scheduler.py` (297 lines) hosts an APScheduler `BackgroundScheduler` started inside the `main.py` lifespan. Key surface:

- Constants: `DAILY_BRIEFING_JOB_NAME = "daily_briefing"` (`scheduler.py:33`); status values `STATUS_RUNNING`, `STATUS_SUCCEEDED`, `STATUS_FAILED`, `STATUS_SKIPPED` (`scheduler.py:35-38`).
- `_SchedulerRunRepoProtocol` (`scheduler.py:41-48`) — write surface (`save_scheduler_run`, `update_scheduler_run`).
- `JobInfo` frozen dataclass (`scheduler.py:51-56`) — `job_id`, `job_name`, `next_run_at`, `cron_expression`.
- `_parse_cron(expression, timezone)` (`scheduler.py:59-75`) — 5-field cron; raises `ValueError` on malformed input.
- `_record_job_run(...)` (`scheduler.py:78-104`) — best-effort persistence (logged on exception).
- `run_daily_briefing_job(*, job_callable, repo_or_none, triggered_by="scheduler") -> SchedulerRunRecord` (`scheduler.py:107-170`) — writes initial `STATUS_RUNNING`, then `STATUS_SUCCEEDED` / `STATUS_FAILED` with `error_text`.
- `_build_default_morning_chain_callable(runtime_settings)` (`scheduler.py:186-201`) — lazy-imports `portfolio_outlook_api.morning_chain` and returns the bound callable.
- `build_scheduler(runtime_settings) -> BackgroundScheduler | None` (`scheduler.py:204-218`) — returns `None` when `scheduler_enabled=False`; otherwise `BackgroundScheduler(timezone=scheduler_timezone)`.
- `install_default_jobs(scheduler, runtime_settings, *, job_callable=None, repo_factory=None)` (`scheduler.py:221-263`) — registers one job (id+name = `DAILY_BRIEFING_JOB_NAME`) on the configured cron, in the configured timezone. The fire wrapper `_fire()` (`scheduler.py:249-255`) fetches a fresh repo per fire and routes through `run_daily_briefing_job(..., triggered_by="scheduler")`.
- `list_jobs(scheduler) -> tuple[JobInfo, ...]` (`scheduler.py:266-282`) — read surface used by `/scheduler/jobs`.

**Registered jobs:** exactly one — `daily_briefing`, cron from `scheduler_daily_briefing_cron` (default `"30 6 * * *"`, `config.py:165`), timezone from `scheduler_timezone` (default `"Europe/Brussels"`, `config.py:164`).

**Error handler:** no APScheduler event listener is registered. Per-fire errors are caught inside `run_daily_briefing_job` and surfaced as `STATUS_FAILED` `SchedulerRunRecord` rows (`scheduler.py:133-152`). Persistence failures are caught and logged but never raised (`scheduler.py:101-103, 147-151, 166-169`).

**`system_event_recorder` integration:** **none.** Searching `scheduler.py` for `system_event` returns no matches. The scheduler writes `SchedulerRunRecord` rows only; it never records a system event.

### Task-127 worker-scheduler read-only surface (`scheduler_routes.py`)

`scheduler_routes.py` (190 lines) is a **read-only window onto the Task-127 worker-scheduler** (which lives in a separate runtime — `apps/worker`). The `v127` URL prefix is mandatory because the V1 scheduler already owns `/scheduler/...` via `status_routes.py` (`scheduler_routes.py:9-14`).

Response models (all `model_config = ConfigDict(extra="forbid")`):

- `SchedulerV127StatusResponse` (`scheduler_routes.py:47-57`) — `enabled`, `last_run_at`, `last_run_type`, `last_mode_detected`, `last_outcome`, `next_runs`, `safe_for_action_drafts: Literal[False]`, `safe_for_orders: Literal[False]`.
- `ScheduledRunAuditRow` (`scheduler_routes.py:60-72`) — nine fields including `run_id`, `run_at`, `mode_detected`, `duration_ms`, `outcome`, `error_details_json`.
- `SchedulerV127RunsResponse` (`scheduler_routes.py:74-79`) — list + the same two `Literal[False]` safety flags.

Routes:

| Method | Path | Handler | File:line | Response model |
|---|---|---|---|---|
| GET | `/scheduler/v127/status` | `read_scheduler_v127_status` | `scheduler_routes.py:108-164` | `SchedulerV127StatusResponse` |
| GET | `/scheduler/v127/runs?limit=20` (1..200) | `read_scheduler_v127_runs` | `scheduler_routes.py:167-189` | `SchedulerV127RunsResponse` |

Behaviour:

- `/status` returns `enabled=False` with empty fields when storage is disabled / unconfigured (no 503, `scheduler_routes.py:116-127`). When storage is reachable, opens `StorageConnectionProvider.checked_connection(require_writable=False)` (`scheduler_routes.py:133`), reads `SqlAlchemyScheduledRunAuditRepository.list_recent(limit=1)` + `SqlAlchemySchedulerStateRepository.list_all()` (`scheduler_routes.py:134-141`), aggregates the next-run timestamps from the state rows (`scheduler_routes.py:147-153`). On `StorageConnectionError` → 503 (`scheduler_routes.py:142-143`).
- `/runs` is stricter — storage off → 503 immediately (`scheduler_routes.py:171-173`).
- **No auth gating.** Neither route declares any `Depends(...)`.

## 6. System events — recorder, reader, mutations

All three modules share the SQLAlchemy `SqlAlchemySystemEventRepository` (from `ai_trading_agent_storage`) over a single per-call `StorageConnectionProvider.checked_connection` context manager. There is no in-process ring buffer and no in-process hash chain — the chain (if any) lives downstream in the storage package.

### `system_event_recorder.py`

Public surface:

- `ApiSystemEventInput` frozen dataclass (`system_event_recorder.py:23-39`) — severity, category, `source_component`, `event_code`, Dutch title/message/help, optional `technical_summary`, pre-redacted details + stack-trace, related-entity tuple, three `blocks_*` gates.
- `ApiSystemEventRecordingResult` frozen dataclass (`system_event_recorder.py:42-49`) — `attempted`, `recorded`, `blocked`, `system_event_id`, `status_nl`, `message_nl`.
- DI type aliases `ConnectionProviderFactory`, `RepositoryFactory`, `DateTimeProvider`, `IdProvider` (`system_event_recorder.py:52-58`).
- `record_api_system_event(...)` (`system_event_recorder.py:61-154`) — single write entry point. Defaults: `now_provider = datetime.now(UTC)`, `id_provider = f"system-event-{uuid4()}"` (`system_event_recorder.py:66-67`). Hard-codes `source_service="api"` and `status="open"` (`system_event_recorder.py:111, 125`). Caller must pre-redact details (`system_event_recorder.py:69-72`).

Storage path: writes via `SqlAlchemySystemEventRepository.create_event(CreateSystemEventRequest(...))` (`system_event_recorder.py:105-128`) inside a `checked_connection(require_writable=True)` (`system_event_recorder.py:103`).

Blocked branches (all return Dutch `status_nl`/`message_nl`):

- `storage_settings.enabled = False` (`system_event_recorder.py:78-86`).
- Missing/empty `database_url` (`system_event_recorder.py:88-97`).
- `StorageConnectionNotReadyError` ("Writes zijn geblokkeerd door migratie-readiness.") (`system_event_recorder.py:137-145`).
- `StorageConnectionError` ("Databaseverbinding mislukt.") (`system_event_recorder.py:146-154`).

### `system_event_reader.py`

Public surface:

- `ActiveSystemEventSummary` frozen Pydantic (`system_event_reader.py:20-36`) — flat projection of an open event.
- `ActiveSystemEventsResponse` frozen Pydantic (`system_event_reader.py:39-48`) — `available`, `storage_configured`, `events_loaded`, `active_count`, NL strings, list of summaries.
- `_map_event_summary(record)` (`system_event_reader.py:58-74`).
- `list_active_system_events(...)` (`system_event_reader.py:77-147`) — read-only listing.

Storage path: `SqlAlchemySystemEventRepository.list_open_events().records` inside `checked_connection(require_writable=False)` (`system_event_reader.py:113-115`).

Blocked branches mirror the recorder: storage disabled (`system_event_reader.py:87-96`), missing URL (`:99-108`), `StorageConnectionError` (`:138-147`). Empty list returns `available=True, active_count=0` with "Geen actieve systeemmeldingen." (`:118-127`).

### `system_event_mutations.py`

Public surface:

- `SystemEventMutationInput` frozen Pydantic (`system_event_mutations.py:21-23`) — single field `reason_nl`.
- `SystemEventMutationResult` frozen dataclass (`system_event_mutations.py:26-30`) — `response`, `blocked`, `not_found`.
- Public mutations:
  - `mark_system_event_resolved(...)` (`system_event_mutations.py:40-54`) → `_mutate_system_event_status(mutation='resolve')` → `repository.mark_resolved(...)` (`system_event_mutations.py:114-116`).
  - `mark_system_event_archived(...)` (`system_event_mutations.py:57-71`) → `_mutate_system_event_status(mutation='archive')` → `repository.mark_archived(...)` (`system_event_mutations.py:117-119`).
- `_mutate_system_event_status(...)` (`system_event_mutations.py:74-153`) — shared engine over `checked_connection(require_writable=True)` (`:112`).

**Allowed mutations:** only `resolve` and `archive`. No create, no delete, no in-place edit. Both take a free-text `reason_nl` audit field. Create-only is the recorder's job.

Blocked branches (all return Dutch text, `blocked=True`, `updated=False`):

- Storage disabled (`system_event_mutations.py:88-96`).
- Missing URL (`:98-107`).
- `StorageConnectionNotReadyError` (`:136-144`).
- `StorageConnectionError` (`:145-153`).
- Not-found returns `blocked=False, not_found=True, status_nl='Niet gevonden'` (`:121-130`).

The three modules are stateless and reentrant; the only shared state is the `system_events` table row.

## 7. Storage status — offline and online

### `storage_status.py` — offline-only snapshot

The module **does not open a DB connection**. It synthesises a fixed "not connected, writes blocked" report from the offline migration inventory in `ai_trading_agent_storage`.

Pydantic models:

- `StorageBackendStatusCard` (`storage_status.py:10-13`) — `label_nl`, `status_nl`, `mode`.
- `StorageBackupStatus` (`storage_status.py:16-20`) — `status`, `encrypted_required`, `restore_test_required`, `restore_tested`.
- `StorageMigrationReadinessStatus` (`storage_status.py:23-35`) — 12 fields incl. `safe_to_write`, `persistence_allowed`, `blocks_runtime_writes`.
- `StorageStatusResponse` (`storage_status.py:38-56`) — title/help, planned-DB strings, four `storage_ready`/`can_persist_*` booleans, `persistence_mode`, `block_reasons`, `warning_reasons`, nested `migration_readiness`, list of backends, backup.

Functions:

- `_migration_status_nl(status)` (`storage_status.py:59-62`) — maps `NOT_CONNECTED` → Dutch label; everything else → "Onbekende migratiestatus".
- `build_storage_status() -> StorageStatusResponse` (`storage_status.py:65-142`) — Hard-codes `persistence_mode="blocked_not_connected"` (`:88`), `storage_ready=False`, all `can_persist_*=False` (`:84-87`). Block reasons enumerated: `database_not_connected`, `migration_readiness_not_checked_online`, `runtime_writes_blocked`, `audit_storage_missing` (`:90-95`). Warnings: `offline_inventory_only`, `backup_not_tested` (`:96`). Listed backends: PostgreSQL (`blocked`), TimescaleDB (`not_configured`), Auditlog (`blocked`), Research archief (`not_configured`), Raw data archief (`not_configured`) (`:113-135`). Backup: `status="not_configured"`, `encrypted_required=True`, `restore_test_required=True`, `restore_tested=False` (`:136-141`).

### `online_storage_status.py` — live DB probe

Pydantic model `OnlineStorageStatusResponse` (`online_storage_status.py:20-27`) — `configured`, `connected`, `safe_to_write`, NL strings, `migration_readiness_status`, `writes_status_nl`.

Functions:

- `_status_nl(readiness)` (`online_storage_status.py:33-36`) — `MIGRATIONS_CURRENT` → "Migraties klaar", else "Migraties niet klaar".
- `build_online_storage_status(storage_settings, engine_factory=None) -> OnlineStorageStatusResponse` (`online_storage_status.py:39-105`) — actually creates an engine (default factory at `:67`), connects (`:72-74`), and calls `check_online_migration_readiness(connection)`. `safe_to_write` is derived via `migration_readiness_is_safe_to_write(readiness)` (`:92`). Engine + connection are disposed in `finally` (`:86-90`). Error paths (disabled / no URL / `SQLAlchemyError` / `ValueError`) all return `configured=False`-or-`connected=False` with "Writes geblokkeerd" (`:43-85`).

**Difference:** `storage_status.py` is fully offline (always "not connected"); `online_storage_status.py` actually probes the live DB.

## 8. Release readiness scorecard (`release_readiness.py`)

The V1 + V1.1 scorecard. Hard contract from the module docstring (`release_readiness.py:8-11`): the scorecard **never authorises an order** — `serialize_release_readiness(...)` hard-codes `safe_for_action_drafts=False`, `safe_for_orders=False`, `blocks_orders=True` on the JSON envelope (`release_readiness.py:464-466`).

### Blocker codes (`Final[str]` module constants)

V1 (`release_readiness.py:33-47`):

| Code | File:line constant | Raised in |
|---|---|---|
| `BLOCKER_STORAGE_NOT_CONFIGURED` | `:33` | `_storage_checks` when `enabled and database_url` falsy (`:113-121`) |
| `BLOCKER_STORAGE_NOT_WRITABLE` | `:34` | `_storage_checks` when `writes_enabled=False` (`:122-130`) |
| `BLOCKER_EODHD_NOT_CONFIGURED` | `:35` | `_eodhd_checks` when `eodhd_enabled=False` (`:136-144`) |
| `BLOCKER_EODHD_API_KEY_MISSING` | `:36` | `_eodhd_checks` when `eodhd_api_key` falsy (`:145-153`) |
| `BLOCKER_IBKR_NOT_ENABLED` | `:37` | `_ibkr_checks` when `ibkr_enabled=False` (`:159-167`) |
| `BLOCKER_IBKR_SYNC_NOT_ENABLED` | `:38` | `_ibkr_checks` when `ibkr_sync_enabled=False` (`:168-176`) |
| `BLOCKER_SCHEDULER_DISABLED` | `:39` | `_scheduler_checks` when `scheduler_enabled=False` (`:181-189`) |
| `BLOCKER_MARKET_DATA_SYNC_DISABLED` | `:40` | morning-chain leg 1 (`:194`) |
| `BLOCKER_FORECAST_SYNC_DISABLED` | `:41` | morning-chain leg 2 (`:195`) |
| `BLOCKER_SUGGESTIONS_SYNC_DISABLED` | `:42` | morning-chain leg 3 (`:196`) |
| `BLOCKER_DECISION_PACKAGES_SYNC_DISABLED` | `:43` | morning-chain leg 4 (`:197-201`) |
| `BLOCKER_ACTION_DRAFTS_SYNC_DISABLED` | `:44` | morning-chain leg 5 (`:202-206`) |
| `BLOCKER_DAILY_BRIEFING_SYNC_DISABLED` | `:45` | morning-chain leg 6 (`:207-211`) |
| `BLOCKER_RECONCILIATION_SYNC_DISABLED` | `:46` | audit leg 1 (`:215-219`) |
| `BLOCKER_PREDICTION_DIARY_SYNC_DISABLED` | `:47` | audit leg 2 (`:220-224`) |

V1.1 Slice 34 (`release_readiness.py:50-56`):

| Code | File:line constant | Raised in |
|---|---|---|
| `BLOCKER_ENSEMBLE_WEIGHT_STRATEGY_INVALID` | `:50` | `_v1_1_checks` strategy not in `_LOCKED_ENSEMBLE_WEIGHT_STRATEGIES` (`:276-289`) |
| `BLOCKER_PREDICTOR_BACKTEST_DISABLED` | `:51` | `_v1_1_checks` when `predictor_backtest_enabled=False` (`:291-307`) |
| `BLOCKER_CLAUDE_AI_API_KEY_MISSING_WHEN_REAL_CLIENT_ENABLED` | `:52-54` | `_v1_1_checks` when real-client toggle on + key missing (`:309-329`) |
| `BLOCKER_CLAUDE_AI_BUDGET_EXCEEDED` | `:55` | `_v1_1_checks` via live `monthly_budget_status(repo, cap)` (`:362-375`) |
| `BLOCKER_UNIVERSE_SET_UNKNOWN` | `:56` | `_v1_1_checks` when `universe_set` not in `_LOCKED_UNIVERSE_SETS` (`:331-346`) |

Total: **20 blocker codes** (15 V1 + 5 V1.1).

### Locked enumerations / thresholds

- `_LOCKED_ENSEMBLE_WEIGHT_STRATEGIES = frozenset({"equal_weight", "auto"})` (`release_readiness.py:59-61`).
- `_LOCKED_UNIVERSE_SETS = frozenset({"SP500", "EU600", "ALL_5K"})` (`release_readiness.py:62-64`).
- Default Claude monthly cap: `Decimal("50")` EUR via `getattr(runtime_settings, "claude_ai_budget_monthly_eur", Decimal("50"))` (`release_readiness.py:352-354`).
- Status strings: `STATUS_READY = "ready"`, `STATUS_BLOCKED = "blocked"` (`release_readiness.py:67-68`).
- Cron pin reference in detail text: `"30 6 * * *"` Europe/Brussels (`release_readiness.py:186`).

### Data model

- `_BudgetRepoProtocol` (`release_readiness.py:71-82`) — `monthly_total_eur(budget_month: str) -> Decimal`, `save_usage(record) -> object`.
- `ReadinessCheck` frozen dataclass (`release_readiness.py:85-92`) — `code`, `passed`, `detail_nl`.
- `ReleaseReadinessReport` frozen dataclass (`release_readiness.py:94-102`) — `status`, `summary_nl`, `help_nl`, `blockers: tuple[str, ...]`, `checks: tuple[ReadinessCheck, ...]`.

### Aggregator

`compute_release_readiness(runtime_settings, *, budget_repo=None) -> ReleaseReadinessReport` (`release_readiness.py:378-443`) chains the seven check-generator functions (`_storage_checks`, `_eodhd_checks`, `_ibkr_checks`, `_scheduler_checks`, `_morning_chain_checks`, `_audit_checks`, `_v1_1_checks`), computes `blockers = tuple(c.code for c in checks if not c.passed)` (`:417`), and stamps the Dutch summary/help. When `budget_repo is None` the budget check is skipped (`:348-351`) — backward-compatible.

`serialize_release_readiness(report) -> dict[str, object]` (`release_readiness.py:446-467`) hard-codes the order-safety floor: `safe_for_action_drafts=False`, `safe_for_orders=False`, `blocks_orders=True` (`:464-466`).

## 9. Request audit (`request_audit.py`)

`request_audit.py` (504 lines) is a **router** (`router = APIRouter(prefix="/audit", tags=["audit"])`, `request_audit.py:21`), not middleware. It is registered in `main.py:121`. The router writes **nothing**; it exposes six read-only GET endpoints over three storage tables (`request_logs`, `provider_sources`, `freshness_audits`) via `SqlAlchemyRequestAuditRepository` over `checked_connection(require_writable=False)` (`request_audit.py:181`).

### Pydantic response models

- `RequestLogResponse` (`request_audit.py:29-59`) — 27 fields, all defaulting `safe_for_analysis = safe_for_suggestions = safe_for_action_drafts = False` (`:51-53`).
- `ProviderSourceResponse` (`request_audit.py:62-84`) — same three `False` defaults (`:76-78`).
- `FreshnessAuditResponse` (`request_audit.py:87-108`) — same three `False` defaults (`:100-102`).
- `RequestLogListResponse` / `ProviderSourceListResponse` / `FreshnessAuditListResponse` (`request_audit.py:111-167`) — list + summary buckets.

### Routes

| Method | Path | Handler | File:line |
|---|---|---|---|
| GET | `/audit/request-logs` | `list_request_logs` | `request_audit.py:424-441` |
| GET | `/audit/request-logs/{request_log_id}` | `get_request_log` | `request_audit.py:444-449` |
| GET | `/audit/provider-sources` | `list_provider_sources` | `request_audit.py:452-468` |
| GET | `/audit/provider-sources/{provider_source_id}` | `get_provider_source` | `request_audit.py:471-476` |
| GET | `/audit/freshness-audits` | `list_freshness_audits` | `request_audit.py:479-496` |
| GET | `/audit/freshness-audits/{freshness_audit_id}` | `get_freshness_audit` | `request_audit.py:499-504` |

All routes raise HTTP 503 on storage-disabled / unreachable via `_with_repository` (`request_audit.py:170-186`), and 404 on not-found.

**Hash-chain note:** the file talks about a "chain" but it refers to *foreign-key linkage* between rows (`request_log_id` ↔ `freshness_audit` ↔ `provider_source_id`) — `_request_chain_fields` (`:328-331`) always tags request-log rows as `missing_links` against `freshness_audit`; `_freshness_chain_fields` (`:334-341`) checks whether `request_log_id` and `provider_source_id` are linked. **No cryptographic hash chain** is computed in this module.

**PII redaction:** **none** in this module. Records are passed through verbatim via `RequestLogResponse(**record.__dict__, ...)` (`:364-372`). Any redaction would have to live upstream.

`BOUNDARY_HELP_NL` constant (`request_audit.py:23-26`) is a fixed Dutch read-only boundary statement attached to every response.

## 10. Portfolio valuation readiness (`portfolio_valuation_readiness.py`)

The largest module in scope (916 lines). Builds two scorecard responses — `PortfolioValuationReadinessResponse` and `PortfolioReconciliationReadinessResponse` — that downstream T-005 routes (`/portfolio/valuation/readiness`, `/portfolio/valuation/reconciliation-readiness`) return.

### Status enum + scorecard models

- `PortfolioValuationStatus` `StrEnum` (`portfolio_valuation_readiness.py:29-34`) — five states: `storage_unavailable`, `no_latest_ibkr_snapshot`, `no_positions`, `missing_market_data`, `calculation_available`.
- `PositionValuationReadinessRow` Pydantic (`portfolio_valuation_readiness.py:37-75`) — 39 fields per position; **all numeric fields are `str | None`** (Decimal-as-string boundary, see §10b below).
- `PortfolioValuationReadinessResponse` Pydantic (`portfolio_valuation_readiness.py:78-141`) — ~60 fields with hard-coded order-safety floor `suggestions_allowed=False`, `action_drafts_allowed=False`, `orders_allowed=False` (`:91-93`); embedded cash / FX / totals sub-blocks.
- `PortfolioReconciliationReadinessResponse` Pydantic (`portfolio_valuation_readiness.py:144-185`) — eleven boolean availability flags + `blocker_categories: list[str]`; hard-codes six `*_allowed=False` and `blocks_orders=True` (`:176-185`).
- `PositionRowBuildInput` frozen dataclass (`portfolio_valuation_readiness.py:188-192`).

### Builders

- `build_position_row(payload)` (`portfolio_valuation_readiness.py:212-377`) — starts blocked with `reason_code="missing_market_data"`; with a fresh snapshot computes `market_value = quantity * snapshot.last_price` (`:297-298`) and re-runs `calculate_position_cost_basis_and_unrealized_pl` with the live price; stale prices emit `reason_code="stale_market_data"`, "Controle nodig" (`:288-296`).
- `_build_conversion_inputs(...)` (`portfolio_valuation_readiness.py:391-468`) — assembles `PositionConversionInput`, `CashConversionInput`, `FxPairConversionInput`, `ConversionTotalsInput`, plus a `ValuationInputTrace`.
- `build_portfolio_valuation_readiness(...)` (`portfolio_valuation_readiness.py:471-799`) — cascades through the five `PortfolioValuationStatus` states.
- `build_portfolio_reconciliation_readiness(...)` (`portfolio_valuation_readiness.py:802-916`) — derives a reconciliation envelope; appends blockers and stamps the appropriate Dutch status/help.

### Blocker / reason codes emitted

Top-level reasons: `storage_unavailable`, `no_latest_ibkr_snapshot`, `no_positions`, `missing_market_data`, `calculation_available`.

Reconciliation `blockers` list (`portfolio_valuation_readiness.py:810-839`): `storage_unavailable`, `no_latest_ibkr_snapshot`, `no_positions_snapshot`, `no_cash_snapshot`, `missing_market_data`, `stale_market_data`, `missing_fx`, `stale_fx`, `invalid_fx`, `missing_cost_basis`, `sync_diagnostics_unavailable`, `payload_validation_failed`, `payload_validation_not_available`.

### 10b. Decimal-as-string boundary

`_money(value: Decimal) -> str: return str(value)` (`portfolio_valuation_readiness.py:195-196`) is the single boundary helper. Every numeric field exposed by the response is declared `str | None`: `quantity: str`, `average_cost`, `market_price`, `market_value`, `unrealized_pnl`, `cost_basis`, `unrealized_pl`, `unrealized_pl_percent`, `converted_unrealized_pl` (`portfolio_valuation_readiness.py:43-69`), plus the totals `total_market_value`, `total_cash_value`, `total_portfolio_value` (`:135-137`, stamped at `:780-794`). The only place a `Decimal` is reconstituted is inside `_build_conversion_inputs` (`Decimal(row.market_value) if row.market_value is not None else None`, `:411`) — the conversion engine takes Decimals, but the row carries strings; the boundary is crossed exactly once, inside the readiness module itself, immediately before `calculate_conversion_totals` (`:709`).

This matches the project-wide doctrine documented in the domain reality docs (`docs/reality/components/domain-primitives-and-money.md`) — no floats in money.

## 11. AI explanation surface (Anthropic Claude)

The AI explanation cluster covers four modules. The locked intent is in `docs/ai-policy.md` — most importantly: **"AI is uitsluitend research- en uitleglaag."** (`docs/ai-policy.md:4`) and **"Python berekent, AI legt uit."** (`docs/ai-policy.md:7`). Together with `ai-policy.md:13` ("AI mag geen financiële kerncijfers voor beslissingen verzinnen.") and `:14` ("AI mag risicoregels niet overrulen.") these lock the cluster into **Case C — LLM-as-explanation-layer** in the doctrine framework.

### 11a. AI scope classification

**Case C.** Evidence:

- `ai_explanation_provider.py:1-2`: "boundary … between the deterministic Decision Package evidence chain and an AI model that produces a natural-language Dutch explanation."
- `ai_explanation_provider.py:14-15`: stub "does not invent numbers; it only echoes what the package already contains and appends the locked risk disclaimer."
- `ai_explanation_sync.py:19-22`: "Hard contract: this module never originates a financial number; it only paraphrases what the persisted Decision Package + research evidence already contain."
- `anthropic_explanation_provider.py:19-21`: "Hallucinated-number guard — the response goes through the same Slice-10 validation pass (`validate_explanation_output`); any number not in the source Decision Package fails the call."
- `anthropic_explanation_provider.py:55-62`: locked Dutch system prompt demands paraphrase, no new numbers, no advice, no directional opinion, always append the risk disclaimer.
- `ai_explanation_sync.py:344-346`: response serializer hard-codes `safe_for_self_learning=False`, `safe_for_action_drafts=False`, `safe_for_orders=False`.

Contrast with `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py` (T-005 doc) which is **Case B (LLM-as-forecaster)** — that one is doctrine-locked to "remove from ensemble". The explanation surface here is the only sanctioned LLM call site.

### 11b. `ai_explanation_provider.py` — protocol, stub, factory

- `ExplanationProviderProtocol` (`ai_explanation_provider.py:64-67`) — single method `generate(self, inputs: ExplanationProviderInputs) -> ExplanationProviderResult`.
- `ExplanationProviderInputs` frozen dataclass (`ai_explanation_provider.py:36-53`) — `decision_package_id`, `decision_package_content_hash`, `symbol`, `risk_profile`, `rationale_nl`, `package_explanation_nl`, `research_snippet_nl`, `input_text`. Doctrine comment (`:43-44`): "Providers must not pull additional data from the network — everything the model sees is in this struct."
- `ExplanationProviderResult` frozen dataclass (`ai_explanation_provider.py:56-61`) — `output_text`, `model_provider_code`, `model_name`, `model_version`.
- `StubExplanationProvider` (`ai_explanation_provider.py:70-108`) — deterministic paraphrase. Constants: `STUB_PROVIDER_CODE="stub"`, `STUB_MODEL_NAME="deterministic_paraphrase"`, `STUB_MODEL_VERSION="v1"` (`:31-33`). Output concatenates symbol + risk_profile + package explanation + rationale + research snippet + `LOCKED_RISK_DISCLAIMER_NL` (`:93-102`). Per docstring (`:72-77`): "every numeric token in the output already appeared in the input, the locked risk disclaimer is always appended, and the output is fully reproducible".
- `ExplanationProviderUnavailable` frozen dataclass (`ai_explanation_provider.py:111-114`) — sentinel with `reason` + `detail_nl`.

#### Factory `build_explanation_provider` (`ai_explanation_provider.py:117-197`)

Gates, in order:

1. **Gate A — global enable**: `runtime_settings.ai_explanation_enabled=False` → `Unavailable(reason="ai_explanation_disabled", ...)` (`:139-146`).
2. **Gate B — stub provider code**: `provider_code == STUB_PROVIDER_CODE` → return `StubExplanationProvider()` directly (`:147-149`). No further gates.
3. **Gate C — real client switch**: `ai_explanation_real_client_enabled=False` → `Unavailable(reason="real_client_not_enabled", ...)` (`:150-159`).
4. **Gate D — `anthropic_claude` branch** (`:160-189`):
   - **D1 — API key**: `claude_ai_api_key` falsy → `Unavailable(reason="claude_ai_api_key_missing", ...)` (`:161-170`).
   - **D2 — budget repo**: `budget_repo is None` → `Unavailable(reason="claude_ai_budget_repo_missing", ...)` (`:171-179`).
   - All passed → `AnthropicExplanationProvider(budget_repo=..., monthly_cap_eur=claude_ai_budget_monthly_eur, max_output_chars=claude_ai_explanation_max_output_chars, model_name=claude_ai_explanation_model)` (`:180-189`).
5. **Gate E — unknown provider code**: `Unavailable(reason="real_client_not_implemented", ...)` (`:191-197`) listing supported codes ("stub", "anthropic_claude").

The `from portfolio_outlook_api.anthropic_explanation_provider import AnthropicExplanationProvider` import is lazy inside the factory (`:180-182`) so the Anthropic SDK is not loaded at module-import time.

### 11c. `anthropic_explanation_provider.py` — Anthropic SDK provider

Module status (docstring): "V1.1 Slice 29", "Replaces the Slice 10 stub for the Decision Package narrative path" (`anthropic_explanation_provider.py:1-3`), "Locked by §22.2 of the V1.1 doctrine" (`:5`).

- Class: `AnthropicExplanationProvider` (`anthropic_explanation_provider.py:182`) implements `ExplanationProviderProtocol` structurally (`:183-185`).
- Supporting Protocols / dataclasses: `_BudgetRepoProtocol` (`:65-68`), `_AnthropicMessageProtocol` (`:71-81`), `_AnthropicMessagesAPI` (`:84-85`), `_AnthropicClientProtocol` (`:88-89`), `_Usage` frozen dataclass (`:92-97`).

#### Call shape

The provider goes through the Anthropic Python SDK, not raw HTTP. The SDK is **lazy-imported**: `from anthropic import Anthropic` (`:217-221`) only happens when no `client_factory` is injected. Tests inject a fake `client_factory` so they never open a socket (`:16-18, 198`).

The single SDK call: `client.messages.create(**payload)` (`:238`). The payload is built by `_build_messages_payload(...)` (`:135-179`):

```python
{
  "model": <model_name>,
  "max_tokens": <max_output_chars>,
  "system": [
    {"type": "text", "text": SYSTEM_PROMPT_NL, "cache_control": {"type": "ephemeral"}},
    {"type": "text", "text": LOCKED_RISK_DISCLAIMER_NL, "cache_control": {"type": "ephemeral"}},
  ],
  "messages": [{"role": "user", "content": <user_payload>}],
}
```

(`anthropic_explanation_provider.py:147-179`).

- **System prompt**: `SYSTEM_PROMPT_NL` (`:55-62`) — locked Dutch instructions ("paraphrase assistant, 2–3 sentences, no new numbers, no advice, no opinion on price direction, always append the disclaimer").
- **Disclaimer**: `LOCKED_RISK_DISCLAIMER_NL` imported from `portfolio_outlook_portfolio` (`:37`, used at `:155`).
- **Tools**: none — the provider does not use Anthropic tool use; pure text-in / text-out.

#### Prompt-cache invariants

Both system blocks carry `"cache_control": {"type": "ephemeral"}` (`:151, :156`). Ephemeral = Anthropic's short-lived cache (~5 min default), not the 1-hour or persistent variant. The user payload has no cache breakpoint, so per-call billable input is just the system prompt + the Decision Package content. The cache stays warm for "every morning-chain call after the first" (`:13-15`).

Crucially, `compute_cost_eur` correctly handles cache misses by charging both raw `input_tokens` and `cache_creation_input_tokens` at the full input rate, and `cache_read_input_tokens` at the cached rate (`:242-251`) — so a cold start still bills correctly, just more expensively.

#### Hard-coded model identifier

- `DEFAULT_MODEL_NAME = "claude-haiku-4-5-20251001"` (`anthropic_explanation_provider.py:52`).
- `PROVIDER_CODE = "anthropic_claude"` (`:51`).
- Result version stamp: `model_version="v1.1-anthropic-2026-05"` (`:270`).
- The `model_name` on the result is read from the SDK response's `model` field when present, else the configured name (`:269`).
- Override path: `Settings.claude_ai_explanation_model` (`config.py:187`) → factory keyword (`ai_explanation_provider.py:188`).

#### Input / output validation

- Inbound response is **duck-typed** via `_AnthropicMessageProtocol` (`:71-81`) — only `content`, `usage`, `model` are read.
- Token counters: `int(getattr(usage, "...", 0))` (`:111-118`) — fields default to 0 if absent.
- Text extraction: blocks without a `text` attribute are silently skipped (`:127-131`).
- Output text validation is **downstream** in `ai_explanation_sync.generate_explanation` via `validate_explanation_output` (`ai_explanation_sync.py:246-251`) — that pass enforces the hallucinated-number guard.

#### Error handling

- No retry loop, no timeout, no circuit breaker in the provider.
- `assert_budget_available` raises `ClaudeAiBudgetExceededError` (`:228-230`); higher-level orchestrator (`ai_explanation_sync.py:229-240`) catches and surfaces it as `EXPLANATION_STATUS_FAILED` + `blocking_reason="provider_error"`.
- The promise in `:9-10` ("the factory falls back to the stub for the rest of the month") is **not** implemented at the provider level — it would have to be implemented by the orchestrator + a re-resolution loop, which is absent. After a breach, subsequent calls in the same process invocation will keep raising until the operator switches `provider_code` to `"stub"` or the month rolls over.

#### Audit / cost recording

- The only audit row this file emits is via `persist_call_cost(...)` (`:252-263`) — writes a `ClaudeAiBudgetUsageRecord` into table `claude_ai_budget_usage` (per `claude_ai_budget.py:5`, populated by storage migration 0043).
- **No** `system_event_recorder` calls. **No** `request_audit` calls. Higher-level evidence-ledger anchoring is `ai_explanation_sync.py`'s responsibility.

### 11d. `ai_explanation_sync.py` — orchestration

- Single public entry point: `generate_explanation(*, package, research_sources, provider, repo, max_output_chars) -> ExplanationReport` (`ai_explanation_sync.py:188-321`).
- `ExplanationReport` frozen dataclass (`:57-66`): `requested_at`, `completed_at`, `status`, `status_nl`, `help_nl`, `explanation_id`, `blocking_reason`, `hallucinated_numbers`.
- `_ExplanationRepoProtocol` (`:69-76`).
- `_build_canonical_input(...)` (`:83-154`) canonicalises the Decision Package + research metadata for hashing.
- `_build_evidence_ledger(...)` (`:157-185`) emits one entry per source: `evidence_kind="decision_package"` for the package itself (`:169`) plus one `evidence_kind="research_source"` per research source (`:179`).

#### Storage writes

- `repo.save_decision_package_explanation(explanation)` (`:278`) — writes `DecisionPackageExplanationRecord`.
- `repo.save_explanation_evidence_ledger_entry(ledger_entry)` (`:285`) — one per evidence source.
- The orchestrator does **not** read from storage; `package` and `research_sources` are passed in already-loaded by the caller (`:189-191`).
- Indirectly, when the provider is `AnthropicExplanationProvider`, `persist_call_cost` writes to `claude_ai_budget_usage`.

#### State-machine touchpoints

`status` on the explanation row is set from `validation.status` (`:268`). Failure branches set `status=EXPLANATION_STATUS_FAILED` with `blocking_reason="provider_error"` (`:234-238`) or `"persistence_error"` (`:291-295`). Provider-unavailable returns a report with `status="provider_unavailable"` but **no row is persisted** (`:199-209`).

The orchestrator does **NOT** mutate `action_draft.status`, `suggestion.status`, or `decision_package.status`. The explanation is a sibling/child row of the Decision Package, never a state transition on it. Response serializer: `safe_for_self_learning=False`, `safe_for_action_drafts=False`, `safe_for_orders=False` (`:344-346`).

#### Audit / hash chain

- `input_evidence_hash = _hash_text(input_text)` (`:215`) — SHA-256 over the canonical JSON of every Decision Package field + linked research metadata.
- `output_text_hash = _hash_text(provider_result.output_text)` (`:265`).
- Both hashes persist on `DecisionPackageExplanationRecord` (`:264-265`) and every `ExplanationEvidenceLedgerRecord` (`:170, 182`).
- Disclaimer stored: `risk_disclaimer_nl=LOCKED_RISK_DISCLAIMER_NL` (`:267`).
- **No `system_event_recorder` calls. No `request_audit` calls.**

#### Idempotency gap

`explanation_id = f"exp_{uuid4().hex}"` (`ai_explanation_sync.py:254`) — fresh UUID per run, **not** keyed on `(decision_package_id, content_hash)`. The module docstring states the intended invariant ("Generates one `DecisionPackageExplanationRecord` per `(decision_package_id, decision_package_content_hash)` pair", `:3-4`), but **no idempotency guard is implemented in this file**. Consequence: if `generate_explanation` is called twice for the same `(package_id, content_hash)`, two Anthropic calls happen, two budget rows are written, two explanation rows + duplicate ledger entries are persisted. Enforcement would need to live in the calling layer or as a DB unique constraint on `DecisionPackageExplanationRecord`.

### 11e. `claude_ai_budget.py` — monthly EUR budget cap

Module docstring (`claude_ai_budget.py:3-6`): "caps real Anthropic Claude usage at `CLAUDE_AI_BUDGET_MONTHLY_EUR` (default €50)" and "owns the read/write surface against the `claude_ai_budget_usage` audit table created by storage migration 0043".

#### Pricing constants

- `DEFAULT_INPUT_EUR_PER_M: Final[Decimal] = Decimal("0.80")` (`:34`)
- `DEFAULT_CACHED_INPUT_EUR_PER_M: Final[Decimal] = Decimal("0.08")` (`:35`)
- `DEFAULT_OUTPUT_EUR_PER_M: Final[Decimal] = Decimal("4.00")` (`:36`)

The pricing comment (`:12-20`) is explicit about the Haiku 4.5 tier defaults and the Sonnet 4.6 alternative (€3.00 / €0.30 / €15.00 per million); the choice of Haiku defaults aligns with the hard-coded `DEFAULT_MODEL_NAME` in the provider (`anthropic_explanation_provider.py:52`). All three rates are overridable per call.

#### Cap value origin

The cap is **passed in by the caller**, not a constant in this module. Signatures: `monthly_budget_status(monthly_cap_eur, ...)` (`:103`), `assert_budget_available(monthly_cap_eur, ...)` (`:125`). The factory reads `runtime_settings.claude_ai_budget_monthly_eur` (default `Decimal("50")`, `config.py:182`) and passes it through to `AnthropicExplanationProvider(monthly_cap_eur=...)` (`ai_explanation_provider.py:186`). Env-var override: `API_CLAUDE_AI_BUDGET_MONTHLY_EUR` via the standard `Settings` prefix.

#### Spend tracking

- Audit row: `ClaudeAiBudgetUsageRecord` (imported from `ai_trading_agent_storage`, `claude_ai_budget.py:31`).
- Table: `claude_ai_budget_usage`.
- Columns written by `persist_call_cost` (`:157-169`): `usage_id` (uuid prefixed `clbu_`), `budget_month`, `provider_code`, `model_name`, `called_at`, `input_units`, `cached_input_units`, `output_units`, `cost_eur`, `call_kind`, `explanation_nl`.
- Aggregation: `repo.monthly_total_eur(budget_month) -> Decimal` (`:63, :111`).
- Protocol surface (`:62-65`) is minimal — just `monthly_total_eur(budget_month)` and `save_usage(record)`.

#### Cap enforcement

- **Pre-call check.** `assert_budget_available` (`:122-139`) is invoked **before** the HTTP call by `AnthropicExplanationProvider.generate` (`anthropic_explanation_provider.py:228-230`). Computation: `monthly_budget_status` reads `repo.monthly_total_eur(month)`, subtracts from cap, sets `exceeded = remaining <= 0` (`:111-119`).
- **Post-call accounting.** `persist_call_cost` is invoked unconditionally after the SDK call returns (`anthropic_explanation_provider.py:252-263`). A single call **can** push the running total over the cap — the *next* call is then blocked. The cap is therefore a soft "no new calls after threshold," not a hard per-call upper bound.

#### Cap breach behaviour

- `raise ClaudeAiBudgetExceededError(...)` (`:134-138`). Message includes the cap, the month tag, the running total, and the Dutch instruction "provider valt terug op de stub" (`:137`).
- `ClaudeAiBudgetExceededError(RuntimeError)` (`:39-40`).
- The provider does **not** catch it (`anthropic_explanation_provider.py:223-271`); it bubbles to `ai_explanation_sync.generate_explanation`'s bare `except Exception` (`:229-240`) and becomes `status=EXPLANATION_STATUS_FAILED`, `blocking_reason="provider_error"`. **It is not classified to a distinct `budget_exceeded` status.**
- Auto-fallback to the stub is **not** implemented — see §11c above.

#### Reset period

- `budget_month_of(now: datetime) -> str` returns `now.astimezone(UTC).strftime("%Y-%m")` (`claude_ai_budget.py:68-71`).
- **Calendar month, UTC-anchored.** Not rolling 30 days.
- Reset is implicit: at 00:00 UTC on the 1st, `budget_month_of` returns a new tag, so `monthly_total_eur(new_month)` returns 0 and the cap auto-resets.

## 12. Cross-cutting reality observations

- **No FastAPI middleware.** `main.py` adds no CORS, no auth, no request-logging middleware, no exception handler. Request audit is an *application-level router* (`/audit/*`), not middleware.
- **No `extra="forbid"` at the app boundary.** `Settings` is `extra="ignore"` (`config.py:257`). Only the three `scheduler_routes.py` response models enforce `extra="forbid"` (`scheduler_routes.py:48, 61, 75`).
- **No `system_event_recorder` calls from the scheduler.** Scheduled-job successes/failures are recorded only as `SchedulerRunRecord` rows; system events are not emitted on cron-fire failure.
- **AI explanation idempotency gap.** `ai_explanation_sync.generate_explanation` re-bills on retry; the `(decision_package_id, content_hash)` uniqueness invariant is documented (`:3-4`) but unenforced in this file.
- **Anthropic-budget cap is post-call accounting.** A single oversized call can push the running total past the cap before being blocked; the cap is "no new calls after threshold", not "no over-cap call ever".
- **Policy / code drift.** `docs/ai-policy.md:38, 43` still talks about OpenAI usage and OpenAI budget contracts. The code has pivoted to Anthropic Claude (`claude_ai_budget.py:1`, `anthropic_explanation_provider.py:52`). The policy doc has not been updated. Likewise the V1 `status_models.OpenAiSettingsSection` + `build_settings_summary` placeholder (`status_builders.py:137-205`) still surfaces OpenAI on the status UI even though the live AI surface is Anthropic.
- **Hard-coded order-safety floor.** Five infrastructure response models all hard-code `safe_for_action_drafts=False` / `safe_for_orders=False` / `blocks_orders=True`: `release_readiness.serialize_release_readiness` (`:464-466`), `PortfolioValuationReadinessResponse` (`:91-93`), `PortfolioReconciliationReadinessResponse` (`:176-185`), `SchedulerV127StatusResponse` + `SchedulerV127RunsResponse` (`scheduler_routes.py:55-56, 78-79`), the read-only flags on `request_audit` response models (`:51-53, :76-78, :100-102`), and `ai_explanation_sync.serialize_explanation_for_response` (`:344-346`). This is the project-wide tri-defence pattern: scorecards never authorise orders, even when "green".
- **Decimal-as-string boundary** holds throughout the readiness + AI surface. The only intra-module Decimal reconstitution is `Decimal(row.market_value)` inside `_build_conversion_inputs` (`portfolio_valuation_readiness.py:411`), one hop before the conversion engine — and that boundary is internal to the readiness module.

## 13. Verification trail

- `grep -cE 'include_router' apps/api/src/portfolio_outlook_api/main.py` → 15 (matches the route catalogue above).
- `pip-audit` baseline (T-054) flagged `fastapi==0.136.3` as MAL-2026-4750; the FastAPI app is constructed via the same vulnerable release until pinned away (see `docs/code-health/04-bugs.md` FIND-PIPAUDIT-001). No code in this cluster currently uses `fastapi[standard]`, so the malicious `fastar` extra is not actually pulled in this repo (per the FIND).
- Module line counts above were re-measured by the cited subagent reads and differ from the task spec by 1–2 lines in a few files (e.g. `main.py` is 131, not 130; `status_routes.py` matches at 4014).
