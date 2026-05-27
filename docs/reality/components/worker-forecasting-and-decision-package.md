# Reality — worker forecasting and decision-package

**Scope.** The worker's deterministic forecasting + Decision Package pipeline: the 5-file `forecasting/` sub-package, the 3-file `decision_package/` sub-package, the cross-asset `market_data_step`, and the `providers/eodhd` HTTP client.

Sibling docs cover the rest of the worker:

- `docs/reality/components/worker-orchestration-and-scheduling.md` — entry point, settings, scheduler, single-flight lock, IBKR gateway, storage readiness, starter watchlist.
- `docs/reality/components/worker-actions-and-reconciliation.md` — action drafts, IBKR submission cluster, reconciliation passes A/B/C.

Intent reference: `docs/decisions/0003-forecast-engine-architecture.md` (locked ADR).

## In-scope modules

All paths under `apps/worker/src/portfolio_outlook_worker/`.

| Module | Role |
|---|---|
| `forecasting/asset_universe_resolver.py` (135 lines) | union of (confirmed watchlist) + (held positions) for a single account |
| `forecasting/calibration_step.py` (179 lines) | per-forecast realized-vs-band hit_status (06:00 pre_briefing only) |
| `forecasting/forecasting_step.py` (446 lines) | per-asset bootstrap forecast + label + persistence |
| `forecasting/historical_bootstrap.py` (149 lines) | block-bootstrap math (numpy float64 inside, Decimal at outputs) |
| `forecasting/label_translator.py` (142 lines) | locked 6-label vocabulary |
| `market_data_step.py` (203 lines) | per-asset EOD + per-currency FX sync via EODHD |
| `providers/eodhd.py` (415 lines) | HTTP client — only `/eod/{sym}.{exch}` and `/eod/{base}{quote}.FOREX` |
| `decision_package/composer.py` (572 lines) | pure-function composer + SHA-256 content-addressed hash chain |
| `decision_package/dutch_explanation_template.py` (144 lines) | locked Dutch f-string template — no AI |
| `decision_package/orchestration.py` (191 lines) | per-run iteration + persistence |

## 1. Intent (ADR 0003)

Status `accepted`, Phase P1, dated 2026-05-26 (`docs/decisions/0003-forecast-engine-architecture.md:3-5`). Locked decisions (verbatim):

- **"Seven predictors retained for v1. Simplification deferred to Phase 4 after gap-analysis verdict."** (`:25`)
- **"Single 20 trading day horizon (~ 1 month). Multi-horizon is a Phase 4 candidate."** (`:26`)
- **"Weighted-average-by-historical-accuracy ensemble with a 10% weight floor and 40% ceiling. Strong predictor disagreement reduces combined confidence by design."** (`:27`)
- **"Mandatory calibration correction layer with yellow / red on system-health for per-predictor / ensemble drift. Red ensemble drift stops new suggestion generation but keeps existing forecasts visible."** (`:28`)
- **"EODHD All-In-One data tier required."** (`:29`)

Rejected alternatives: trim-to-three before Phase 1 (`:32`), multi-horizon ensembles in v1 (`:33`), simple unweighted average ensemble (`:34`). Consequences: gap-analysis lives in T-046 (`:38`); the 10%/40% bound is a hard constraint future predictor work must respect (`:39`); Phase 4 queue includes predictor-set simplification review, multi-horizon evaluation, regime detection, survivorship-bias correction (`:40`).

The ADR makes **no** statement about an 8-bucket label vocabulary. The Decimal-as-string boundary is not asserted in the ADR — it is enforced in the code (see §§5, 8, 9 below).

### Intent-vs-reality gap (surfaced for Phase 1c)

**This is the single biggest intent-vs-reality gap in the worker.**

- **Predictor count.** ADR locks "seven predictors retained for v1" (`:25`). The worker ships **one** — `historical_bootstrap_v1` — and no other predictor module exists in `apps/worker/src/portfolio_outlook_worker/forecasting/` (`forecasting_step.py:48-55` shows the sole import; `:349, :406` show the sole `method="historical_bootstrap_v1"` stamp).
- **Ensemble combiner.** ADR locks a weighted-average ensemble with a 10%/40% bound (`:27`). The worker has **no ensemble combiner** in this cluster — `forecasting_step.py` calls `compute_historical_bootstrap_forecast` once per asset and persists one `ForecastEntry` row (`forecasting_step.py:278-285, :341-366`).
- **Calibration correction layer.** ADR locks "mandatory calibration correction layer" with per-predictor + ensemble drift (`:28`). The worker has a **per-forecast** realized-vs-band hit_status calibration only (`calibration_step.py:62-72`). There is no per-predictor drift calculation and no system-health red/yellow signal in this sub-cluster.

Per the ADR these gaps are explicitly Phase 4 territory (`:38`) — the gap-analysis task T-046 surfaces them in `docs/code-health/03-quant-and-forecasting-gaps.md`. This reality doc records what the code does today.

## 2. Asset universe resolver (`asset_universe_resolver.py`)

Pure resolution logic — "no storage I/O happens here" (`asset_universe_resolver.py:19-23`). No SP500 / EU600 / ALL_5K universe-set selector; no pilot conids list; no cache TTL.

### Entry point

`resolve_forecast_universe(*, ibkr_account_id, watchlist_provider, position_provider, override_conids=None)` (`asset_universe_resolver.py:77-83`).

### Inputs

