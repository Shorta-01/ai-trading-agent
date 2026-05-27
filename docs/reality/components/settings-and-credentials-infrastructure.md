# Reality — settings and credentials infrastructure

**Scope.** What exists today for the settings and secrets surface. Maps each existing code module against the five-category intent in `docs/intent/settings-and-credentials.md` (locked 2026-05-26) + ADR `docs/decisions/0004-settings-and-credentials-structure.md`. Surfaces gaps where the intent has no implementation yet, and pre-empted defaults where code commits to a value the intent left open.

This is **reality documentation only** — no settings code is modified by this task. Phase 1c gap analysis (T-046 and similar) will score the gaps surfaced here.

## 0. TL;DR — three settings vocabulary homes

The settings + credentials surface is **bifurcated across three vocabulary homes**:

1. **`config.py` env-var surface (api + worker)** — `pydantic_settings.BaseSettings` with `env_prefix="API_"` / `env_prefix="WORKER_"`. Loads at process startup. Holds: secrets (API keys, DB URL, IBKR account hint), feature gates (`*_enabled` booleans), scheduler cron strings, V1.1 budget caps.
2. **`packages/domain/src/portfolio_outlook_domain/settings.py` typed-vocabulary module** — pure Pydantic models + StrEnum vocabularies. No I/O. Holds: `UserStrategySettings`, `AllowedUniverseSettings`, `IBKRConnectionSettings`, `OpenAIIntegrationSettings`, `SecretReference`, `ApiBudgetPolicy`, `SettingsProfile`. Used as the typed boundary between the runtime layer and the storage layer.
3. **`TradingSettingsRecord` storage table** — `packages/storage/.../repository_contracts.py:1395-1411`. Persisted JSON columns `allowed_universe_json` + `user_strategy_json` carry the long-term Category 2 user preferences. Read+write via `apps/api/src/portfolio_outlook_api/trading_settings.py:134-197`.

There is **no single canonical settings module**. The five intent categories map onto these three homes with significant overlap (e.g. `paper_only_mode` is in both `config.py` AND `PortfolioSettings`) and significant gaps (Category 4 monitoring has no implementation, Category 5 audit/backup is a stub).

Sibling reality docs:

- `docs/reality/components/api-infrastructure-and-ai.md` §2 — full `apps/api/.../config.py:Settings` field catalogue (78 fields).
- `docs/reality/components/worker-orchestration-and-scheduling.md` §3 — full `apps/worker/.../config.py:Settings` field catalogue.
- `docs/reality/components/api-infrastructure-and-ai.md` §11e — Anthropic Claude `claude_ai_budget.py` cost-tracking detail.

## 1. The five-category intent (verbatim refs)

Per `docs/intent/settings-and-credentials.md` (locked 2026-05-26):

| Category | Scope | Intent file:line |
|---:|---|---|
| 1 | **Connections** — IBKR, EODHD, AI providers, database (secrets live here) | `:14-23` |
| 2 | **User preferences** — base currency, tax residency, risk profile, etc. (no secrets) | `:25-55` |
| 3 | **Safety limits** — max order value, max orders/day, kill switch, drawdown circuit breaker | `:57-71` |
| 4 | **Monitoring** — critical-alert email, event classification, quiet hours | `:73-81` |
| 5 | **Audit, backup, observability** — retention, backup destination, restore-test cadence | `:83-93` |

Plus **7 UX rules** (`:95-105`) and **7 open questions** (`:107-115`) — see §6 + §7 below.

ADR `docs/decisions/0004-settings-and-credentials-structure.md` accepts the 5-category model + 7 UX rules and explicitly assigns gap-mapping to T-061 (this doc).

## 2. Vocabulary home A — env-var Settings (`config.py`)

### 2.1 API config (`apps/api/src/portfolio_outlook_api/config.py:78-258`)

`Settings(BaseSettings)` with `SettingsConfigDict(env_prefix="API_", env_nested_delimiter="__", extra="ignore")` at `config.py:254-258`. 78 fields total, full inventory in `docs/reality/components/api-infrastructure-and-ai.md` §2.

Category coverage:

- **Category 1** (`:86-189`): `eodhd_enabled` (`:120`), `eodhd_api_key` (`:121`), `eodhd_base_url` (`:122`), `claude_ai_api_key` (`:188`), `claude_ai_explanation_model` (`:187`), `claude_ai_explanation_max_output_chars` (`:189`), `ibkr_enabled` (`:86`), `ibkr_account_id_hint` (`:88`), `ibkr_gateway_url` (`:89`), `storage.database_url` (nested `:12`). **No OpenAI fields, no Anthropic-organization-id, no database host/port (only the full URL).**
- **Category 2** (sparse — only string scalars): `suggestions_risk_profile:str="Gebalanceerd"` (`:138`), `universe_set:str="SP500"` (`:193`), `forecast_pilot_conids:str="ASML.AS"` (`:136`), `action_drafts_default_buy_value:str="1000"` (`:143`), `action_drafts_top_up_pct:str="0.25"` (`:144`). **No base_currency, no tax_residency, no morning_evaluation_time, no ui_language.** The long-term Category 2 carrier is the storage `TradingSettingsRecord`, not Settings.
- **Category 3**: `paper_only_mode:bool=True` (`:84`), `claude_ai_budget_monthly_eur:Decimal=50` (`:182`), `action_draft_approval_valid_minutes:int=5` (`:153`), `qvm_min_universe_size:int=30` (`:225`); the locked `predictor_backtest_enabled:bool=False` (`:202`). **No `max_order_value`, no `max_orders_per_day`, no `trading_halt_master_switch`, no drawdown threshold, no calibration thresholds.**
- **Category 4**: only feature gates that double as monitoring proxies — `storage.enabled` (`:13`), `storage.writes_enabled` (`:14`), `ibkr_status_check_enabled` (`:91`), `scheduler_enabled` (`:163`). **No critical-alert email, no quiet hours, no event-classification list.**
- **Category 5**: `research_upload:ResearchUploadSettings` (`:228`) holds `archive_dir`, `max_file_size_bytes`, `allowed_extensions`; `research_extraction.extracted_text_archive_dir` (`:64`); `forecast_history_lookback_days:int=400` (`:127`); `universe_scan_history_lookback_days:int=400` (`:168`). **No `audit_log_retention`, no `backup_destination`, no `backup_frequency`, no `restore_test_reminder_cadence`.**

### 2.2 Worker config (`apps/worker/src/portfolio_outlook_worker/config.py:69-85`)

`Settings(BaseSettings)` with `env_prefix="WORKER_"`, full inventory in `docs/reality/components/worker-orchestration-and-scheduling.md` §3.

Category coverage:

- **Category 1** (`:33-37, :49-52`): `ibkr.host`, `ibkr.port`, `ibkr.client_id`, `ibkr.account_id`, `eodhd.api_key`, `storage.database_url`. **No `claude_ai_api_key` on the worker** — Claude is API-only (T-006 §11d documents the cross-tier split).
- **Category 2**: **None.** Worker consumes Category 2 via the storage `TradingSettingsRecord` JSON columns, not via env vars.
- **Category 3**: `paper_only_mode:bool=True` (`:72`), `ibkr.enabled:bool=False` (`:33`), `scheduler.enabled:bool=False` (`:64`), `eodhd.fetch_enabled:bool=False` (`:52`). All default OFF.
- **Category 4**: `scheduler.heartbeat_interval_seconds:int=60` (`:66`), `scheduler.timezone:str="Europe/Brussels"` (`:65`).
- **Category 5**: None.

### 2.3 Settings prefix mismatch — already flagged (T-009)

Per `docs/reality/components/infra-docker-and-compose.md` §5 (T-009), `infra/docker/.env.example` ships **bare keys** (`STORAGE_ENABLED`, `IBKR_ENABLED`, `EODHD_API_KEY`, etc.) that Pydantic's `env_prefix="API_"`/`env_prefix="WORKER_"` does NOT match. Compose only rewrites 2 keys (`ENVIRONMENT` → `API_ENVIRONMENT` + `WORKER_ENVIRONMENT`; `PAPER_ONLY_MODE` similarly). **Every other bare key is silently dropped by `extra="ignore"`.** This blocks V1 readiness as-shipped — re-recorded here as a cross-reference.

## 3. Vocabulary home B — domain typed-vocabulary (`packages/domain/.../settings.py`)

File: `packages/domain/src/portfolio_outlook_domain/settings.py` (833 lines, MI 0.00 — flagged in T-055 as `FIND-013` rank-B / `FIND-012` cluster member). Pure Pydantic models + StrEnums — **no `BaseSettings`, no env-var loading**.

### 3.1 StrEnum vocabularies (`settings.py:51-114`)

8 enums covering Category 2 user preferences + Category 3 safety limits:

| Enum | File:line | Values |
|---|---|---|
| `AllowedAssetType` | `:51-56` | ETF / STOCK / CURRENCY / BOND_ETF / COMMODITY_ETF |
| `BlockedAssetType` | `:59-67` | OPTIONS / FUTURES / LEVERAGE / SHORT_SELLING / CRYPTO / PENNY_STOCKS / CFDS / COMPLEX_DERIVATIVES |
| `PortfolioGoal` | `:70-73` | BALANCED_GROWTH_RISK / STABLE_INCOME / LONG_TERM_GROWTH |
| `StrategyRiskLevel` | `:76-79` | LOW / MEDIUM / HIGH **(naming mismatch with intent's Conservative / Moderate / Aggressive)** |
| `AssetMixPreference` | `:82-85` | ETF_AND_STOCK_MIX / MOSTLY_ETFS / MOSTLY_STOCKS |
| `RegionPreference` | `:88-92` | GLOBAL / EUROPE / USA / EMERGING |
| `SectorPreference` | `:95-102` | 7-sector vocabulary |
| `CurrencyPreference` | `:105-108` | EUR_PREFERRED_USD_ALLOWED / EUR_ONLY / USD_ONLY |
| `AssetPermissionStatus` | `:111-114` | ALLOWED / WATCH_ONLY / BLOCKED |

V1 blocked-asset-type frozen list at `:39-48` (`_VERSION_1_BLOCKED_ASSET_TYPES`) — Category 3 hard block.

### 3.2 Category 2 / 3 vocabulary classes (`settings.py:130-326`)

- `AllowedUniverseSettings` (`:130-139`) — **Category 3 hard filter**: which asset types are allowed at the universe level. Validators enforce the V1 block list.
- `UserStrategySettings` (`:142-182`) — **Category 2 preferences**: `portfolio_goal`, `risk_level:StrategyRiskLevel`, `preferred_regions`, `preferred_sectors`, `avoided_sectors`, `max_position_pct:Decimal=10` (Category 3 cap), `min_cash_reserve_pct:Decimal=5` (Category 3), `currency_preference`, `prefer_simple_belgian_tax_admin:bool=True` (Category 2 — Belgian tax-admin nod), `user_buffer_eur:Decimal=0` (Category 3).
- `PortfolioSettings` (`:303-316`) — mixed Category 2 + Category 3: `starting_paper_capital:Money=€10000` (`:305`), `base_currency:CurrencyCode="EUR"` (`:305`), `paper_live_mode:PaperLiveMode=PAPER` (`:307` — hard-locked PAPER), `risk_profile:str="balanced"` (`:307`), four refresh-toggle booleans (`:311-313`), `interface_language:str="nl"` (`:315`), `simple_ui_enabled:bool=True` (`:315`). Model validator `validate_paper_mode_and_percentages` (`:318-328`) hard-locks `paper_live_mode==PAPER` for V1.

### 3.3 Category 1 connection vocabulary (`settings.py:331-684`)

- **`SecretReference`** (`:331-370`) — Category 1 typed pointer. Fields: `secret_reference_id`, `secret_name`, `storage_kind:SecretStorageKind` (see §3.4), `status:SecretStatus`, `environment_variable_name:str|None`, `configured:bool`, `last_checked_at`, `explanation_nl`. **Defence-in-depth**: validator at `:348-357` rejects `sk-`-prefixed names (`sk-` is an OpenAI key prefix — guard against accidentally putting the secret value in the name field).
- **`IBKRConnectionSettings`** (`:373-419`) — Category 1 IBKR. Fields include `enabled`, `host`, `port`, `client_id`, `account_id`, `paper_account_required:bool=True`, `allow_live_order_transmission:bool=False`. Model validator (`:397-400`) **hard-locks** `allow_live_order_transmission=False` AND `paper_account_required=True` — V1 cannot transmit a live order even through the domain vocabulary.
- **`OpenAIIntegrationSettings`** (`:422-468`) — Category 1 OpenAI. Fields include `enabled`, `api_key_secret_reference_id:SecretReferenceId|None` (the secret is referenced by id, NEVER stored inline), `default_research_model`, `cheaper_model`, `fallback_model`, `budget_policy_id`. **No equivalent `AnthropicIntegrationSettings` class exists** in the domain vocabulary.
- `OpenAIModelPricing` (`:471-502`), `ApiBudgetPolicy` (`:505-542`), `ApiUsageSummary` (`:545-603`), `ApiCostEstimate` (`:606-640`), `ApiConnectionCheck` (`:643-657`).
- **`SettingsProfile`** (`:660-684`) — aggregate root that bundles `ibkr_settings + openai_settings + secret_references[] + budget_policies[]`. Cross-validates that `OpenAIIntegrationSettings.api_key_secret_reference_id` resolves to one of the listed `secret_references` (`:680-683`).

### 3.4 `SecretStorageKind` enum — pre-empts Doctrine §15 open question

In `packages/domain/src/portfolio_outlook_domain/enums.py:953-957`:

```python
class SecretStorageKind(StrEnum):
    ENVIRONMENT_VARIABLE = "environment_variable"
    LOCAL_GITIGNORED_FILE = "local_gitignored_file"
    EXTERNAL_SECRET_MANAGER_FUTURE = "external_secret_manager_future"
    NOT_CONFIGURED = "not_configured"
```

Intent §7 open question: **"Storage backend choice: OS keyring vs encrypted file."** The domain vocabulary commits 4 storage-kind values that do NOT include `OS_KEYRING`. `LOCAL_GITIGNORED_FILE` is closest to "encrypted file" but the name does not commit to encryption. The de-facto runtime mechanism is **environment variables** (`ENVIRONMENT_VARIABLE`) — every secret in §4 below enters via Pydantic Settings from env.

### 3.5 Module-level helpers (`settings.py:191-833`)

`evaluate_asset_permission` (`:191-239`), `get_allowed_universe_help_texts` (`:242-259`), `get_user_strategy_help_texts` (`:262-290`), `strategy_settings_summary_nl` (`:293-300`), `build_default_settings_profile` (`:687-744`), `ibkr_settings_ready_for_paper` (`:747-758`), `openai_settings_ready` (`:761-770`), `estimate_openai_cost` (`:773-801`), `calculate_budget_status` (`:804-818`), `remaining_budget_eur` (`:821-825`), `connection_check_blocks_jobs` (`:828-833`).

Defaults in `build_default_settings_profile` (`:687-744`): IBKR `NOT_CONFIGURED`, OpenAI `NOT_CONFIGURED`, two empty budget rows (daily+monthly, both `enabled=False`, `budget_amount_eur=0`).

## 4. Vocabulary home C — storage-persisted `TradingSettingsRecord`

`TradingSettingsRecord` lives in `packages/storage/.../repository_contracts.py:1395-1411` with `version:int` for optimistic-concurrency tracking. Two JSON columns:

- `allowed_universe_json` — serialised `AllowedUniverseSettings`.
- `user_strategy_json` — serialised `UserStrategySettings`.

The write path is `apps/api/.../trading_settings.py:134-197` (save-on-write — no apply-cadence-by-category mechanism per UX rule 4; see §6).

The `version:int` field is the foundation for the intent UX rule "Show me what changed" — but per §6 no diff route is implemented today.

## 5. The storage-layer settings facade (`packages/storage/.../settings.py`)

File: `packages/storage/src/ai_trading_agent_storage/settings.py` (61 lines).

Only the Database portion of Category 1 lives here:

- `@dataclass(frozen=True) DatabaseConnectionSettings` (`:7-14`): `database_url:str|None`, `database_url_configured:bool`, `safe_database_label:str`, `explanation_nl:str`. **Intentionally non-connecting** — the struct does not open a DB connection; it just summarises whether a URL was supplied and produces a redacted display label.
- `_redacted_netloc` (`:17-28`) + `redact_database_url` (`:31-45`) — redaction helpers. Returns Dutch labels for missing/invalid URL (`"Niet ingesteld"`, `"Ongeldige database-url"`).
- `build_database_connection_settings` (`:48-61`) — factory used at ~5 boot sites in api + worker.

This module is the **single redaction point** for DB credentials — the raw URL never leaves the storage adapter; downstream code sees `DatabaseConnectionSettings.safe_database_label` only.

## 6. Paper-setup trio — first-run wizard surface

"Paper setup" is **the first-run wizard that creates the paper portfolio** — base_currency / starting_cash / portfolio_name + three explicit confirmations. It is NOT the long-term Category 2 carrier (that's `TradingSettingsRecord`). IBKR/OpenAI integrations appear here only as `IBKR_NOT_CONFIGURED` / `OPENAI_NOT_CONFIGURED` warning reasons (`packages/domain/.../paper_setup.py:253-254`).

### 6.1 Domain layer — `packages/domain/.../paper_setup.py` (275 lines)

- `PaperCashAccountDefinition` (`:17-42`) — frozen dataclass: `paper_cash_account_id`, `currency:PaperPortfolioBaseCurrency`, `starting_cash:Decimal`, `explanation_nl`. Rejects float (`:23-28`); positive-only (`:30-35`).
- `FirstRunPaperPortfolioSetupRequest` (`:45-86`) — model validator (`:76-86`) **hard-requires** all three booleans true (`user_confirmed_paper_only`, `user_confirmed_no_real_money`, `user_confirmed_no_broker_order`) AND `setup_mode==FIRST_RUN`.
- `FirstRunPaperPortfolioSetupPreview` (`:89-122`) — hard-locks `persisted=False` at the domain layer (`:113-114`).
- `PaperPortfolioSetupDefaults` (`:125-175`) — `default_starting_cash=€10000` (`:159`), hard-locks `paper_only_required=True` (`:169-170`), `broker_required=False` (`:170`), `live_trading_allowed=False` (`:170`).
- `build_default_paper_portfolio_setup_defaults` (`:204-215`) → EUR / €10000 / "Mijn paper portefeuille".

### 6.2 API surface — `apps/api/.../paper_setup.py` (105 lines)

Does NOT reuse the domain module — duplicates the schema as a plain `BaseModel`:

- `SetupPreviewInput(BaseModel)` (`:15-28`): `base_currency:str`, `starting_cash:str` (note: **string**, not Decimal — domain rejects float, API serialises through str), `portfolio_name`, three confirmation booleans.
- `get_setup_status` (`:31-41`), `get_setup_defaults` (`:44-55`), `create_setup_preview` (`:58-105`) — **no persistence here**, response includes `"persisted": False`.

### 6.3 Persistence — `apps/api/.../paper_setup_persistence.py` (127 lines)

The write path. `persist_first_run_paper_setup` (`:44-127`):

1. Storage-enabled gate (`:57-65`) — "Opslag staat uit. Opslaan is geblokkeerd."
2. Database-URL gate (`:67-76`) — "Database-url ontbreekt."
3. `StorageConnectionProvider` via `build_database_connection_settings` (`:78`).
4. `repository.create_setup(CreatePaperPortfolioSetupRequest(...))` (`:81-95`).
5. Storage table: `paper_portfolio_setups` (`packages/storage/.../metadata.py:35`).

DB CHECK constraints at `metadata.py:53-77`: `base_currency='eur'`, `starting_cash_amount > 0`, `paper_only IS TRUE`, `real_money_used IS FALSE`, `broker_order_created IS FALSE`, `live_trading_enabled IS FALSE`, `user_confirmed_paper_only IS TRUE`, `user_confirmed_no_real_money IS TRUE`. **These constraints architecturally forbid Real-money mode at the database layer** — separate from the validator locks in the domain layer.

## 7. Secret-read sites — full inventory

The system has **seven distinct secret/credential types** entering via Pydantic Settings, plus one implicit env-var read.

| # | Secret | Env var | Pydantic field | Consumer site(s) |
|---:|---|---|---|---|
| A | EODHD API key (api) | `API_EODHD_API_KEY` | `Settings.eodhd_api_key:str|None=None` (`apps/api/.../config.py:121`) | `market_data_adapter_factory.py:44, 48-53`; `status_routes.py:3836, 3854`; `release_readiness.py:135, 145-153` (presence gate, blocker `BLOCKER_EODHD_API_KEY_MISSING`) |
| B | EODHD API key (worker) | `WORKER_EODHD__API_KEY` (nested) | `EodhdSettings.api_key:str|None=None` (`apps/worker/.../config.py:49`) | `EodhdClient.__init__` at `apps/worker/.../providers/eodhd.py:131`; raises `EodhdNotConfiguredError` at `:150, :176` when `None`; key passed as `api_token` query param at `:156, :182` |
| C | Claude AI key (api) | `API_CLAUDE_AI_API_KEY` | `Settings.claude_ai_api_key:str|None=None` (`apps/api/.../config.py:188`) | `ai_explanation_provider.py:161-170` (presence gate → `ExplanationProviderUnavailable`); `ai_ts_provider.py:215-224`; `release_readiness.py:314, 316-329` (blocker `BLOCKER_CLAUDE_AI_API_KEY_MISSING_WHEN_REAL_CLIENT_ENABLED`). **NB**: Pydantic field is presence-only; see (H) below. |
| D | IBKR account id (worker) | `WORKER_IBKR__ACCOUNT_ID` (nested) | `IbkrSettings.account_id:str|None=None` (`apps/worker/.../config.py:37`) | `main.py:45` (gate), `:72-76` (`gateway.connect(account_id=...)`); `IbkrGateway.connect` at `ibkr_gateway.py:221` |
| E | IBKR account id hint (api) | `API_IBKR_ACCOUNT_ID_HINT` | `Settings.ibkr_account_id_hint:str|None=None` (`apps/api/.../config.py:88`) | **Display/scoping hint** (NOT used for connection): ~10 routes use it as a row-filter. `ibkr_status.py:153, 260`; `ibkr_connection_routes.py:162, 187`; `ibkr_watchlists.py:64`; `forecast_routes.py:160`; `market_data_runtime_routes.py:182`; `reconciliation.py:276`; `action_draft.py:267`; `ibkr_submission.py:241`; `decision_package_routes.py:185`; `watchlist_confirmation_routes.py:129, 146`; `ibkr_contracts.py:101` |
| F | Database URL (api + worker) | `API_STORAGE__DATABASE_URL` / `WORKER_STORAGE__DATABASE_URL` (nested) | `StorageSettings.database_url:str|None=None` (`apps/api/.../config.py:12`, `apps/worker/.../config.py:17`) | **~153 distinct read sites** across the codebase — every persistence-touching route gates on `storage.enabled and storage.database_url`. Representative: `main.py:66` (api boot), `main.py:53, 62` (worker boot), `paper_setup_persistence.py:67`, `trading_settings.py:98, 153`, `scheduler.py:138, 208, 214, 240, 243` (worker), all forecast/market-data/IBKR/reconciliation routes. URL is consumed only by `build_database_connection_settings(database_url)` → `StorageConnectionProvider(...)`, then SQLAlchemy. The raw URL never leaves the storage adapter (redaction at `packages/storage/.../settings.py:17-45`). |
| G | OpenAI API key | None — no env-var wiring | None — only domain vocabulary at `packages/domain/.../settings.py:426` (`api_key_secret_reference_id:SecretReferenceId|None`) | **No runtime consumer.** The OpenAI integration is vocab-only — the env-var bridge does not exist. See §10 below for the gap. |
| H | **Anthropic SDK auto-read of `ANTHROPIC_API_KEY`** | `ANTHROPIC_API_KEY` (NOT `API_CLAUDE_AI_API_KEY`) | **Not declared in any Pydantic field** | `Anthropic()` SDK constructor at `apps/api/.../anthropic_explanation_provider.py:221` AND `anthropic_ts_provider.py:248` — both call `Anthropic()` with no args, so the SDK auto-reads `ANTHROPIC_API_KEY` from the OS environment. **The Pydantic `claude_ai_api_key` field is only a presence-check gate; the SDK reads a different env var directly for transport.** This is an inconsistency worth surfacing. |

### 7.1 `os.environ` / `os.getenv` direct reads

**Zero hits in production src/.** Every env-var access flows through Pydantic Settings — except the Anthropic SDK auto-read at (H) above. Test fixtures in `packages/storage/tests/*` are the only `os.environ` consumers (out of scope).

### 7.2 `secret_reference_id` typed FK references (NOT secrets)

These are pointer rows, NOT secret values. Sites:

- `packages/domain/.../identifiers.py:71` — type alias.
- `packages/domain/.../settings.py:332, 426, 464-465, 674-677, 680-683` — schema definitions.
- `packages/domain/.../settings.py:705, 710, 764, 768-769` — `build_default_settings_profile` references.

`OpenAIIntegrationSettings.api_key_secret_reference_id` is the canonical example: the domain stores an id pointing at a `SecretReference` row that itself stores the `environment_variable_name` — never the secret value.

## 8. Category-by-category mapping table (intent → reality)

### Category 1 — Connections

| Intent bullet | Implementation | Where (path:line) |
|---|---|---|
| IBKR host / port / client_id / account_id | Settings field (worker) + scoping hint (api) | `apps/worker/.../config.py:34-37`; `apps/api/.../config.py:88-89, 97-99, 106-108, 148-150` |
| IBKR PAPER ↔ REAL toggle | **Not implemented** — hard-locked PAPER at 3 layers: domain (`packages/domain/.../settings.py:319-321, 397-398`), Settings defaults (`paper_only_mode:bool=True`), DB CHECK constraints (`metadata.py:53-77`) | n/a |
| EODHD API key + tier selector + quota display | Settings field only — no tier selector, no quota display | `apps/api/.../config.py:121`; `apps/worker/.../config.py:49`; consumer `market_data_adapter_factory.py:44` |
| AI provider toggle (Claude default, OpenAI alt) | Provider-code string field; **OpenAI not wired** | `apps/api/.../config.py:159` (`ai_explanation_provider_code:str="stub"`); domain has `OpenAIIntegrationSettings` but no env-var bridge |
| Per-provider monthly budget cap | Implemented for Claude only | `apps/api/.../config.py:182`; enforcement at `claude_ai_budget.py:122-139` |
| Fallback-enabled toggle | Encoded as provider-code `"stub"` behaviour | `apps/api/.../ai_explanation_provider.py:150-159` |
| Database host / port / user / password | Single URL string only; no individual fields | `apps/api/.../config.py:12`; redaction at `packages/storage/.../settings.py:17-45` |
| Test-connection button per credential | **Domain vocab exists** (`ApiConnectionCheck`); no HTTP route at `/test-connection`. IBKR has `ibkr_status_check_enabled`; EODHD `/eodhd/health` is closest | partial |

### Category 2 — User preferences

| Intent bullet | Implementation | Where (path:line) |
|---|---|---|
| Base currency (EUR default) | Domain field + DB constraint | `packages/domain/.../settings.py:305`; `metadata.py:53` |
| Tax residency (Belgium default) | **Not implemented** as a field; only `prefer_simple_belgian_tax_admin:bool=True` (`packages/domain/.../settings.py:152`) hints | n/a |
| Trading hours / market focus | Not implemented; `universe_set:str="SP500"` is closest |
| Morning evaluation time (07:00 default) | Encoded in cron string | `apps/api/.../config.py:165`; `apps/worker/.../config.py:65`; `apps/worker/.../orchestrator.py:167-179` (07:00 relabel) |
| Hourly refresh window | Hardcoded `07:00-21:00` cron | `apps/worker/.../scheduler.py:3` (docstring); not configurable |
| UI language (Dutch default) | Domain field, not env-var | `packages/domain/.../settings.py:315` |
| Risk profile Conservative/Moderate/Aggressive | **Vocab naming mismatch** — domain uses LOW/MEDIUM/HIGH (`packages/domain/.../settings.py:76-79`); API has free-string `suggestions_risk_profile="Gebalanceerd"` (`apps/api/.../config.py:138`) |
| **Base Kelly fraction (0.25 default Moderate)** | **0.5 hardcoded** (V1 product lock §21.5) at `packages/portfolio/.../kelly_sizing.py:51` — `DEFAULT_KELLY_FRACTION: Final[float] = 0.5`. **Contradicts intent doc's 0.25 Moderate default.** Hardcoded constant; not a Settings field, not a domain field, not user-controllable. T-002 finding **re-confirmed**. |
| Max % per position / sector / asset class | Per-position implemented as `UserStrategySettings.max_position_pct:Decimal=10` (`packages/domain/.../settings.py:149`); per-sector cap `DEFAULT_PER_SECTOR_CAP_PCT:float=30.0` (`packages/portfolio/.../kelly_sizing.py:53`); per-asset-class **not implemented** |
| Default order behaviour | Encoded as `action_drafts_top_up_pct:str="0.25"`, `action_drafts_reduce_pct:str="0.25"` (`apps/api/.../config.py:144-145`) |
| Stop-loss policy | Not implemented (intent §15 open question) |
| Portfolio valuation method | Not implemented as configurable field |

### Category 3 — Safety limits

| Intent bullet | Implementation | Where (path:line) |
|---|---|---|
| Max order value | **Not implemented** |
| Max orders per day | Not implemented |
| Max total exposure | Indirectly via `max_position_pct` + Kelly per-sector cap |
| Minimum cash buffer | `UserStrategySettings.min_cash_reserve_pct:Decimal=5` (`packages/domain/.../settings.py:150`); `user_buffer_eur:Decimal=0` (`:156`) |
| Trading halt master switch | Closest: `paper_only_mode:bool=True` + `ibkr_paper_order_submission_enabled:bool=False` — not a single kill switch |
| Whitelist / blacklist of instruments | `AllowedUniverseSettings.blocked_asset_types` for class-level block; `universe_set:str="SP500"` for whitelist; no per-ticker list |
| Drawdown circuit breaker | Not implemented |
| Calibration drift thresholds | Not implemented as configurable; `ensemble_weight_strategy` (`apps/api/.../config.py:207`) is adjacent |
| Predictor retirement / shadow-promotion / speculative-classification thresholds | Not implemented |
| AI budget caps | Implemented for Claude: `claude_ai_budget_monthly_eur:Decimal=50` (`apps/api/.../config.py:182`); enforcement `apps/api/.../claude_ai_budget.py:122-139` |

### Category 4 — Monitoring

| Intent bullet | Implementation |
|---|---|
| Critical-alert email | **Not implemented** |
| Critical event classification | Partial: `ApiConnectionCheck.blocks_related_jobs` (`packages/domain/.../settings.py:643-657`); audit tables exist; `system_event_recorder.py` family — but these are audit-log not alerting |
| Quiet hours | Not implemented |
| Delivery channels | Not implemented (§15 open) |

### Category 5 — Audit, backup, observability

| Intent bullet | Implementation |
|---|---|
| Audit log retention | Not implemented as a setting (audit tables themselves exist via 13 `SqlAlchemy*AuditRepository` in storage — see `docs/reality/components/stub-packages.md` §3) |
| Backup destination / frequency / restore-test reminder | **Display-only stub** in `apps/api/.../storage_status.py:56, 136` (`StorageBackupStatus`); surfaces `backup_not_tested` warning at `:96`. No actual backup configuration field. |
| User-initiated reconciliation trigger | Partial — reconciliation routes exist (`apps/api/.../reconciliation.py:276`); no explicit settings-page button code |
| On-demand backtest trigger | `predictor_backtest_enabled:bool=False` is a feature gate, not a button |
| On-demand annual tax report | Not implemented |

## 9. The 7 UX rules from intent (§6) — reality check

| # | Intent rule | Implementation status | Where |
|---:|---|---|---|
| 1 | Settings UI grouped by category 1→5 | **Not implemented** — no grouped category UI; closest is `apps/api/.../status_builders.py` building status panels | n/a |
| 2 | Test-connection button per credential | Partial — `ApiConnectionCheck` domain model (`packages/domain/.../settings.py:643-657`) exists; no HTTP route at `/test-connection`; IBKR has `ibkr_status_check_enabled` + connection-routes; EODHD `/eodhd/health` closest implemented test | partial |
| 3 | Secrets never re-displayed | **Honoured by design.** Pydantic `str|None` fields with no `repr` override. DB URL redaction at `packages/storage/.../settings.py:17-45`. `SecretReference` validator at `packages/domain/.../settings.py:355-356` rejects `sk-`-prefixed names. | ✓ |
| 4 | Apply cadence by category (Cat 2 deferred to next 07:00) | **Not implemented as a code mechanism.** Save path `apps/api/.../trading_settings.py:134-197` applies immediately. No 07:00-deferral wrapper. | ✗ |
| 5 | PAPER → REAL typed confirmation (`BEVESTIG REAL`) | **Not implemented.** The system instead **hard-locks PAPER**: validator locks in domain (`packages/domain/.../settings.py:319-321, 397-398`); Settings defaults (`paper_only_mode:bool=True`); storage CHECK constraints (`metadata.py:53-77`). PAPER→REAL is architecturally forbidden in V1 — typed-confirmation UX is moot. | n/a (forbidden) |
| 6 | "Show me what changed" diff button | Not implemented. `TradingSettingsRecord.version:int` exists (`repository_contracts.py:1398`) as the foundation but no diff route. | ✗ |
| 7 | Export / import as encrypted file | Not implemented. No `export_settings` / `import_settings` symbols. | ✗ |

**Honoured: 1 of 7** (Rule 3, by-design). **Not implemented: 5 of 7**. **Architecturally moot: 1 of 7** (Rule 5).

## 10. The 7 open questions from intent (§7) — defaults committed in code

| # | Intent open question | Code default committed? | Citation |
|---:|---|---|---|
| 1 | Storage backend choice (OS keyring vs encrypted file) | **Pre-empted** — `SecretStorageKind` enum has 4 values (`ENVIRONMENT_VARIABLE / LOCAL_GITIGNORED_FILE / EXTERNAL_SECRET_MANAGER_FUTURE / NOT_CONFIGURED`) — **no `OS_KEYRING` value**. De-facto: environment variables. | `packages/domain/.../enums.py:953-957`; `packages/domain/.../settings.py:712` |
| 2 | Stop-loss policy default | Not implemented — open question remains open | n/a |
| 3 | Drawdown circuit-breaker threshold default | Not implemented — open | n/a |
| 4 | Critical alert channels beyond email | Not implemented at all — open | n/a |
| 5 | Per-provider AI budget defaults | **Pre-empted for Claude only**: `claude_ai_budget_monthly_eur:Decimal=50` (locked by V1.1 §22.2 per `apps/api/.../config.py:178-182`). OpenAI has no env-var wiring; only domain template defaulting to `budget_amount_eur=0, enabled=False` (`packages/domain/.../settings.py:718-740`). | `apps/api/.../config.py:182` |
| 6 | Speculative-classification threshold defaults | Not implemented — open | n/a |
| 7 | Default config of data-feature toggles for new installs | **Pre-empted by uniform OFF default**: `eodhd_enabled:bool=False` (`apps/api/.../config.py:120`), `eodhd.fetch_enabled:bool=False` (worker `:52`), `market_data_sync_enabled:bool=False` (`:118`), `forecast_sync_enabled:bool=False` (`:126`), `ai_explanation_enabled:bool=False` (`:157`), `scheduler_enabled:bool=False` (`:163`). Matches the Task-120 "disabled by default" lock. | multiple sites |

### Bonus pre-empted default — Kelly fraction

Intent specifies Kelly fraction by risk profile (Conservative 0.15 / Moderate 0.25 / Aggressive 0.40). **Code default is 0.5**, hardcoded as a module-level `Final` constant:

```python
# packages/portfolio/src/portfolio_outlook_portfolio/kelly_sizing.py:51
DEFAULT_KELLY_FRACTION: Final[float] = 0.5
```

The docstring at `kelly_sizing.py:3-6` justifies this with reference to V1 product lock §21.5 ("V1 sizes BUY orders with fractional Kelly (default ½ Kelly)"). **The V1 product lock contradicts the settings-and-credentials intent doc on this default**. T-002 surfaced this; T-061 re-confirms.

## 11. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis (T-046 and similar):

1. **Three settings vocabulary homes, no single UI.** `config.py` env-var surface + `packages/domain/.../settings.py` typed vocab + storage `TradingSettingsRecord` JSON columns. The intent's "grouped by category" UI presupposes a single edit surface that doesn't exist.
2. **Settings prefix mismatch in `.env.example`** (already T-009 finding) — Compose ships bare keys that Pydantic's `env_prefix` doesn't match. Most Category 1 + 3 fields are silently dropped by `extra="ignore"`.
3. **OpenAI integration is vocab-only.** Domain has `OpenAIIntegrationSettings` (`packages/domain/.../settings.py:422-468`) + `ApiBudgetPolicy` template + secret-reference plumbing — but no env-var bridge. Intent specifies OpenAI as the alternative AI provider; reality has only Claude wired.
4. **Anthropic SDK auto-reads `ANTHROPIC_API_KEY`, not `API_CLAUDE_AI_API_KEY`.** The Pydantic field is a presence gate; the SDK transport uses a different env var. Documentation, dev-onboarding, and `.env.example` should reflect both.
5. **PAPER → REAL is architecturally forbidden** at three layers (domain validators, Pydantic defaults, DB CHECK constraints). The intent's `BEVESTIG REAL` typed-confirmation UX is moot in V1. V2 will need to relax 3 layers + add the confirmation flow.
6. **Most Category 3 safety limits are not implemented** — `max_order_value`, `max_orders_per_day`, `trading_halt_master_switch`, `drawdown_circuit_breaker`, predictor retirement / shadow-promotion / speculative-classification thresholds. The Action Draft safety pipeline (`packages/portfolio/.../action_draft_safety.py`) implements per-draft checks but no global persisted limits.
7. **Category 4 monitoring has zero implementation.** No critical-alert email, no event classification, no quiet hours, no delivery channels. The audit-log surface exists (13 `SqlAlchemy*AuditRepository`) but no read-side alerting.
8. **Category 5 audit-backup is a display stub.** `StorageBackupStatus` (`apps/api/.../storage_status.py:56, 136`) surfaces `backup_not_tested` warning but there is no backup configuration, no retention policy, no restore-test reminder.
9. **Kelly fraction collision** — V1 product lock §21.5 says 0.5; settings-and-credentials intent §2 says 0.25 Moderate. Both are locked docs. Resolution required before either can claim authority. Re-confirms T-002 finding.
10. **The 7 UX rules are mostly aspirational.** Rule 3 (secrets never re-displayed) is the only one honoured by code; rule 5 (PAPER→REAL confirmation) is architecturally moot; the other 5 are not implemented.
11. **The `SecretStorageKind` enum doesn't include `OS_KEYRING`.** Intent §7 open question 1 is implicitly pre-empted toward `ENVIRONMENT_VARIABLE` + `LOCAL_GITIGNORED_FILE`. Doctrine §15 may want to lock this explicitly.

## 12. References

- `docs/intent/settings-and-credentials.md` — locked five-category intent (2026-05-26).
- `docs/decisions/0004-settings-and-credentials-structure.md` — ADR accepting the model.
- `docs/intent/_trading-system-doctrine.md` §3, §13, §15 — referenced from the intent.
- `docs/reality/components/api-infrastructure-and-ai.md` §2, §11 — api `Settings` field catalogue + Claude provider detail.
- `docs/reality/components/worker-orchestration-and-scheduling.md` §3 — worker `Settings` field catalogue.
- `docs/reality/components/infra-docker-and-compose.md` §5 — the `.env.example` settings prefix mismatch finding (T-009).
- `docs/reality/components/portfolio-money-and-accounting.md` (T-002) — Kelly fraction discovery.
- `docs/reality/components/stub-packages.md` (T-010) — cross-cutting note that `packages/{ai,audit,risk}/` are README-only stubs while the actual concepts live in `apps/api`, `apps/worker`, `packages/portfolio`, `packages/storage`.
