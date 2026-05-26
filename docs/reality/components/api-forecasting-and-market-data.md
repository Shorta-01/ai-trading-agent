# `apps/api` — forecasting and market data

**Phase:** 1a (reality components)
**Task:** T-005
**Scope:** 19 modules in `apps/api/src/portfolio_outlook_api/` covering forecast routes + sync, market-data adapter factory + readiness + runtime routes + sync, EODHD HTTP client, asset identity (master + listings), the universe registry + scan, the predictor backtest orchestrator, both AI time-series providers, decision-package routes + sync, daily briefing sync, prediction diary sync, and the morning-chain orchestrator (~7063 lines total).

This file is descriptive. Every claim cites `path/to/file.py:NNN`. Non-trivial claims carry 3–10 line excerpts. No verdicts, no gaps, no fix proposals.

## Modules covered

Read-only surfaces (8):
- `forecast_routes.py` — 4 read-only forecast + calibration routes.
- `market_data_runtime_routes.py` — 3 read-only EOD snapshot + provider-call routes.
- `market_data_adapter_factory.py` — single gate point: real EODHD client or `None`.
- `market_data_readiness.py` — readiness response contracts + builders.
- `decision_package_routes.py` — 3 read-only decision-package routes.
- `eodhd_client.py` — stdlib-only EODHD HTTP client.
- `universe_registry.py` — V1 universe set (static Python tuples).
- `morning_chain.py` — orchestrator (Slice 21; stub-grade legs).

Write paths (11):
- `forecast_sync.py` — writes `market_data_bars` + `asset_forecasts`.
- `market_data_sync.py` — writes `market_data_latest_snapshots` + `fx_rate_snapshots`.
- `asset_master.py` — writes `asset_master` + `asset_identifier_aliases` + `source_to_asset_links`.
- `asset_listings.py` — writes `asset_listings`.
- `universe_scan_sync.py` — writes `universe_scan_runs` + `asset_fundamentals_snapshots`.
- `predictor_backtest_orchestrator.py` — writes `predictor_backtest_runs`.
- `anthropic_ts_provider.py` — writes `claude_ai_budget_usage` via shared helper.
- `ai_ts_provider.py` — factory (writes only when routing to the Anthropic provider).
- `decision_package_sync.py` — writes `asset_decision_packages`.
- `daily_briefing_sync.py` — writes `daily_briefings` + `briefing_alerts`.
- `prediction_diary_sync.py` — writes `prediction_diary_entries`.

## `forecast_routes.py` — read-only forecast + calibration

**Path:** `apps/api/src/portfolio_outlook_api/forecast_routes.py` (507 lines)

### Public surface

- `GET /forecast/latest` → `read_latest_forecast` (`:285-288`); response_model `ForecastLatestResponse`.
- `GET /forecast/by-account` → `read_forecasts_by_account` (`:323-328`); response_model `ForecastByAccountResponse`.
- `GET /forecast/day-summary` → `read_forecast_day_summary` (`:394-400`); response_model `ForecastDaySummaryResponse`.
- `GET /calibration/coverage` → `read_calibration_coverage` (`:466-471`); response_model `CalibrationCoverageResponse`.

Pydantic models (`extra="forbid"`): `PerAssetCoverage` (`:51`), `ForecastLatestResponse` (`:67`), `ForecastByAccountRow` (`:102`), `ForecastByAccountResponse` (`:116`), `CalibrationCoverageResponse` (`:125`), `ForecastDaySummaryResponse` (`:137`).

### Collaborators

`SqlAlchemyForecastRepository`, `SqlAlchemyFxRateRepository`, `SqlAlchemyCalibrationDiaryRepository` — all `require_writable=False`. Reads `settings.storage`, `settings.ibkr_account_id_hint`, `settings.forecast_pilot_conids`.

### Notable choices

- **Read-only.** No writes.
- **EUR conversion at display time.** `_serialize_forecast` (`:209-229`) returns the local price as EUR string when the source currency is already EUR; otherwise multiplies by the latest FX, quantising to `Decimal("0.000001")`.
- **Decimal-as-string** throughout `_serialize_forecast` (`:237-252`).
- Storage failure → HTTP 503 with `"Opslag is niet beschikbaar."` (`:44, :155-156`).
- Every response carries `safe_for_action_drafts: Literal[False]` + `safe_for_orders: Literal[False]` at the schema layer (`:98-99, :121-122, :133-134, :148-149`).

```python
# forecast_routes.py:209-229 — EUR conversion + Decimal-as-string
if forecast.currency_local == BASE_CURRENCY:
    p10_eur = str(p10_price_local)
    ...
else:
    fx_row = fx_repo.get_latest(base_currency=forecast.currency_local, quote_currency=BASE_CURRENCY)
    if fx_row is None:
        p10_eur = p50_eur = p90_eur = None
    else:
        p10_eur = str((p10_price_local * fx_row.rate).quantize(Decimal("0.000001")))
```

## `forecast_sync.py` — forecast orchestrator

**Path:** `apps/api/src/portfolio_outlook_api/forecast_sync.py` (450 lines)

### Public surface

- `sync_forecasts(...)` (`:179`) — main orchestrator.
- `serialize_forecast_for_response(record)` (`:404`).
- Helpers: `_build_bar_record` (`:87`), `_build_forecast_record` (`:121`), `_unique_positions` (`:163`).
- Dataclass `ForecastSyncReport` (`:51`).

### Collaborators

Repos via `Protocol`: `_MarketDataBarRepoProtocol` (`:70`), `_AssetForecastRepoProtocol` (`:76`). Imports `BaselineForecast`, `HistoricalBar`, `compute_baseline_forecast`, `BASELINE_FORECAST_MODEL_CODE`, `BASELINE_FORECAST_MODEL_VERSION` from `portfolio_outlook_portfolio`. EODHD wiring via `EodhdHistoricalProvider`, `EodhdBar`, and the typed error hierarchy.