- `ibkr_account_id: str` — single account.
- `WatchlistUniverseProvider` Protocol (`:49-60`) — `list_active_conids_for_account(ibkr_account_id) -> tuple[(conid, symbol), ...]`. "Implementations skip rows with empty `ibkr_conid`" (`:58-60`).
- `PositionUniverseProvider` Protocol (`:63-74`) — `list_held_positions_for_account(ibkr_account_id) -> tuple[(conid, symbol, Decimal), ...]`. "Held means `quantity > 0`" (`:71-72`).
- `override_conids: tuple[str, ...] | None` — when non-empty bypasses both providers (`:82, :86-90`). Maps to `FORECAST_OVERRIDE_CONIDS` env var (`:14-17`).

### Output

`tuple[ConidWithContext, ...]` where `ConidWithContext` is a frozen dataclass with `conid`, `symbol`, `source: str` ∈ `{"watchlist", "position", "both", "override"}`, `held_quantity: Decimal`, `user_holds_position: bool` (`:42-46`).

### Dedup

Sorted by conid ascending; `setdefault`-merged across both sources (`:111-125`). When a conid appears in both watchlist and positions, `source` becomes `"both"` and the position's `held_quantity` wins (`:130-134`). Override path returns `held_quantity=Decimal("0")`, `user_holds_position=False`, `symbol=conid` (`:94-101`). Empty/whitespace conids skipped (`:113-114, :119-120`); non-positive quantities skipped (`:121-122`).

## 3. Calibration step (`calibration_step.py`)

Trigger: "Called by the orchestrator on `pre_briefing` 06:00 fires" (`calibration_step.py:1-3`).

### Entry point

`run_calibration_step(*, forecast_repo, diary_repo, realized_close_provider, now_provider=..., max_to_evaluate=100)` (`calibration_step.py:74-81`).

### Algorithm

"For each forecast whose `forecast_valid_until` is in the past AND `expired_at` is still NULL" (`calibration_step.py:3-5`):

1. Look up the close on the as-of-or-after target date.
2. Compute `realized log-return = ln(realized_close / current_price)` (`:132-138`).
3. Decide the locked `hit_status` from p10/p90.
4. Append one `CalibrationDiaryEntry` row (`:145-154`).
5. Mark `expired_at` so the forecast won't re-evaluate (`:155-157`).

This is **per-forecast** calibration, not per-predictor.

### Locked `hit_status` cases (`calibration_step.py:62-72`)

| Condition | `hit_status` |
|---|---|
| `realized > p90` | `"realized_above_p90"` |
| `realized < p10` | `"realized_below_p10"` |
| `p10 <= realized <= p90` | `"realized_within_p10_p90"` |
| (fallback) | `"realized_outside_band"` |

### Storage

- Reads: `forecast_repo.list_expired_unprocessed(now=now, limit=max_to_evaluate)` (`:85-87`); `realized_close_provider.get_close_on_or_after(ibkr_conid=..., target_date=...)` (`:94-96`, Protocol `:33-38`).
- Writes: `CalibrationDiaryEntry(forecast_run_id, evaluated_at, realized_log_return, hit_status, realized_close_price)` via `diary_repo.append(...)` (`:145-154`). Marks the forecast row via `forecast_repo.mark_expired(forecast_run_id, expired_at)` (`:155-157`).

### Per-forecast error handling

All boundary catches surface as `_PerForecastResult(written=False, error=...)`:

- Realized-close lookup raised → `error=str(exc)` (`calibration_step.py:92-109`).
- Missing realized close → `error="realized_close_not_found"` (`:110-119`).
- Non-positive `current_price_local` → `error="current_price_local_not_positive"` (`:121-130`).
- Diary persist raised → caught (`:145-179`).

### Math precision note

`realized log-return = Decimal(repr(math.log(float(realized_close) / float(forecast.current_price_local)))).quantize(Decimal("0.0000000001"))` — 10 decimal places (`calibration_step.py:132-138`). Passes through `float` intermediates but re-wraps via `repr` for the final Decimal — same pattern as the bootstrap output (see §5).

### Result

`CalibrationStepResult(forecasts_evaluated, diary_rows_written, per_forecast)` (`:49-59`) with `as_audit_dict()` for the orchestrator fold.

## 4. Forecasting step (`forecasting_step.py`)

Trigger: "orchestrator on `morning_briefing` 07:00 fires when `mode_detected='normal'`" (`forecasting_step.py:3-5`).

### Entry points

- `run_forecasting_step(*, ibkr_account_id, watchlist_provider, position_provider, close_provider, forecast_repo, scheduled_run_id, now_provider=..., rng_seed=None, history_window_days=252, horizon_days=20, num_resamples=10_000, block_size=5, override_conids=None)` (`forecasting_step.py:124-140`). Docstring: "Run one multi-asset forecasting cycle. Never raises." (`:140`).
- `_forecast_single_asset(...)` (`:195-208`) — module-private but called once per asset by `run_forecasting_step`.

### Single-predictor reality

The only predictor instantiated is `historical_bootstrap_v1`. Imports at `forecasting_step.py:48-55`. Single call site at `:278-285`. Forecast `method` is hard-coded `"historical_bootstrap_v1"` at `:349` and `:406`. **No** GBM, momentum, mean-reversion, QVM modules in the worker. **No** walk-forward outer/inner loop. **No** ensemble combiner call.

### Per-asset flow