### Notable choices

- **Writes** `MarketDataBarRecord` via `bar_repo.save_market_data_bars` (`:330`) → `market_data_bars`; `AssetForecastRecord` via `forecast_repo.save_asset_forecast` (`:356`) → `asset_forecasts`.
- **Auth/rate-limit errors break early** (`:266, :278`); not-found/generic provider errors continue to the next ticker.
- `forecast.adjusted_close_price or record.close_price` chosen for `HistoricalBar.close_price` to honour corporate actions when available (`:333-339`).
- Module docstring locks every `safe_for_*` to False (`:5-8`).
- Decimal-as-string in `serialize_forecast_for_response` via local `_money` helper (`:408-409, :424-437`).

## `market_data_adapter_factory.py` — fake-data boundary gate

**Path:** `apps/api/src/portfolio_outlook_api/market_data_adapter_factory.py` (55 lines)

### Public surface

`build_market_data_provider(settings, *, http_fetcher=None) -> EodhdClient | None` (`:19`).

### Notable choices

- **Single gate point: real EODHD client or `None`.** Module docstring (`:1-7`) calls out: "`None` means the route handler must report 'not configured' rather than fall back to fake data" — direct AGENTS.md "no fake portfolio data" enforcement at the boundary.
- All four gates must pass (`:38-46`): `market_data_sync_enabled`, `market_data_provider.lower() == "eodhd"`, `eodhd_enabled`, API key present.
- `EodhdAuthError` from missing key swallowed → returns `None` (`:54-55`).

## `market_data_readiness.py` — readiness types + builders

**Path:** `apps/api/src/portfolio_outlook_api/market_data_readiness.py` (376 lines)

### Public surface

- Protocol `ReadinessWatchlistItemLike` (`:10`).
- StrEnums: `ReadinessAssetListingGateStatus` (`:23`), `ReadinessStatus` (`:50`), `ReadinessFreshnessStatus` (`:55`), `ReadinessBlockerCode` (`:60`), `LatestSnapshotStatus` (`:64`).
- Pydantic models: `ReadinessValidationStatus` (`:18`), `ReadinessAssetListingGate` (`:31`), `ReadinessSnapshotMetadata` (`:72`), `ReadinessRow` (`:122`), `ReadinessListResponse` (`:164`), `ReadinessDetailResponse` (`:172`), `LatestSnapshotResponse` (`:177`).
- Builders: `utc_now_iso` (`:213`), `build_readiness_row` (`:217`), `build_readiness_snapshot_metadata` (`:291`), `build_latest_snapshot_response` (`:297`), `build_asset_listing_gate` (`:329`).

### Notable choices

- Locked Dutch text constants enforce the read-only boundary: `READINESS_BOUNDARY_TEXT_NL` (`:94`), `READINESS_NO_RUNTIME_TEXT_NL` (`:100`), `LATEST_SNAPSHOT_HELP_NL` (`:112`).
- `LatestSnapshotResponse` carries Decimal-as-string strings (`last_price`, `bid_price`, etc., `:197-201`).
- Hard-codes `analysis_ready=False`, `suggestions_allowed=False`, `action_drafts_allowed=False` in builder (`:285-287`).

## `market_data_runtime_routes.py` — EOD snapshot routes

**Path:** `apps/api/src/portfolio_outlook_api/market_data_runtime_routes.py` (373 lines)

### Public surface

- `GET /market-data/eod/snapshots/latest` → `read_latest_snapshot` (`:192-196`); response_model `MarketDataLatestSnapshotResponse`.
- `GET /market-data/eod/snapshots/by-account` → `read_snapshots_by_account` (`:245-251`); response_model `MarketDataByAccountResponse`.
- `GET /market-data/provider-calls` → `read_provider_calls` (`:335-341`); response_model `ProviderCallsResponse`.

Pydantic: `MarketDataLatestSnapshotResponse` (`:57`), `MarketDataByAccountRow` (`:75`), `MarketDataByAccountResponse` (`:88`), `ProviderCallRow` (`:99`), `ProviderCallsResponse` (`:113`).

### Collaborators

`SqlAlchemyMarketDataEodSnapshotRepository`, `SqlAlchemyFxRateRepository`, `SqlAlchemyProviderCallAuditRepository`, `SqlAlchemyWatchlistItemSeedRepository` — all `require_writable=False`.

### Notable choices

- **Freshness windows** derived at display time, not stored: `_FRESH_DAYS = 1`, `_STALE_DAYS = 3`, `unavailable` otherwise (`:49-50, :132-143`). Per Task 129 product lock §6.
- `_decimal_str` helper enforces `None | str` boundary (`:146-147`).
- Decimal-as-string on every numeric (`close_local`, `close_eur`, `fx_rate_used`, `day_change_percent`) (`:229, :313, :175-177`).
- EUR fallback: `fx_repo.get_rate(...)` for the exact date, falling back to `get_latest(...)` (`:161-170`).
- 503 raised with `STORAGE_UNAVAILABLE_DETAIL` (`:47, :124-125`).

```python
# market_data_runtime_routes.py:132-143 — freshness windowing
def _freshness_for(as_of_date: date, *, today: date | None = None) -> Freshness:
    actual_today = today or _today()
    delta = (actual_today - as_of_date).days
    if delta <= _FRESH_DAYS:
        return "fresh"
    if delta <= _STALE_DAYS:
        return "stale"
    return "unavailable"
```

## `market_data_sync.py` — EOD + FX persistence orchestrator

**Path:** `apps/api/src/portfolio_outlook_api/market_data_sync.py` (522 lines)

### Public surface

- `IBKR_TO_EODHD_EXCHANGE` mapping (`:49`).
- `PROVIDER_CODE_EODHD = "eodhd"` (`:99`).
- `MarketDataSyncReport` dataclass (`:102`).
- `map_ibkr_exchange_to_eodhd()` (`:134`), `derive_required_fx_pairs()` (`:146`), `build_eodhd_market_snapshot_record()` (`:179`), `build_eodhd_fx_snapshot_record()` (`:227`).
- `sync_market_data_and_fx()` (`:269`) — main orchestrator.

### Collaborators

Protocols `_MarketDataRepoProtocol` (`:124`), `_FxRepoProtocol` (`:130`). Imports `EodhdAuthError`, `EodhdClientError`, `EodhdFxRate`, `EodhdMarketDataProvider`, `EodhdNotFoundError`, `EodhdQuote`, `EodhdRateLimitError`.

### Notable choices

- **Writes** `MarketDataLatestSnapshotRecord` (`:406`) → `market_data_latest_snapshots`; `FxRateSnapshotRecord` (`:473`) → `fx_rate_snapshots`.
- Module docstring: "the orchestrator does not invent values: every persisted row is grounded in either an EODHD response or an explicit `unknown_exchange` / `provider_error` failure record" (`:1-9`).
- 35+ IBKR → EODHD exchange mappings hard-coded (`:49-96`); unknown exchange → skipped with `"unknown_exchange"` reason.
- All `safe_for_*` flags stay False at record construction (`:191`).
- FX validation: `usable_rate = Decimal("0")` and `validation_status="invalid"` when rate ≤ 0 or missing (`:240-249`).
- Auth + rate-limit errors break early (`:347, :371, :431, :442`); per-asset `EodhdClientError` continues the batch (`:372-382`).

```python
# market_data_sync.py:240-266
if rate_value is None or rate_value <= 0:
    validation_status = "invalid"
    reason_code = "missing_rate" if rate_value is None else "non_positive_rate"
    freshness = "unusable"
    usable_rate = Decimal("0")
else:
    validation_status = "valid"
    ...
return FxRateSnapshotRecord(
    ...
    rate=usable_rate,
    metadata_json={"previous_close": str(rate.previous_close)} if rate.previous_close else None,
)
```

## `eodhd_client.py` — minimal stdlib HTTP client

**Path:** `apps/api/src/portfolio_outlook_api/eodhd_client.py` (505 lines)

### Public surface

- Dataclasses: `EodhdHttpResponse` (`:49`), `EodhdQuote` (`:57`), `EodhdFxRate` (`:75`), `EodhdBar` (`:88`), `EodhdFundamentals` (`:101`).
- Error hierarchy: `EodhdClientError` (`:126`), `EodhdAuthError` (`:130`), `EodhdNotFoundError` (`:134`), `EodhdRateLimitError` (`:138`).
- `_DefaultHttpFetcher` (`:142`); `EodhdClient` class (`:163`) with `fetch_quote` (`:181`), `fetch_fx_rate` (`:192`), `fetch_eod_bars` (`:208`), `fetch_fundamentals` (`:233`).
- Parsers `_parse_quote`/`_parse_fx_rate`/`_parse_eod_bars`/`_parse_fundamentals` (`:324, :357, :375, :418`).
- Protocols `EodhdMarketDataProvider` (`:488`), `EodhdHistoricalProvider` (`:496`).

### Collaborators

None outside stdlib + Decimal.

### Notable choices

- All numeric values parsed via `_decimal_or_none` (`:277`) — accepts int/float/str; treats `"NA"`/`"N/A"`/`"NULL"`/`"NONE"` as None.
- HTTP error mapping: 401/403 → `EodhdAuthError`, 404 → `EodhdNotFoundError`, 429 → `EodhdRateLimitError`, ≥500 → `server_error`, ≥400 → `http_error` (`:261-270`).
- Fundamentals: percentage normalisation in `_percent_or_none` (`:404-415`) — treats `|x| ≤ 1.5` as fraction and multiplies by 100. SHA-256 hash of canonical JSON for snapshot dedup (`:468-469`).
- Network errors → `EodhdClientError("network_error: ...")` (`:154-155`).
- API key empty at construction → `EodhdAuthError("missing_api_key")` (`:174-175`).

```python
# eodhd_client.py:259-274
def _get(self, url: str) -> object:
    response = self._fetch(url, self._timeout)
    if response.status_code in (401, 403):
        raise EodhdAuthError(f"auth_error: status={response.status_code}")
    if response.status_code == 404:
        raise EodhdNotFoundError(f"not_found: status={response.status_code}")
    if response.status_code == 429:
        raise EodhdRateLimitError("rate_limited")
    if response.status_code >= 500:
        raise EodhdClientError(f"server_error: status={response.status_code}")
```

## `asset_master.py` — asset-identity CRUD

**Path:** `apps/api/src/portfolio_outlook_api/asset_master.py` (288 lines)

### Public surface (routes)

- `POST /assets/master` → `create_asset` (`:62-63`)
- `GET /assets/master` → `list_assets` (`:190-191`)
- `GET /assets/master/search?q=` → `search_assets` (`:129-130`)
- `GET /assets/master/{asset_id}` → `get_asset` (`:176-177`)
- `POST /assets/master/{asset_id}/aliases` → `create_alias` (`:208-209`)
- `GET /assets/master/{asset_id}/aliases` → `list_aliases` (`:229-230`)
- `POST /assets/master/source-links` → `create_source_to_asset_link` (`:250-251`)
- `GET /assets/master/{asset_id}/source-links` → `list_source_to_asset_links` (`:280-281`)

### Notable choices