1. **Load closes** via `close_provider.list_recent_closes(ibkr_conid, days=history_window_days)` (`:213-215`). Exception → `block_reason="missing_asset_listing"` (`:216-229`). Empty → same (`:231-243`).
2. **Stale check** — `STALE_MARKET_DATA_THRESHOLD_DAYS = 3` (`:66`). `days_old > 3` → `block_reason="stale_market_data"` (`:249-262`).
3. **Insufficient history** — `len(closes) < MIN_CLOSES_FOR_FORECAST` (200) → `"insufficient_history"` (`:264-276`).
4. **Bootstrap call** — `compute_historical_bootstrap_forecast(...)` (`:278-285`). `BootstrapInsufficientHistoryError` → `"insufficient_history"` (`:286-298`). Other exception → `"computation_error"` (`:299-312`).
5. **Excessive volatility** — `EXCESSIVE_VOLATILITY_THRESHOLD = Decimal("1.00")` (`:71`). `forecast.expected_volatility_annualized > 1.00` → `"excessive_volatility"` (`:314-326`).
6. **Freshness + confidence** — `freshness = "fresh" if days_old <= 1 else "stale"` (`:328`); `confidence = derive_confidence(history_closes_count, gaps_in_last_60_days=0, expected_volatility_annualized)` (`:329-333`). **Note:** `gaps_in_last_60_days=0` is currently hard-coded — the gap-aware path in `derive_confidence` cannot fire today.
7. **Label** — `translate_to_label(forecast, user_holds_position, freshness, confidence, history_closes_count)` (`:334-340`).
8. **Persist** — `ForecastEntry(forecast_run_id=f"fcst_{uuid4().hex}", ..., method="historical_bootstrap_v1", forecast_valid_until=now + timedelta(days=int(horizon_days * 1.4)), ...)` via `forecast_repo.append(entry)` (`:341-366`). Persist failure → `_PerConidResult(forecast_run_id=None, ...)` → counted in `persistence_failures` (`:367-375`).

Blocked rows persist a placeholder `ForecastEntry` with `label="Geblokkeerd"`, `confidence_level="Laag"`, zero quantiles, `prob_positive=Decimal("0.5")` (`forecasting_step.py:385-438`).

### Locked block reasons (`forecasting_step.py:8-20`)

`insufficient_history`, `stale_market_data`, `missing_asset_listing`, `computation_error`, `excessive_volatility`.

### Result

`ForecastingStepResult(total_attempted, succeeded, blocked_by_reason, per_conid, wall_clock_ms, persistence_failures)` (`:91-121`). Wall-clock via `time.monotonic() * 1000.0` (`:142, :184`). "`succeeded` and `blocked_by_reason` count only **persisted** rows" (`:95-100`). `as_audit_dict()` for orchestrator fold.

## 5. Historical bootstrap math (`historical_bootstrap.py`)

Locked math (verbatim, `historical_bootstrap.py:1-19`):

1. Take the last `history_window_days` daily closes (default 252).
2. Compute daily log-returns.
3. Slide `horizon_days`-long overlapping windows of log-returns.
4. Bootstrap `num_resamples` (default 10 000) cumulative `horizon_days` log-returns using `block_size`-day block resampling (default 5).
5. Return p10/p50/p90 + probabilities + annualized volatility.

### Constants (`historical_bootstrap.py:30-35`)

`DEFAULT_HORIZON_DAYS = 20`, `DEFAULT_NUM_RESAMPLES = 10_000`, `DEFAULT_BLOCK_SIZE = 5`, `DEFAULT_HISTORY_WINDOW_DAYS = 252`, `MIN_CLOSES_FOR_FORECAST = 200`, `TRADING_DAYS_PER_YEAR = 252`.

### Resampling strategy

Block bootstrap — non-circular, non-stationary. Picks blocks of `block_size` consecutive daily returns from random start indices, sums until a horizon-length path is filled (`historical_bootstrap.py:101-126`). `num_blocks_per_resample = math.ceil(horizon_days / block_size)` (`:105`). `max_block_start = log_returns.size - block_size` (`:106`). Last block truncated so total path equals `horizon_days` (`:120-121`). Edge case: if history exactly equals block_size, falls back to single-day bootstrap (`:107-112`).

### Quantile / probability formulas (`historical_bootstrap.py:128-135`)

- `p10 = np.quantile(resampled_cumulative, 0.10)`
- `p50 = np.quantile(resampled_cumulative, 0.50)`
- `p90 = np.quantile(resampled_cumulative, 0.90)`
- `prob_pos = np.mean(resampled_cumulative > 0.0)`
- `prob_loss_gt_5 = np.mean(resampled_cumulative < math.log(1.0 - 0.05))`
- `daily_std = np.std(log_returns, ddof=1)`; `annualized_vol = daily_std * sqrt(252)`

### Float / Decimal boundary

Module docstring (`historical_bootstrap.py:13-15`) is explicit: "numpy float64 inside the bootstrap (we're computing distribution summary stats, not money). Decimal at every output where money is later derived." Reproducibility note (`:17-19`): "a seeded `numpy.random.default_rng` is used so golden tests pin the output to the fourth decimal place."

### Output

`BootstrapForecastResult` — `@dataclass(frozen=True)` at `historical_bootstrap.py:38-49`:

- `history_closes_count: int`, `horizon_days: int`
- `p10_log_return: Decimal`, `p50_log_return: Decimal`, `p90_log_return: Decimal`
- `prob_positive: Decimal`, `prob_loss_gt_5pct: Decimal`
- `expected_volatility_annualized: Decimal`

Decimal quantisation at output (`historical_bootstrap.py:140-149`): quantiles to `0.0000000001` (10 dp), probabilities to `0.000001` (6 dp), volatility to `0.00000001` (8 dp). Conversion uses `Decimal(repr(float_value)).quantize(...)` — float → str → Decimal, no float-truncation into the Decimal.

### Validation (`historical_bootstrap.py:77-97`)