- **Writes** via `SqlAlchemyResearchSourceArchiveRepository`: `AssetMasterRecord` (`:91`) → `asset_master`; `AssetIdentifierAliasRecord` (`:222`) → `asset_identifier_aliases`; `SourceToAssetLinkRecord` (`:268`) → `source_to_asset_links`.
- Every saved record carries `safe_to_use_for_suggestions=False`, `blocks_suggestions=True` (`:87-88, :262-263`).
- Storage failure → HTTP 503 (`:29-38`).

## `asset_listings.py` — listing CRUD

**Path:** `apps/api/src/portfolio_outlook_api/asset_listings.py` (142 lines)

### Public surface (routes)

- `POST /assets/listings` → `create_asset_listing` (`:55-56`)
- `GET /assets/listings` → `list_asset_listings` (`:112-113`)
- `GET /assets/listings/search?q=` → `search_asset_listings` (`:123-124`)
- `GET /assets/listings/{listing_id}` → `get_asset_listing` (`:134-135`)

### Notable choices

- Every created listing has hard-coded `safe_to_use_for_market_data=False`, `safe_to_use_for_analysis=False`, `safe_to_use_for_suggestions=False` and mirror `blocks_*` flags True (`:84-89`).
- `listing_status="reference_only"`, `validation_status="unvalidated"` (`:74-75`).
- Writes `AssetListingRecord` via `repo.save_asset_listing` (`:95`) → `asset_listings`.

## `universe_registry.py` — V1 universe data

**Path:** `apps/api/src/portfolio_outlook_api/universe_registry.py` (555 lines)

### Public surface

- `UniverseEntry` dataclass with `symbol`, `eodhd_symbol`, `index_code`, `sector`, `country_code` (`:40-46`).
- Tuples `BEL20` (`:61`), `AEX` (`:87`), `CAC40` (`:118`), `DAX40` (`:164`), `SP100` (`:210`), `NASDAQ100_EXTRA` (`:318`), `EU600_EXTRA` (`:398`), `ALL_5K_EXTRA` (`:452`).
- Set codes `UNIVERSE_SET_SP500`, `UNIVERSE_SET_EU600`, `UNIVERSE_SET_ALL_5K`, `LOCKED_UNIVERSE_SETS`; `DEFAULT_UNIVERSE_SET = "SP500"` (`:50-56`).
- `locked_universe(set_code=DEFAULT_UNIVERSE_SET)` (`:505`) — deduplicated tuple; raises `ValueError` for unknown set_code.
- `universe_by_index(index_code, *, set_code=DEFAULT_UNIVERSE_SET)` (`:528`).

### Notable choices

- Dedup by `eodhd_symbol` so the scan never hits EODHD twice for the same symbol (`:492-502`).
- Aggregation `SP500 ⊂ EU600 ⊂ ALL_5K` (`:466-483`).
- Comment defers full 5K materialisation to a post-V1.1 widening via EODHD bulk-list endpoint (`:25-30, :396, :450-451`).

## `universe_scan_sync.py` — daily scan orchestrator

**Path:** `apps/api/src/portfolio_outlook_api/universe_scan_sync.py` (379 lines)

### Public surface

- `UniverseScanReport` dataclass (`:54`).
- `scan_universe(...)` (`:174`) — main orchestrator with knobs `universe_set`, `cache_ttl_hours`, `max_tickers`, `triggered_by`.
- `build_universe_fundamentals(snapshots)` (`:364`) — translates persisted snapshots to QVM predictor input.

### Notable choices

- **Writes** `UniverseScanRunRecord` initial + final (`:235, :343`) → `universe_scan_runs`; `AssetFundamentalsSnapshotRecord` (`:295`) → `asset_fundamentals_snapshots`.
- Cache TTL: looks up `get_latest_snapshot_for_symbol` and reuses if `fetched_at >= cache_cutoff` (`:215-219, :247-261`).
- `_return_pct(bars, days_back)` favours `adjusted_close` over `close_price` (`:101-102`).
- Caps batch via `max_tickers` (`:213`); per-ticker failures recorded in `failures` list, never aborts batch.

## `predictor_backtest_orchestrator.py` — walk-forward orchestrator

**Path:** `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py` (411 lines)

### Public surface

- `LOCKED_MODEL_CODES = frozenset({"baseline_gbm", "momentum_v1", "mean_reversion_v1"})` (`:41-47`).
- `SKIPPED_QVM_REASON`, `SKIPPED_AI_TS_REASON` (`:57-58`).
- `BacktestOrchestratorResult` dataclass (`:81`).
- `run_backtest_for_symbol(...)` (`:199`).
- `serialize_backtest_run_record(record)` (`:367`).

### Notable choices

- **Writes** `PredictorBacktestRunRecord` (initial `running`, then `succeeded`/`skipped`/`failed`) (`:268, :284, :311, :355`) → `predictor_backtest_runs`.
- **QVM + AI TS deferred at this layer.** Module docstring (`:48-54`) and `_build_predictor_or_skip` return `(None, blocker)` for `qvm_factor_v1` (`:158-164`) and `ai_ts_v1` (`:165-166`). Routes accept them but produce a `skipped` audit row.
- Brier / hit-rate / Sharpe quantised to 6 decimals (`:338-350`).
- Decimal-as-string in `serialize_backtest_run_record` (`:386-395`).

## `anthropic_ts_provider.py` — LLM-as-forecaster provider

**Path:** `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py` (350 lines)

### Public surface

- Constants `PROVIDER_CODE = "anthropic_claude"` (`:47`), `DEFAULT_MODEL_NAME = "claude-haiku-4-5-20251001"` (`:48`), `TS_TOOL_NAME = "emit_ts_forecast"` (`:49`).
- `SYSTEM_PROMPT_NL` (`:52`); `TS_TOOL_SCHEMA` (`:65`).
- `AnthropicTsModelProvider` class (`:214`) with `forecast(inputs) -> TsModelProviderResult | TsModelProviderUnavailable` (`:250`).
- Helpers: `_extract_tool_call` (`:112`), `_validate_payload` (`:137`), `_build_messages_payload` (`:169`).