- `horizon_days <= 0`, `num_resamples <= 0`, `block_size <= 0` → `ValueError`.
- `len(daily_closes) < 200` → `BootstrapInsufficientHistoryError`.
- Any negative close → `ValueError`.
- `log_returns.size < horizon_days` → `BootstrapInsufficientHistoryError`.

## 6. Label translator (`label_translator.py`)

**The locked vocabulary is six labels, not eight** (`label_translator.py:26-28`):

```
"Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken", "Geblokkeerd"
```

Locked semantics (`:4-12`):

- **Kopen** — strong positive signal + position not blocked.
- **Verminderen** — weak negative + user holds.
- **Verkopen** — strong negative + high downside + user holds.
- **Houden** — user holds + no sell-side trigger.
- **Bekijken** — everything else when freshness is good.
- **Geblokkeerd** — data-quality issue; `block_reason` enum.

### Threshold table (locked at `label_translator.py:38-45`)

| Constant | Value |
|---|---|
| `_KOPEN_PROB_POSITIVE_MIN` | `Decimal("0.65")` |
| `_KOPEN_PROB_LOSS_MAX` | `Decimal("0.15")` |
| `_VERMINDEREN_PROB_POSITIVE_MAX` | `Decimal("0.35")` |
| `_VERKOPEN_PROB_POSITIVE_MAX` | `Decimal("0.25")` |
| `_VERKOPEN_PROB_LOSS_MIN` | `Decimal("0.40")` |
| `_IMPLAUSIBLE_VOLATILITY_THRESHOLD` | `Decimal("0.50")` annualised |

Comment: "locked by product brainstorm 2026-05-25 §Q4" (`:38`).

### Decision tree (`label_translator.py:75-118`)

1. **Block reasons trump every label rule** (`:75-92`):
   - `freshness=="stale"` → `Geblokkeerd / data_stale` (`:76-77`)
   - `freshness=="unavailable"` → `Geblokkeerd / data_unavailable` (`:78-81`)
   - `history_closes_count < 200` → `Geblokkeerd / insufficient_history` (`:82-85`)
   - `expected_volatility_annualized > 0.50` → `Geblokkeerd / implausible_volatility` (`:86-92`)
2. **Sell-side (require `user_holds_position`)** (`:94-105`):
   - `prob_positive <= 0.25 AND prob_loss_gt_5pct >= 0.40` → `Verkopen`
   - `prob_positive <= 0.35 AND p50_log_return < 0` → `Verminderen`
3. **Buy-side** (`:107-113`): `prob_positive >= 0.65 AND p50_log_return > 0 AND prob_loss_gt_5pct <= 0.15` → `Kopen`.
4. **Residual** (`:115-118`): `Houden` if user holds; else `Bekijken`.

### Confidence (`derive_confidence`, `:121-142`)

- `Hoog`: ≥252 closes + zero gaps + vol ≤ Decimal("0.30") (`:134-139`).
- `Gemiddeld`: ≥200 closes + gaps ≤ 2 (`:140-141`).
- else `Laag` (`:142`).

`confidence` is accepted by `translate_to_label` but not used — the block_reason branches handle data quality (`:67-71`).

### Type literals

`Freshness = Literal["fresh", "stale", "unavailable"]` (`:24`). `ConfidenceLevel = Literal["Laag", "Gemiddeld", "Hoog"]` (`:25`). `BlockReason` literal at `:29-35`: `data_stale`, `data_unavailable`, `insufficient_history`, `implausible_volatility`, `not_held_for_sell_label` (last is in the type but never produced by the function body).

## 7. Market-data step (`market_data_step.py`)

Trigger: "orchestrator when `mode_detected='normal'` AND `pre_briefing` or `morning_briefing`. Hourly delta runs (08:00–21:00) skip this step entirely — EOD prices don't change intraday." (`market_data_step.py:2-11`).

### Entry point

`fetch_market_data_for_account(*, ibkr_account_id, asset_universe, snapshot_repo, fx_rate_repo, eodhd_client, target_date, now_provider=..., base_currency="EUR")` (`market_data_step.py:92-103`).

`AssetForFetch` frozen dataclass (`:42-49`): `ibkr_conid`, `symbol`, `exchange`, `currency_local`.

### Storage table writes

- EOD snapshots → `snapshot_repo.append(MarketDataEodSnapshotEntry(...))` (`:166-185`). Fields: `snapshot_id=f"mdsnap_{uuid4().hex}"`, `ibkr_conid`, `symbol`, `exchange`, `currency_local`, `as_of_date`, `as_of_close_ts=now`, `ingested_ts=now`, OHLC `open_local/high_local/low_local/close_local`, `adj_close_local`, `volume`, `provider=PROVIDER_CODE`, `provider_response_hash=response.raw_hash`.
- FX rates → `fx_rate_repo.upsert(FxRateRecord(base_currency, quote_currency, as_of_date, rate, ingested_ts=now, provider=PROVIDER_CODE))` (`:245-254`). The table is `market_data_eod_snapshot` (not `eod_bars` as the task spec guessed).

### Provider calls (EODHD only)

- `eodhd_client.fetch_eod(symbol=asset.symbol, exchange=asset.exchange, as_of_date=target_date)` (`:138-143`).
- `eodhd_client.fetch_fx(base=currency, quote=base_currency, as_of_date=target_date)` (`:219-222`).

### FX pair derivation

While iterating snapshots, the step collects `needed_currencies` (set of each asset's `currency_local`, `:120, :127`). After snapshots, iterates `sorted(needed_currencies)`; for each currency `!= base_currency`, fetches `currency → base_currency` (e.g. `USD → EUR`) (`:206-208, :219-222`). Pair recorded as `FxRateRecord(base_currency=currency, quote_currency=base_currency, ...)` (`:246-250`).

### Cache / freshness / idempotency

- EOD: `snapshot_repo.get_for_date(ibkr_conid, as_of_date, provider=PROVIDER_CODE)` — if a snapshot exists for that conid+date+provider, skip (`:129-135`). "idempotent — same conid+date already cached" (`:135`).
- FX: `fx_rate_repo.get_rate(base_currency, quote_currency, as_of_date, provider)` — skip if cached (`:209-216`).
- Duplicate conids within one fetch are skipped via `seen_conids` set (`:122-126`).
- Empty-universe short-circuit returns a zero-counts result without any provider calls (`:105-114`).

### Decimal boundary

All Decimal values come from `EodResponse`/`FxResponse` built in `providers/eodhd.py` (see §8). No floats touched here.

### Error handling (never raises)

Docstring at `:13-15`: "every failed fetch is logged + counted in the returned `MarketDataFetchResult`." `EodhdNotConfiguredError` caught explicitly (`:144-153, :223-232`); generic exceptions caught at boundary (`:154-163, :233-242`); persistence errors caught (`:187-199, :256-267`).

### Result

`MarketDataFetchResult(snapshots_attempted, snapshots_succeeded, snapshots_failed, fx_rates_attempted, fx_rates_succeeded, fx_rates_failed)` (`:70-89`) with `as_audit_dict()` (`:81-89`). Failures: `_FetchFailure(ibkr_conid, symbol, error_class, message)` (`:60-67`).

## 8. EODHD provider (`providers/eodhd.py`)

### Class structure

`EodhdClient` (`providers/eodhd.py:115-310`). Constructor at `:118-141` (kw-only).

Module docstring (`:1-21`) declares:

- **Only two endpoints called**: `fetch_eod` + `fetch_fx`. No fundamentals, no splits, no dividends.
- "Coerce every numeric to `Decimal` via the string form (never float)" (`:11`).
- "Retry once on 5xx with 2 s backoff. No retry on 4xx" (`:12`).
- "Honour the configurable per-second rate limit (default 10 r/s, well below the 20 r/s EODHD ceiling)" (`:13-14`).
- "Write one `ProviderCallAuditEntry` row per call (success or failure)" (`:15-16`).
- "Return `EodhdNotConfiguredError` when `api_key=None` without touching the network" (`:17-18`).
- "The HTTP client is injectable so tests can supply a fake without adding `httpx` as a hard test-time dep" (`:20-21`).

### Constructor params (`providers/eodhd.py:118-141`)

`api_key: str | None`, `audit_repo`, `http_client: _HttpClientProtocol | None`, `base_url="https://eodhd.com/api"`, `rate_limit_per_second=10`, `clock`, `sleep`, `account_id`, `triggered_by_run_id` (last two for audit attribution).

`_HttpClientProtocol` at `:51-60` — single `get(url, *, params, timeout)` method.

### Constants

`PROVIDER_CODE = "eodhd"`, `_DEFAULT_TIMEOUT_SECONDS = 8.0`, `_RETRY_BACKOFF_SECONDS = 2.0` (`providers/eodhd.py:46-48`).

### Endpoints

- `fetch_eod` (`:143-167`) → `GET /eod/{symbol}.{exchange}?api_token=...&fmt=json&from={date}&to={date}` (`:155-160`).
- `fetch_fx` (`:169-190`) → `GET /eod/{base}{quote}.FOREX?...` (`:181-186`).

**No** fundamentals / splits / dividends endpoints anywhere in this file.

### `_request(...)` core (`providers/eodhd.py:194-273`)

- Lazy `_default_http_client_factory()` imports `httpx` only when needed (`:200-201, :407-415`).
- Loop `for attempt in (1, 2)` — up to two attempts total (one retry) (`:206`).
- `_rate_limiter.acquire()` before each attempt (`:207`).
- `_http_client.get(url, params=params, timeout=_DEFAULT_TIMEOUT_SECONDS)` (`:210-212`).
- 2xx: logs success, returns `json.loads(body_text)` (`:216-226`).
- 5xx on attempt 1: logs with `{"retry": True, "status": ...}`, sleeps 2 s, continues (`:228-239`).
- 4xx (any) or 5xx on attempt 2: logs final, raises `RuntimeError(f"EODHD request failed: HTTP {status}")` (`:240-252`).
- Exception during `get`: logs, sleeps + continues on attempt 1, re-raises on attempt 2 (`:253-269`).

### Rate limiter

`_RateLimiter` (`:90-112`) — token-bucket-style, threading-safe, refills one token every `1/rate_per_second` s (`:91-97`). `acquire()` blocks via `time.sleep` until next allowed time (`:106-112`).

### Auth — API key handling

- Stored on instance (`:131`).
- `fetch_eod` / `fetch_fx` raise `EodhdNotConfiguredError` **before** any HTTP call when key is `None` (`:150-153, :176-179`).
- Key passed as `api_token` query param (`:156, :182`).
- **API key is stripped from audit rows** (`:288-289`): `sanitised = {k: v for k, v in params.items() if k != "api_token"}`.

### Audit writes

`_log_call(...)` (`:275-310`) writes `ProviderCallAuditEntry(audit_id=f"pcaud_{uuid4().hex}", called_at, provider=PROVIDER_CODE, endpoint, request_params_json (sanitised), response_status, response_size_bytes, duration_ms, error_class, error_details_json, account_id, triggered_by_run_id)` (`:290-308`). Audit-write failures are caught and logged so they can never crash the parent call (`:309-310`).

### Decimal parsing

- `_decimal_required(value)` (`:375-378`): if already `Decimal`, return as-is; else `Decimal(str(value))`. **No `float()` cast.** Raw JSON value → `str()` → `Decimal` directly.
- `_decimal_or_none(value)` (`:381-384`): same path, `None` for empty.
- `_int_or_none(value)` (`:387-393`): `int(value)` for volume only.

### Response parsers

- `_parse_eod_response(...)` (`:316-345`): non-empty list (`:323-324`), reads `row[0]` (`:325-327`), requires `close` (`:328-330`), computes `raw_hash = sha256(json.dumps(row, sort_keys=True).encode("utf-8")).hexdigest()` (`:331-333`).
- `_parse_fx_response(...)` (`:348-372`): same shape; `close_raw = row.get("close") or row.get("adjusted_close")` (`:360`); same `raw_hash` (`:363-365`).

Output records: `EodResponse` (`:63-77`) with all numerics `Decimal` or `Decimal | None`, plus `raw_hash`. `FxResponse` (`:79-87`) with `rate: Decimal`, `raw_hash`.

## 9. Decision-package composer (`decision_package/composer.py`)

### Doctrine bindings (verbatim, `composer.py:1-24`)

- **"AI never originates a field of the Decision Package.**" The label is copied from the forecast; the explanation is generated by the locked Dutch template; the gate outcomes are deterministic boolean checks; the audit hash is SHA-256 of canonical JSON. (`:8-12`)
- **"Decimal end-to-end.** No `float` anywhere in the composition path, including inside the hash input. The canonical JSON serializer renders each Decimal as its string repr with full precision so the hash is reproducible." (`:13-17`)
- **"Immutable.** `DecisionPackageEntry` is frozen; the composer never mutates input records. Two calls with identical inputs (modulo `composed_at`) yield identical hashes." (`:18-20`)
- **"The composer crashes when asked to compose for a `Geblokkeerd` forecast — that's a caller bug.** The orchestrator filters Geblokkeerd forecasts before calling." (`:21-24`)

### Entry point

`compose_decision_package(*, forecast, ibkr_account_id, market_snapshot, fx_rate, asset_listing, position_snapshot, previous_package, composed_at=None)` (`composer.py:79-89`).

Geblokkeerd guard raises `GeblokkeerdForecastError` (`composer.py:70-76`, raised `:108-113`). `composed_at` defaults to `datetime.now(UTC)` (`:115-116`).

### Locked gate sequence (`composer.py:56-62`)

`forecast_valid`, `data_fresh`, `asset_listing_resolved`, `freshness_within_sla`, `confidence_at_least_medium`. "Must stay in this order so the explanation template can append 'Let op:' sentences in the same sequence." (`:54-55`)

`_FRESHNESS_SLA_DAYS = 3` (`:67`) — same threshold as the Task 131 `stale_market_data` block_reason (`:64-67`).

### Gate evaluation (`evaluate_gates`, `:287-358`)

| Gate | Condition | Dutch fail reason |
|---|---|---|
| `forecast_valid` | Always `True` here (orchestrator pre-filters Geblokkeerd) | n/a — "for completeness + audit traceability" (`:298-309`) |
| `data_fresh` | `freshness_state != "unavailable"` | "Marktdata is niet beschikbaar voor dit asset." (`:310-320`) |
| `asset_listing_resolved` | `asset_listing is not None` | "Asset-listing kon niet worden opgehaald." (`:321-331`) |
| `freshness_within_sla` | `data_age_trading_days <= 3` | `f"Marktdata is {data_age_trading_days} dagen oud; SLA is {_FRESHNESS_SLA_DAYS} dagen."` (`:332-345`) |
| `confidence_at_least_medium` | `forecast.confidence_level in ("Gemiddeld", "Hoog")` | "Betrouwbaarheid is Laag — gebruik met voorzichtigheid." (`:346-357`) |

### Per-asset derived fields (`composer.py:118-178`)

- `user_holds = position_snapshot is not None and position_snapshot.quantity > 0` (`:118-120`).
- `held_quantity`, `held_avg_cost` from snapshot when held (`:121-126`).
- `current_price_eur`, `p10/p50/p90_price_eur` via `_convert_to_eur(...)` (`:129-154`).
- `data_age` via `_trading_day_age` (`:500-512`) — calendar-day proxy, honest about being calendar-day not trading-day (`:503-509`).
- `freshness_state` via `_classify_freshness` (`:515-520`): `<=1 → "fresh"`, `<=3 → "stale"`, else `"unavailable"`.
- `gates = evaluate_gates(...)` (`:164-169`).
- `explanation = render_explanation(...)` (see §10).
- `decision_package_id = f"dp_{uuid4().hex}"` (`:200`).
- `previous_package_hash = previous_package.audit_trail_hash if not None` (`:201-205`).

### Quantile price math

`_price_at_quantile(current_price_local, log_return)` (`:469-475`): `factor = Decimal(repr(math.exp(float(log_return))))`, `(current_price_local * factor).quantize(Decimal("0.000001"))`. Goes through `float` for `exp` but re-wraps as Decimal via `repr` — same pattern as the bootstrap output.

`_convert_to_eur(amount_local, fx_rate)` (`:478-497`): EUR-only assets short-circuit (`:484-485`); missing FX for non-EUR falls back 1:1 with logger warning (`:486-496`).

### Hash-chain invariants

`compute_audit_trail_hash(...)` (`composer.py:361-455`). Computation at `:452-455`:

```python
canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
return hashlib.sha256(canonical.encode("utf-8")).hexdigest()
```

**Content-addressed invariant** (`:395-401`): "SHA-256 over canonical JSON of every package-defining field. `composed_at` + `decision_package_id` are **deliberately excluded** so the hash is content-addressed — two compositions of the same logical content yield identical hashes (the per-asset chain check in `test_compose_idempotent_hash` depends on this)."

Hash-input fields (`:403-451`): `forecast_run_id`, `ibkr_account_id`, `conid`, `symbol`, `exchange`, `currency_local`, `asset_class`, `user_holds_position`, `held_quantity`, `held_avg_cost_local`, `current_price_local`, `current_price_eur`, `as_of_market_data_ts.isoformat()`, `freshness_state`, `data_age_trading_days`, `forecast_method`, `p10/p50/p90_log_return`, `p10/p50/p90_price_eur`, `prob_positive`, `prob_loss_gt_5pct`, `expected_volatility_annualized`, `forecast_confidence_level`, `suggested_action_label`, `block_reason`, `gate_outcomes` (list of `{gate_name, passed, reason_nl}`), `evidence_references` (list of `{source_id, source_type, claim_summary}`), `previous_package_hash`.

`_decimal_to_canonical(value)` (`:461-466`): `str(Decimal)` preserves full precision without scientific notation. **No `float()` anywhere in the hash path.**

### Evidence collection (`_build_evidence_references`, `:523-564`)

Always includes the EOD market-data snapshot (`:529-538`); claim_summary `f"EOD-snapshot voor {symbol} op {as_of_date.isoformat()}"`. Adds FX-rate evidence when `fx_rate is not None` (`:539-552`); claim `f"FX-koers {base}→{quote} = {rate}"`. Adds IBKR position evidence when held (`:553-563`). **No news/research evidence in this composer.**

### Output record `DecisionPackageEntry` (`composer.py:245-284`)

Imported from `ai_trading_agent_storage`. Key fields:

- `decision_package_id`, `forecast_run_id`, `composed_at`, `valid_until`, `ibkr_account_id`, `conid`, `symbol`, `exchange`, `currency_local`, `asset_class` (`:246-255`)
- `user_holds_position`, `held_quantity`, `held_avg_cost_local` (`:256-258`)
- `current_price_local`, `current_price_eur` (`:259-260`)
- `as_of_market_data_ts`, `freshness_state`, `data_age_trading_days` (`:261-263`)
- `forecast_method`, `p10/p50/p90_log_return`, `p10/p50/p90_price_eur` (`:264-270`)
- `prob_positive`, `prob_loss_gt_5pct`, `expected_volatility_annualized` (`:271-273`)
- `forecast_confidence_level`, `suggested_action_label`, `block_reason` (`:274-276`)
- `gate_outcomes: tuple[GateOutcome, ...]`, `evidence_references: tuple[EvidenceReference, ...]` (`:277-278`)
- `deterministic_dutch_explanation: str` (`:279`)
- `audit_trail_hash: str`, `previous_package_hash: str | None` (`:280-281`)
- **`safe_for_action_drafts=False`, `safe_for_orders=False`** — hard-coded `False` in V1.1.0 (`:282-283`).

## 10. Dutch explanation template (`decision_package/dutch_explanation_template.py`)

Module header (`dutch_explanation_template.py:1-20`):

- **"Pure Python templating. No AI. No conditional prose beyond the locked branches below."** (`:3-4`)
- "Same forecast + same gate outcomes always produces the exact same paragraph — that's the doctrine: 'AI never originates a field of the Decision Package'." (`:4-6`)
- "UI surfaces the paragraph verbatim — no client-side rendering of forecast numbers, no client-side translation." (`:18-20`)

Confirmed: **no AI call.** No model-client imports. Only stdlib + `ai_trading_agent_storage.GateOutcome` (`:23-28`). Interpolation is Python f-strings (hand-built), **not** `str.format`, **not** Jinja.

### Locked paragraph structure (`:8-17`)

```
{opening sentence with asset name + label + horizon}
{forecast quantile sentence with p10/p50/p90 prices in EUR}
{probability sentence with prob_positive + prob_loss_gt_5pct}
{risk sentence with annualized volatility}
{confidence sentence}
{validity sentence}
{one "Let op: <reason>" sentence per failed gate}
```

### Locked constants

`_LABEL_PROSE` (`:33-39`):

- `"Kopen"` → `"een koopkans"`
- `"Verminderen"` → `"een aanleiding om de positie te verminderen"`
- `"Verkopen"` → `"een aanleiding om de positie te verkopen"`
- `"Houden"` → `"geen actie nodig"`
- `"Bekijken"` → `"een signaal om te bekijken"`

(Geblokkeerd never reaches this template; comment `:30-32`.)

`_DUTCH_MONTHS` (`:43-56`) — integer-to-Dutch-month-name map (`januari` … `december`). "Avoid locale-dependent `strftime` which on CI containers can produce English names." (`:42-43`)

Formatting helpers: `_fmt_date_nl` (`:59-60`); `_fmt_pct(value, decimals=0)` (`:63-68`) multiplies by `Decimal("100")`, formats via float, replaces `.` with `,`, appends `%`; `_fmt_eur(value)` (`:71-76`) quantises to 0.01, replaces `.` with `,`, prepends `€`.

### Entry point + validation

`render_explanation(*, symbol, label, horizon_trading_days, p10/p50/p90_price_eur, prob_positive, prob_loss_gt_5pct, expected_volatility_annualized, confidence_level, valid_until, gate_outcomes)` (`:79-93`). Raises `ValueError` if `label not in _LABEL_PROSE` (`:101-105`).

### Locked sentence templates

| Sentence | File:line |
|---|---|
| Opening | `:107-111` (`f"Voor {symbol} duidt de voorspelling op {_LABEL_PROSE[label]} (label: {label}) over de komende {horizon_trading_days} handelsdagen."`) |
| Quantile | `:112-116` (`Verwachte bandbreedte in EUR: {p10} (p10) — {p50} (mediaan) — {p90} (p90).`) |
| Probability | `:117-120` |
| Risk | `:121-124` |
| Confidence | `:125` (`Betrouwbaarheid: {confidence_level}.`) |
| Validity | `:126-128` (`Deze Decision Package is geldig tot {date}.`) |
| Per failed gate | `:141-143` (`Let op: {gate.reason_nl}`) — appended once per `gate.passed == False`, in input order (composer's responsibility, `:139-141`) |

Final join via `" ".join(paragraph_parts)` (`:144`).

## 11. Decision-package orchestration (`decision_package/orchestration.py`)

Module purpose (`orchestration.py:1-11`): "The bridge between the persisted forecasts of a scheduled run and the `compose_decision_package` pure function… Failures in single-asset composition are logged but do **not** crash the run — the forecast row is already durable, so a failed package composition is a soft degradation, not data loss."

### Entry point

`compose_and_persist_for_run(*, ibkr_account_id, scheduled_run_id, forecast_source, context_provider, decision_package_repo, now_provider=...)` (`orchestration.py:93-101`).

### Protocols

- `_ForecastSourceProtocol` (`:38-43`) — `list_forecasts_for_scheduled_run(ibkr_account_id, scheduled_run_id) -> tuple[ForecastEntry, ...]`.
- `_ContextProviderProtocol` (`:46-63`) — four methods: `market_snapshot_for_conid`, `fx_rate_for_currency`, `asset_listing_for_conid`, `position_for_account_conid`.

### Per-asset iteration (`orchestration.py:119-188`)

1. Load all forecasts for the run (`:108-111`).
2. For each forecast:
   - **Skip Geblokkeerd** — `skipped_geblokkeerd += 1` (`:120-122`).
   - Fetch market snapshot (`:124-126`); `None` → log warning, `missing_context += 1`, continue (`:127-135`). "No snapshot → composer can't compute current_price_eur or the freshness gate."
   - Conditionally fetch FX (skip if currency is EUR) (`:137-143`).
   - Fetch asset listing (`:144-146`) + current position (`:147-149`).
   - **Fetch previous package as chain anchor** — `decision_package_repo.get_latest_for_account_conid(ibkr_account_id, conid)` (`:150-154`).
   - Call `compose_decision_package(...)` (`:156-166`).
   - Catch `GeblokkeerdForecastError` defensively → `skipped_geblokkeerd += 1` (`:167-170`).
   - Catch all other exceptions → log + `composition_errors += 1` (`:171-177`).
   - Persist via `decision_package_repo.append(package)` (`:179-181`).
   - Persist failure → log + `composition_errors += 1` (`:182-188`).

### Storage

Writes: `decision_package_repo.append(package)` (`:180`) — one Decision Package row per asset per run. No explicit audit-row write inside this orchestration file; the audit dict is returned to the caller via `as_audit_dict()`.

### Result

`DecisionPackageCompositionResult(forecasts_seen, composed, skipped_geblokkeerd, missing_context=0, composition_errors=0, persisted_ids=())` (`:66-90`). Documented invariant (`:70-74`): `forecasts_seen == composed + skipped_geblokkeerd + missing_context + composition_errors`.

## 12. Cross-cutting observations

- **Single-predictor reality (vs ADR's seven-predictor intent).** Only `historical_bootstrap_v1` is in the worker; no ensemble combiner exists. Major Phase 1c gap surface for `docs/code-health/03-quant-and-forecasting-gaps.md` (T-046).
- **Six labels, not eight.** `Kopen`, `Verminderen`, `Verkopen`, `Houden`, `Bekijken`, `Geblokkeerd` (`label_translator.py:26-28`). The 8-bucket `Sterk dalend` / `Onbepaald` family the task spec assumed does not exist.
- **Decimal-as-string discipline** is enforced in three places with documented rationale: provider parsers (`providers/eodhd.py:11, :375-378`), bootstrap output quantisation (`historical_bootstrap.py:13-15, :140-149`), composer hash input (`composer.py:13-17, :461-466`). Floats are tolerated only inside numpy bootstrap (intentional — distribution statistics, not money).
- **Decision-package audit hash is content-addressed.** Excludes `composed_at` + `decision_package_id` (`composer.py:207-210, :395-401`). Chain anchor via `previous_package_hash` pointing at the prior package's `audit_trail_hash` (`:201-205, :280-281`). Idempotency: two compositions of identical content produce identical `audit_trail_hash`.
- **EODHD client never leaks the API key** (`providers/eodhd.py:288-289`).
- **`_trading_day_age` is a calendar-day proxy**, not literal trading-day arithmetic — flagged in code as a conservative approximation (`composer.py:500-512`).
- **`gaps_in_last_60_days=0` is hard-coded** in `forecasting_step.py:331` — the gap-aware path in `derive_confidence` (`label_translator.py:140-142`) cannot fire today.
- **EODHD endpoints under-implement the ADR's "All-In-One" intent.** ADR locks "EODHD All-In-One data tier" (`docs/decisions/0003-forecast-engine-architecture.md:29`); the client implements only `/eod` and `/eod/...FOREX` — no fundamentals, splits, or dividends. Phase 4 surface.