### Notable choices

- **Writes** to `claude_ai_budget_usage` via `persist_call_cost(...)` (`:312`) — shared with explanation calls via `call_kind="ts_forecast"`.
- Returns `TsModelProviderUnavailable` rather than raising on soft errors: `budget_exceeded`, `provider_error`, validation failures (`:266-297`).
- **Cache-control on system prompt** (`:194-196`) — `"cache_control": {"type": "ephemeral"}` for prompt-caching savings.
- `tool_choice` forces calling the locked tool (`:209`).
- `_validate_payload` enforces `p10 ≤ p50 ≤ p90`, `prob_gain ∈ [0,1]`, `confidence_score ∈ [0,1]`, all required fields present (`:137-166`).
- Truncates bars to last 60 for token-budget reasons (`:175-178`).

### AI scope classification

**Case B — LLM-as-forecaster.** The LLM directly emits price quantiles (p10/p50/p90), `expected_return_pct`, `prob_gain`, and `confidence_score` (`:65-85, :329-340`). Result feeds the ensemble via `AiTsPredictor` (Slice 18) as the "AI vote", not as a feature for a deterministic forecaster.

Per `docs/intent/ai-usage.md:112-116`: Case B → "**remove from the ensemble.** This is not a mainstream-safe pattern for retail trading." This module is the canonical Case B observation for the AI-in-forecasting boundary.

```python
# anthropic_ts_provider.py:65-85 — the LLM-as-forecaster tool schema
TS_TOOL_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "p10_price": {"type": "number"},
        "p50_price": {"type": "number"},
        "p90_price": {"type": "number"},
        "prob_gain": {"type": "number", "minimum": 0, "maximum": 1},
        "expected_return_pct": {"type": "number"},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "explanation_nl": {"type": "string"},
    },
    "required": ["p10_price", "p50_price", "p90_price", "prob_gain",
                 "expected_return_pct", "confidence_score", "explanation_nl"],
}
```

## `ai_ts_provider.py` — provider factory + classical stub

**Path:** `apps/api/src/portfolio_outlook_api/ai_ts_provider.py` (284 lines)

### Public surface

- Constants `STUB_PROVIDER_CODE = "stub"`, `STUB_MODEL_NAME = "empirical_quantile_drift"`, `STUB_MODEL_VERSION = "v1"` (`:33-35`).
- `StubTsModelProvider` class (`:58`) with `forecast(inputs) -> TsModelProviderResult` (`:85`).
- `build_ts_model_provider(runtime_settings, *, budget_repo=None, invoked_from_scheduler=False)` (`:168`).

### Notable choices

- **Stub computes pure deterministic statistics**: log-returns → mean drift `mu` → population SD `sigma` → projects onto horizon as `mu*horizon` drift + `sigma*sqrt(horizon)` SD → derives p10/p50/p90 via z-scores ±1.2815 (`:128-145`). No LLM, no ML training.
- Confidence capped at 0.85 via `0.4 + 0.45 * min(1.0, len(returns)/250.0)` (`:147-149`).
- Factory gates: `ai_ts_predictor_enabled`, provider code matches, real_client flag, API key present, budget_repo supplied, scheduler invocation if `daily_only` set (`:194-246`).
- `timesfm` declared but unimplemented → `"timesfm_not_implemented"` (`:257-268`).

### AI scope classification

**Case A — classical ML model labelled "AI"** for the stub. Provider code `"stub"` / model name `"empirical_quantile_drift"` (`:33-34`) — pure deterministic statistics, no LLM. Per `docs/intent/ai-usage.md:106-110`: Case A → "**rename.** A classical ML predictor remains a Predictor."

The module itself is a *factory* that also routes to the Case B implementation (`AnthropicTsModelProvider`) — the routing layer itself isn't a case.

```python
# ai_ts_provider.py:128-145 — the stub is classical statistics, not AI
mu = statistics.fmean(returns)
sigma = statistics.pstdev(returns)
horizon = inputs.horizon_trading_days
horizon_drift = mu * horizon
horizon_sd = sigma * math.sqrt(horizon) if sigma > 0 else 0.0001

current = float(inputs.current_price)
p10_log = horizon_drift + horizon_sd * (-1.2815515655446004)
p50_log = horizon_drift
p90_log = horizon_drift + horizon_sd * 1.2815515655446004
```

## `decision_package_routes.py` — read-only DP routes

**Path:** `apps/api/src/portfolio_outlook_api/decision_package_routes.py` (308 lines)

### Public surface

- `GET /decision-package/latest` → `read_latest_decision_package` (`:192-198`); response_model `DecisionPackageResponse`.
- `GET /decision-package/chain` → `read_decision_package_chain` (`:241-248`); response_model `DecisionPackageChainResponse`.
- `GET /decision-package/{decision_package_id}` → `read_decision_package` (`:276-280`).

**Route ordering note** (`:181-183`): `/latest` and `/chain` are registered before `/{id}` to avoid the path-param catch-all.

### Notable choices

- 50-row hard cap on chain via `Query(default=20, ge=1, le=50)` (`:247`).
- Decimal-as-string throughout `_serialize_package` (`:116-178`).
- `safe_for_action_drafts: Literal[False]` and `safe_for_orders: Literal[False]` at schema layer (`:98-99, :108-109`).
- Account fallback via `_configured_account_id()` reads `settings.ibkr_account_id_hint` (`:184-189`).

## `decision_package_sync.py` — DP composition orchestrator

**Path:** `apps/api/src/portfolio_outlook_api/decision_package_sync.py` (549 lines)

### Public surface

- `DecisionPackageSyncReport` dataclass (`:54`).
- `build_research_summary_by_symbol(...)` (`:88`).
- `build_decision_package_record(context, *, risk_profile, generated_at, valid_until)` (`:220`) — pure function.
- `sync_decision_packages(...)` (`:355`) — main orchestrator.
- `serialize_decision_package_for_response(record)` (`:481`).
- Helpers `_compute_content_hash` (`:140`), `_build_audit_links` (`:145`), `_build_gate_outcomes` (`:170`).

### Notable choices

- **Writes** `AssetDecisionPackageRecord` (`:434`) → `asset_decision_packages`.
- **Content-hash for immutability**: `content_hash = sha256(canonical_json(...))` over audit-relevant fields (`:140-142, :263`).
- `safe_for_action_drafts: False`, `safe_for_orders: False`, `safe_for_broker_submission: False` always (`:541-543`).
- Status mapping: `"blocked"` if suggestion blocked, `"control_needed"` if control_needed, else `"ready"` (`:341-345`).
- Ready suggestions missing forecast or market evidence → skipped with `incomplete_evidence_chain` (`:397-410`).

```python
# decision_package_sync.py:140-142, :244-263
def _compute_content_hash(payload: dict[str, object]) -> str:
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
...
hash_payload: dict[str, object] = {
    "ibkr_conid": suggestion.ibkr_conid,
    "symbol": suggestion.symbol,
    "currency": suggestion.currency,
    "risk_profile": risk_profile,
    ...
    "research_blocking_reason": research_summary.research_blocking_reason,
}
content_hash = _compute_content_hash(hash_payload)
```

## `daily_briefing_sync.py` — Dutch briefing orchestrator

**Path:** `apps/api/src/portfolio_outlook_api/daily_briefing_sync.py` (329 lines)

### Public surface

- `DailyBriefingReport` dataclass (`:47`).
- `generate_daily_briefing(...)` (`:170`).
- `serialize_briefing_for_response(record, alerts=())` (`:274`).
- Adapters `_to_position_inputs` (`:70`), `_to_suggestion_inputs` (`:84`), `_to_package_inputs` (`:99`), `_to_draft_inputs` (`:113`), `_to_diary_inputs` (`:128`), `_to_event_inputs` (`:142`), `_sum_cash` (`:158`).

### Notable choices

- **Writes** `DailyBriefingRecord` via `repo.upsert_daily_briefing` (`:234`) → `daily_briefings`; `BriefingAlertRecord` via `repo.save_briefing_alert` (`:237`) → `briefing_alerts`. Existing alerts deleted first (`:235`).
- **AI never authors the briefing** — module docstring (`:9`); calls deterministic `compute_daily_briefing` from `portfolio_outlook_portfolio`.
- Critical-event filter: only `severity == "critical"` events pass through `_to_event_inputs` (`:154`).
- Boundary catch on persistence → returns `failed` report rather than raising (`:251-261`).
- `safe_for_action_drafts: False`, `safe_for_orders: False` (`:320-321`).

## `prediction_diary_sync.py` — diary outcome orchestrator

**Path:** `apps/api/src/portfolio_outlook_api/prediction_diary_sync.py` (312 lines)

### Public surface

- Horizon constants `HORIZON_1D_DAYS=1`, `HORIZON_1W_DAYS=7`, `HORIZON_1M_DAYS=30` (`:41-43`).
- `PredictionDiaryReport` dataclass (`:46`).
- `evaluate_prediction_diary(...)` (`:164`).
- `serialize_prediction_diary_entry_for_response(record)` (`:265`).
- Helpers `_index_bars_by_date` (`:66`), `_realised_price_at` (`:84`), `_build_entry` (`:100`).

### Notable choices

- **Writes** `PredictionDiaryEntryRecord` via `repo.upsert_prediction_diary_entry` (`:224`) → `prediction_diary_entries`. Upserted by `suggestion_id`.
- **AI never assigns the outcome label** — module docstring (`:6-8`); the realised-price look-back walks back ≤7 calendar days from the target horizon to handle weekends/holidays (`:88-97`).
- Skips suggestions without a linked forecast or whose forecast isn't present (`:186-204`).
- Decimal-as-string serialisation with `None`-guards on every realised value (`:280-302`).
- `safe_for_self_learning: False`, `safe_for_model_retraining: False` (`:310-311`) — diary is for human review only.

## `morning_chain.py` — chain orchestrator (Slice 21 stub-grade)

**Path:** `apps/api/src/portfolio_outlook_api/morning_chain.py` (368 lines)

### Public surface

- Leg constants `LEG_MARKET_DATA_SYNC`, `LEG_FORECAST_SYNC`, `LEG_SUGGESTION_SYNC`, `LEG_DECISION_PACKAGE_SYNC`, `LEG_ACTION_DRAFT_SYNC`, `LEG_DAILY_BRIEFING_SYNC` (`:34-39`); `MORNING_CHAIN_LEG_NAMES` tuple (`:42`).
- Status constants `LEG_STATUS_SUCCEEDED`/`_SKIPPED`/`_FAILED` (`:52-54`); `CHAIN_STATUS_SUCCEEDED`/`_FAILED` (`:57-58`).
- `MorningChainLegOutcome` dataclass (`:61`) with `__post_init__` validation (`:77-91`).
- `MorningChainResult` dataclass (`:94`).
- `MorningChainFailed` exception (`:109`).
- `run_morning_chain(*, legs)` (`:128`).
- `build_scheduler_chain_callable(*, legs_factory)` (`:176`).
- `build_default_morning_chain_legs(runtime_settings)` (`:224`).
- `serialize_morning_chain_result(result)` (`:322`).

### Notable choices

- **Pure orchestrator** — no storage imports. `build_scheduler_chain_callable` raises `MorningChainFailed` (`:198`) so the caller's audit row captures the failure.
- Skipped legs (disabled in config) do not stop the chain (`:128-141`).
- Per-leg exceptions caught and reshaped to a `failed` outcome with stable code `leg_callable_raised` (`:151-157`).
- **Slice 21 stub-grade legs.** Module docstring (`:230-235`) calls out that the default-leg implementations are intentionally pass-through stubs — the real session-bound pipeline lands in Slice 22.
- `safe_for_action_drafts: False`, `safe_for_orders: False` on serialised result (`:342-343`).

## Route catalogue (consolidated)

| Method | Path | Handler | Source |
|---|---|---|---|
| GET | `/forecast/latest` | `read_latest_forecast` | `forecast_routes.py:285` |
| GET | `/forecast/by-account` | `read_forecasts_by_account` | `forecast_routes.py:323` |
| GET | `/forecast/day-summary` | `read_forecast_day_summary` | `forecast_routes.py:394` |
| GET | `/calibration/coverage` | `read_calibration_coverage` | `forecast_routes.py:466` |
| GET | `/market-data/eod/snapshots/latest` | `read_latest_snapshot` | `market_data_runtime_routes.py:192` |
| GET | `/market-data/eod/snapshots/by-account` | `read_snapshots_by_account` | `market_data_runtime_routes.py:245` |
| GET | `/market-data/provider-calls` | `read_provider_calls` | `market_data_runtime_routes.py:335` |
| GET | `/decision-package/latest` | `read_latest_decision_package` | `decision_package_routes.py:192` |
| GET | `/decision-package/chain` | `read_decision_package_chain` | `decision_package_routes.py:241` |
| GET | `/decision-package/{decision_package_id}` | `read_decision_package` | `decision_package_routes.py:276` |
| POST | `/assets/master` | `create_asset` | `asset_master.py:62` |
| GET | `/assets/master` | `list_assets` | `asset_master.py:190` |
| GET | `/assets/master/search` | `search_assets` | `asset_master.py:129` |
| GET | `/assets/master/{asset_id}` | `get_asset` | `asset_master.py:176` |
| POST | `/assets/master/{asset_id}/aliases` | `create_alias` | `asset_master.py:208` |
| GET | `/assets/master/{asset_id}/aliases` | `list_aliases` | `asset_master.py:229` |
| POST | `/assets/master/source-links` | `create_source_to_asset_link` | `asset_master.py:250` |
| GET | `/assets/master/{asset_id}/source-links` | `list_source_to_asset_links` | `asset_master.py:280` |
| POST | `/assets/listings` | `create_asset_listing` | `asset_listings.py:55` |
| GET | `/assets/listings` | `list_asset_listings` | `asset_listings.py:112` |
| GET | `/assets/listings/search` | `search_asset_listings` | `asset_listings.py:123` |
| GET | `/assets/listings/{listing_id}` | `get_asset_listing` | `asset_listings.py:134` |

**22 routes total.** Read-only forecasting/market-data/decision-package routes use HTTP 503 + `"Opslag is niet beschikbaar."` on storage failure; asset-master/listings routes use HTTP 503 variants.

## Storage write-path map

| Repository | Tables | Module |
|---|---|---|
| `bar_repo.save_market_data_bars` | `market_data_bars` | `forecast_sync.py:330` |
| `forecast_repo.save_asset_forecast` | `asset_forecasts` | `forecast_sync.py:356` |
| `market_repo.save_latest_market_data_snapshot` | `market_data_latest_snapshots` | `market_data_sync.py:406` |
| `fx_repo.save_fx_rate_snapshot` | `fx_rate_snapshots` | `market_data_sync.py:473` |
| `SqlAlchemyResearchSourceArchiveRepository.save_asset_master_record` | `asset_master` | `asset_master.py:91` |
| `…save_asset_identifier_alias` | `asset_identifier_aliases` | `asset_master.py:222` |
| `…save_source_to_asset_link` | `source_to_asset_links` | `asset_master.py:268` |
| `…save_asset_listing` | `asset_listings` | `asset_listings.py:95` |
| `scan_repo.save_run` / `update_run` | `universe_scan_runs` | `universe_scan_sync.py:235, :343` |
| `snapshot_repo.save_snapshot` | `asset_fundamentals_snapshots` | `universe_scan_sync.py:295` |
| `backtest_repo.save_backtest_run` / `update_backtest_run` | `predictor_backtest_runs` | `predictor_backtest_orchestrator.py:242, :268, :284, :311, :355` |
| `persist_call_cost(...)` (via `claude_ai_budget`) | `claude_ai_budget_usage` | `anthropic_ts_provider.py:312` |
| `repo.save_asset_decision_package` | `asset_decision_packages` | `decision_package_sync.py:434` |
| `repo.upsert_daily_briefing` | `daily_briefings` | `daily_briefing_sync.py:234` |
| `repo.delete_alerts_for_briefing` + `save_briefing_alert` | `briefing_alerts` | `daily_briefing_sync.py:235, :237` |
| `repo.upsert_prediction_diary_entry` | `prediction_diary_entries` | `prediction_diary_sync.py:224` |

Read-only modules: `forecast_routes.py`, `market_data_runtime_routes.py`, `decision_package_routes.py`, `market_data_readiness.py`, `morning_chain.py`, `eodhd_client.py`, `universe_registry.py`. All use `require_writable=False` on the `StorageConnectionProvider.checked_connection(...)` context manager.

## Decimal-as-string boundary

Every `Decimal` that crosses an API or serialisation boundary is wrapped in `str(...)`. The full catalogue:

- **`forecast_routes.py`** `_serialize_forecast` (`:209-252`), `read_forecasts_by_account` (`:375-376`), `read_calibration_coverage` (`:491-503`).
- **`forecast_sync.py`** `serialize_forecast_for_response` (`:404-446`) via local `_money(value) -> str(value)`.
- **`market_data_runtime_routes.py`** `_decimal_str` (`:146-147`); `_fx_join` returns `(str|None, str|None, str|None)` (`:156-178`); `read_latest_snapshot` (`:229`); `read_snapshots_by_account` (`:313`).
- **`market_data_sync.py`** `build_eodhd_fx_snapshot_record` (`:265`) — `metadata_json={"previous_close": str(...)}`.
- **`predictor_backtest_orchestrator.py`** `serialize_backtest_run_record` (`:386-395`).
- **`decision_package_routes.py`** `_serialize_package` (`:129-156`).
- **`decision_package_sync.py`** `_decimal_or_none_str` (`:136-137`); `serialize_decision_package_for_response` (`:494-525`).
- **`daily_briefing_sync.py`** `serialize_briefing_for_response` (`:286-291`).
- **`prediction_diary_sync.py`** `serialize_prediction_diary_entry_for_response` (`:280-302`).

AGENTS.md "no fake portfolio data" enforcement at the boundary:

- `market_data_adapter_factory.py:1-7, :38-46` — explicit comment "`None` means the route handler must report 'not configured' rather than fall back to fake data."
- `market_data_sync.py:1-9` — "the orchestrator does not invent values: every persisted row is grounded in either an EODHD response or an explicit `unknown_exchange` / `provider_error` failure record."
- Cluster-wide: every persisted record carries `safe_for_action_drafts` / `safe_for_orders` / `safe_for_analysis` / `safe_for_suggestions` hard-False at construction time.

## AI scope classification

Two AI providers exist in this cluster:

- **`anthropic_ts_provider.py` → Case B (LLM-as-forecaster).** Claude is invoked via tool-use with a JSON schema that forces it to emit p10/p50/p90 prices, prob_gain, expected_return_pct, confidence_score (`:65-85`). Result feeds the ensemble. Per `docs/intent/ai-usage.md:112-116`: "**remove from the ensemble**." Canonical Case B observation for T-015 / T-023 reality.
- **`ai_ts_provider.py:StubTsModelProvider` → Case A (classical ML labelled "AI").** Deterministic statistics (drift/variance projection with z-scores ±1.2815, `:128-145`). Provider code `"stub"` / model `"empirical_quantile_drift"`. Per `docs/intent/ai-usage.md:106-110`: "**rename**. A classical ML predictor remains a Predictor."
- **`ai_ts_provider.py:build_ts_model_provider`** is a routing factory: `"stub"` → Case A; `"anthropic_claude"` → Case B; `"timesfm"` declared but unimplemented (`:257-268`).

**No Case C** in this cluster: no LLM produces a structured feature consumed by a deterministic forecaster.

## Cross-cutting observations

1. **Storage gating is uniform.** Every route repeats the four-line `storage.enabled` + `storage.database_url` → `StorageConnectionProvider(...)` → `checked_connection(require_writable=...)` → catch `StorageConnectionError` → 503 pattern. Dutch detail consistent: `"Opslag is niet beschikbaar."` for forecast/market-data/DP; `"Opslag is niet verbonden. ..."` for asset-identity surfaces.
2. **Pydantic v2 with `extra="forbid"`.** All response models in `forecast_routes.py`, `market_data_runtime_routes.py`, `decision_package_routes.py` use `ConfigDict(extra="forbid")`; `Literal[False]` defaults on safety booleans put the contract in the schema.
3. **EUR conversion at display time, never stored.** Both `market_data_runtime_routes.py:21-22` (Task 129 §5) and `forecast_routes.py:207-229` compute EUR on the fly. Storage never co-mingles local + EUR.
4. **Append-only / immutable artefacts.** DPs have a `content_hash` (`decision_package_sync.py:140-142, :263, :278`); forecasts get a fresh `forecast_id = forecast_{uuid4().hex}` per run; briefings upsert with alerts delete+re-save; diary entries upsert by `suggestion_id`.
5. **Orchestrator pattern.** `*_sync.py` modules are pure orchestrators taking `Protocol`-typed repositories and pure-Python compute functions (`portfolio_outlook_portfolio`). No FastAPI imports — called from routes elsewhere or from the morning-chain scheduler.
6. **Universe registry is static Python.** `universe_registry.py` codifies the V1 universe in `Final[tuple[UniverseEntry, ...]]` constants; locked sets via tuple concatenation. Full 5K materialisation deferred post-V1.1.
7. **Morning chain is intentionally stub-grade** (Slice 21). Real session-bound pipeline lands in Slice 22.
8. **The `claude_ai_budget` boundary is shared** between explanations (out of scope) and TS forecasts (`anthropic_ts_provider.py:312`); same table, different `call_kind` discriminator. Monthly cap is shared.

## Open questions / uncertainty

- `anthropic_ts_provider.py` is in active use as a Case B LLM-forecaster despite the doctrine's locked Case B response ("remove from the ensemble"). Whether removal is queued for Phase 4 or whether the doctrine is in tension with V1.1 Slice 30 is out of scope for this Phase 1a doc.
- `ai_ts_provider.py:StubTsModelProvider` lives in a module named "ai_ts_provider" but contains zero AI. Whether the module should be renamed (Case A response) is a Phase 4 decision.
- `predictor_backtest_orchestrator.py` accepts QVM + AI TS model codes but always returns `skipped` for them (`:158-166`). Whether the API surface should reject those codes outright or whether the skip is intentional staging is out of scope here.
- `morning_chain.py` ships stub-grade legs (Slice 21). The actual session-bound chain wiring is Slice 22 territory — Phase 1c gap analysis will assess.
- `universe_registry.py` defers ALL_5K materialisation to a post-V1.1 widening (`:25-30`). The EODHD bulk-list endpoint integration is not yet wired.
