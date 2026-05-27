# Reality — workflow: forecast generation + labelling

**Scope.** End-to-end per-asset trace of how a forecast is generated and labelled — from the orchestrator's forecasting gate firing at 07:00 morning_briefing → universe resolution → per-asset close-history load → block-bootstrap math → freshness + confidence + label decision → persisted `ForecastEntry` row in the `forecasts` table. Documents the **single-predictor reality** against ADR-0003's seven-predictor intent.

This is the math + labelling side of the morning chain. Sibling workflow docs:

- `docs/reality/workflows/morning-chain-orchestration.md` (T-011) — the orchestration shell that calls into this flow.
- `docs/reality/workflows/market-data-pipeline.md` (T-014) — supplies the close history this flow consumes.
- Calibration / Decision Package / action-draft / AI explanation flows are siblings (T-016/T-017/T-018/T-023, future).

**Sibling reality docs (read for module-level detail):**

- `docs/reality/components/worker-forecasting-and-decision-package.md` §1-§6 — ADR intent, universe resolver, calibration, forecasting step, historical bootstrap, label translator (T-007).
- `docs/reality/components/portfolio-predictors.md` (T-002) — predictor protocol + backtester surface.

## 0. TL;DR

A worker orchestrator fire at 07:00 morning_briefing (T-011 §6) calls `forecasting_step.run_forecasting_step(...)`. For each asset in the universe (T-014 §3.1 — confirmed watchlist ∪ held positions):

1. Load the last 252 daily closes from `market_data_bars` (T-014 §5).
2. Run `compute_historical_bootstrap_forecast(daily_closes, history_window_days=252, horizon_days=20, num_resamples=10_000, block_size=5)` — block-bootstrap on log-returns, returns p10/p50/p90 + `prob_positive` + `prob_loss_gt_5pct` + `expected_volatility_annualized`.
3. Run 5 sequential gates that can short-circuit to a `Geblokkeerd` placeholder row:
   - `insufficient_history` (< 200 closes)
   - `stale_market_data` (latest close > 3 days old)
   - `missing_asset_listing` (close provider raised or empty)
   - `computation_error` (bootstrap raised)
   - `excessive_volatility` (annualised > 1.00)
4. Derive `freshness ∈ {fresh, stale}`, `confidence ∈ {Hoog, Gemiddeld, Laag}`, and the 6-label `suggested_action_label` via `translate_to_label(...)`.
5. Persist exactly one `ForecastEntry` row per asset (success rows + blocked placeholders both persisted).

**The single biggest gap** (T-007 §1, T-011 §15, T-014 §9.1, re-confirmed here): ADR-0003 locks 7 predictors + weighted-average ensemble + calibration correction layer; the worker ships **one predictor only** (`historical_bootstrap_v1`) with no ensemble combiner. Per ADR (`docs/decisions/0003-forecast-engine-architecture.md:38`) this gap is explicit Phase 4 work.

## 1. ADR-0003 — locked intent (verbatim)

`docs/decisions/0003-forecast-engine-architecture.md` (accepted 2026-05-26, Phase P1):

- **"Seven predictors retained for v1.** Simplification deferred to Phase 4 after gap-analysis verdict." (`:25`)
- **"Single 20 trading day horizon** (~ 1 month). Multi-horizon is a Phase 4 candidate." (`:26`)
- **"Weighted-average-by-historical-accuracy ensemble** with a 10% weight floor and 40% ceiling. Strong predictor disagreement reduces combined confidence by design." (`:27`)
- **"Mandatory calibration correction layer** with yellow / red on system-health for per-predictor / ensemble drift. Red ensemble drift stops new suggestion generation but keeps existing forecasts visible." (`:28`)
- **"EODHD All-In-One data tier required."** (`:29`)

Phase 4 queue (`:40`): "predictor-set simplification review, multi-horizon evaluation, regime detection, survivorship-bias correction."

## 2. The single-predictor reality

Per T-007 `worker-forecasting-and-decision-package.md` §1 — verified gap inventory:

| Intent (ADR-0003) | Reality (HEAD) | Where |
|---|---|---|
| 7 predictors retained | **1 predictor shipped**: `historical_bootstrap_v1` | `apps/worker/.../forecasting/forecasting_step.py:48-55` (sole import), `:349, :406` (sole `method=` stamp) |
| Weighted-average ensemble (10/40 floor/ceiling) | **No ensemble combiner** in the worker | n/a |
| Mandatory calibration correction layer | **Per-forecast realised-vs-band only** (T-016 future) — no per-predictor drift, no system-health red/yellow | `apps/worker/.../forecasting/calibration_step.py:62-72` |
| EODHD All-In-One | **EOD + FX only** (T-014 §3.2) | `apps/worker/.../providers/eodhd.py:143-190` |

Per the ADR, these are **explicit Phase 4 deferrals** (`docs/decisions/0003-forecast-engine-architecture.md:38, :40`). The doc lands the math at the same horizon (20 trading days) the ADR locked.

## 3. The forecasting step (`forecasting_step.py:124-140`)

Triggered by `worker.orchestrator.run_orchestrator` step 9 (T-011 §6 control-flow):

```
if mode_detected == "normal" AND run_type == "morning_briefing" AND forecasting_runner is not None AND ibkr_account_id is not None:
    forecast_details = forecasting_runner.run(ibkr_account_id, scheduled_run_id)
```

**Gate**: `mode_detected="normal"` AND `run_type="morning_briefing"`. Pre_briefing skips forecasting; hourly_delta runs at 08:00–21:00 do not run forecasting either. Forecasts are written **exactly once per morning**, at 07:00 Brussels.

### 3.1 Entry signature (`forecasting_step.py:124-140`)

```python
def run_forecasting_step(
    *,
    ibkr_account_id: str,
    watchlist_provider, position_provider,
    close_provider: _CloseProviderProtocol,
    forecast_repo: SqlAlchemyForecastRepository,
    scheduled_run_id: str,
    now_provider, rng_seed, history_window_days=252,
    horizon_days=20, num_resamples=10_000, block_size=5,
    override_conids=None,
) -> ForecastingStepResult
```

Docstring contract (`forecasting_step.py:140`): **"Never raises."**

### 3.2 Outer loop (`forecasting_step.py:156-182`)

1. Resolve universe via `resolve_forecast_universe(...)` (`forecasting_step.py:143-148`) — confirmed watchlist ∪ held positions (T-012 §1 + T-014 §3.1 outer).
2. For each `ConidWithContext` in the universe, call `_forecast_single_asset(...)` (`forecasting_step.py:156-168`).
3. Classify result into `succeeded`, `blocked_by_reason[block_reason]`, or `persistence_failures` (`:170-182`).

Wall-clock instrumentation via `time.monotonic() * 1000.0` (`:142, :184`).

## 4. The 5 block reasons (`_forecast_single_asset`, `forecasting_step.py:195-382`)

Sequential gates — first match wins. Each blocked row still persists a placeholder `ForecastEntry` with `label="Geblokkeerd"`, `confidence_level="Laag"`, zero quantiles, `prob_positive=Decimal("0.5")` (`:385-438`). The `block_reason` column on the row makes the failure mode observable.

| Gate # | Block reason | Condition | File:line |
|---|---|---|---|
| 1 | `missing_asset_listing` | `close_provider.list_recent_closes(...)` raises OR returns empty | `:213-243` |
| 2 | `stale_market_data` | `STALE_MARKET_DATA_THRESHOLD_DAYS = 3` (`:66`); `(now.date() - latest_close_date).days > 3` | `:249-262` |
| 3 | `insufficient_history` | `MIN_CLOSES_FOR_FORECAST = 200` (per `historical_bootstrap.py:34`); `len(closes) < 200` | `:264-276` |
| 4 | `computation_error` | `compute_historical_bootstrap_forecast(...)` raises a non-`BootstrapInsufficientHistoryError` exception | `:299-312` |
|   | (`insufficient_history` re-emission) | `compute_historical_bootstrap_forecast(...)` raises `BootstrapInsufficientHistoryError` — falls back to gate 3's category | `:286-298` |
| 5 | `excessive_volatility` | `EXCESSIVE_VOLATILITY_THRESHOLD = Decimal("1.00")` (`:71`); `expected_volatility_annualized > 1.00` (annualised) | `:314-326` |

**The 3-day stale threshold collides with the 15/30-minute freshness policy from T-014 §2** — T-014's policy is for IBKR live quotes; this 3-day threshold is for EOD bars feeding forecasts. Different freshness scales for different consumers; T-014 §9.4 flags this as a per-data-domain Phase 1c surface.

## 5. The block-bootstrap math (`historical_bootstrap.py`)

The single predictor. Module docstring (`historical_bootstrap.py:1-19`) lays out the algorithm:

1. Take the last `history_window_days` daily closes (default 252).
2. Compute daily log-returns.
3. Slide `horizon_days`-long overlapping windows of log-returns.
4. Bootstrap `num_resamples` cumulative `horizon_days` log-returns using `block_size`-day block resampling.
5. Return `p10/p50/p90 + prob_positive + prob_loss_gt_5pct + expected_volatility_annualized`.

### 5.1 Constants (`historical_bootstrap.py:30-35`)

| Constant | Value | Purpose |
|---|---|---|
| `DEFAULT_HORIZON_DAYS` | `20` | matches ADR-0003 single 20-day horizon (`:26`) |
| `DEFAULT_NUM_RESAMPLES` | `10_000` | bootstrap sample count |
| `DEFAULT_BLOCK_SIZE` | `5` | block bootstrap block length (preserves serial correlation) |
| `DEFAULT_HISTORY_WINDOW_DAYS` | `252` | one trading year |
| `MIN_CLOSES_FOR_FORECAST` | `200` | gate 3 threshold |
| `TRADING_DAYS_PER_YEAR` | `252` | volatility annualisation factor |

### 5.2 Block-bootstrap algorithm (`historical_bootstrap.py:101-126`)

- `num_blocks_per_resample = math.ceil(horizon_days / block_size)` (`:105`) — typically `ceil(20/5) = 4` blocks per resample.
- `max_block_start = log_returns.size - block_size` (`:106`) — bounds the random start index.
- Pick `num_blocks_per_resample` random start indices, each block is `block_size` consecutive daily log-returns. Sum within each block; concatenate blocks; truncate the last block so total path equals `horizon_days` (`:120-121`).
- Sum across all blocks → one cumulative `horizon_days`-day log-return per resample.
- Edge case: if history exactly equals `block_size`, falls back to single-day bootstrap (`:107-112`).

This is **non-circular, non-stationary** block bootstrap — preserves short-range autocorrelation (within a 5-day block) but loses long-range structure (across blocks). Module docstring (`:13-15`) is explicit on the design rationale.

### 5.3 Quantile + probability formulas (`historical_bootstrap.py:128-135`)

| Field | Formula |
|---|---|
| `p10 / p50 / p90` | `np.quantile(resampled_cumulative, {0.10, 0.50, 0.90})` |
| `prob_positive` | `np.mean(resampled_cumulative > 0.0)` |
| `prob_loss_gt_5` | `np.mean(resampled_cumulative < math.log(1.0 - 0.05))` (log-return for −5%) |
| `daily_std` | `np.std(log_returns, ddof=1)` |
| `annualized_vol` | `daily_std * sqrt(252)` |

### 5.4 Float / Decimal boundary

Module docstring `:13-15`: *"numpy float64 inside the bootstrap (we're computing distribution summary stats, not money). Decimal at every output where money is later derived."*

Quantisation at output (`historical_bootstrap.py:140-149`):

- Quantiles → `0.0000000001` (10 dp).
- Probabilities → `0.000001` (6 dp).
- Volatility → `0.00000001` (8 dp).

Conversion uses `Decimal(repr(float_value)).quantize(...)` — float → str → Decimal, **no float-truncation into the Decimal** (per T-002 `portfolio-money-and-accounting.md` Decimal-as-string discipline).

### 5.5 Reproducibility

Seeded `numpy.random.default_rng(rng_seed)` (`historical_bootstrap.py:99`); golden tests pin output to the fourth decimal place (`:17-19`).

### 5.6 Output dataclass `BootstrapForecastResult`

Frozen at `historical_bootstrap.py:38-49`:

- `history_closes_count: int`
- `horizon_days: int`
- `p10_log_return / p50_log_return / p90_log_return: Decimal`
- `prob_positive: Decimal`
- `prob_loss_gt_5pct: Decimal`
- `expected_volatility_annualized: Decimal`

## 6. Per-asset derived fields (`forecasting_step.py:328-340`)

After successful bootstrap, before persistence:

### 6.1 Freshness (`:328`)

```python
freshness = "fresh" if days_old <= 1 else "stale"
```

Binary: `fresh` (close is today or yesterday) or `stale` (older but ≤ 3 days; > 3 days hit gate 2 and never reach here).

**Note**: forecasts only get `Freshness ∈ {"fresh", "stale"}`. The third state `"unavailable"` declared at `label_translator.py:24` is emitted only when gate 1 (missing_asset_listing) fires, but those paths persist a `Geblokkeerd` placeholder (§4) — the label-translator's `data_unavailable` block-reason path applies to the placeholder row's `block_reason` field, not to the live forecast.

### 6.2 Confidence (`derive_confidence`, `label_translator.py:121-142`)

3-state enum `ConfidenceLevel = Literal["Laag", "Gemiddeld", "Hoog"]` (`label_translator.py:25`):

| Level | Condition |
|---|---|
| `Hoog` | ≥252 closes AND zero gaps AND vol ≤ `Decimal("0.30")` |
| `Gemiddeld` | ≥200 closes AND gaps ≤ 2 |
| `Laag` | else |

**Hardcoded gap count** (`forecasting_step.py:331`):

```python
confidence = derive_confidence(history_closes_count, gaps_in_last_60_days=0, expected_volatility_annualized)
```

`gaps_in_last_60_days=0` is a literal — the confidence deriver's gap-aware path (`label_translator.py:140-142`) **never fires today**. T-007 §6 + T-011 §15 + T-014 §9 already flagged this; T-015 re-confirms.

Consequence: in practice every asset that passes gate 3 (≥200 closes) gets either `Hoog` (if vol ≤ 0.30 AND ≥252 closes) or `Gemiddeld`. The `Laag` confidence path is unreachable from `derive_confidence` for a forecast that survives the upstream gates.

## 7. The 6-label decision tree (`label_translator.py`)

Locked enum at `label_translator.py:26-28`:

```python
LABELS = Literal["Kopen", "Verminderen", "Verkopen", "Houden", "Bekijken", "Geblokkeerd"]
```

**Locked by product brainstorm 2026-05-25 §Q4** (`label_translator.py:38` comment). This is the canonical Dutch label set — frontend pills, Decision Package headers, action-draft routing all key off this enum.

### 7.1 Threshold table (`label_translator.py:39-45`)

| Constant | Value | Used in |
|---|---|---|
| `_KOPEN_PROB_POSITIVE_MIN` | `Decimal("0.65")` | Kopen gate |
| `_KOPEN_PROB_LOSS_MAX` | `Decimal("0.15")` | Kopen gate |
| `_VERMINDEREN_PROB_POSITIVE_MAX` | `Decimal("0.35")` | Verminderen gate |
| `_VERKOPEN_PROB_POSITIVE_MAX` | `Decimal("0.25")` | Verkopen gate |
| `_VERKOPEN_PROB_LOSS_MIN` | `Decimal("0.40")` | Verkopen gate |
| `_IMPLAUSIBLE_VOLATILITY_THRESHOLD` | `Decimal("0.50")` annualised | Geblokkeerd-by-volatility gate (in label translator — **distinct from `forecasting_step.EXCESSIVE_VOLATILITY_THRESHOLD = 1.00`**, see §10) |
| `_ZERO` | `Decimal("0")` | helper |

### 7.2 Decision tree (`translate_to_label`, `label_translator.py:54-118`)

Sequential gates — first match wins:

**Tier 1 — Block reasons trump every label rule** (`:75-92`):

| Order | Condition | Label / block_reason |
|---|---|---|
| 1.1 | `freshness == "stale"` | `Geblokkeerd / data_stale` (`:76-77`) |
| 1.2 | `freshness == "unavailable"` | `Geblokkeerd / data_unavailable` (`:78-81`) |
| 1.3 | `history_closes_count < 200` | `Geblokkeerd / insufficient_history` (`:82-85`) |
| 1.4 | `expected_volatility_annualized > 0.50` | `Geblokkeerd / implausible_volatility` (`:86-92`) |

**Tier 2 — Sell-side** (`:94-105`) — require `user_holds_position`:

| Order | Condition | Label |
|---|---|---|
| 2.1 | `prob_positive ≤ 0.25 AND prob_loss_gt_5pct ≥ 0.40` AND user_holds | `Verkopen` (`:96-100`) |
| 2.2 | `prob_positive ≤ 0.35 AND p50_log_return < 0` AND user_holds | `Verminderen` (`:101-105`) |

**Tier 3 — Buy-side** (`:107-113`) — no holding required:

| Order | Condition | Label |
|---|---|---|
| 3.1 | `prob_positive ≥ 0.65 AND p50_log_return > 0 AND prob_loss_gt_5pct ≤ 0.15` | `Kopen` (`:108-113`) |

**Tier 4 — Residual** (`:115-118`):

| Order | Condition | Label |
|---|---|---|
| 4.1 | user_holds | `Houden` (`:116-117`) |
| 4.2 | else | `Bekijken` (`:118`) |

### 7.3 Confidence parameter is accepted but unused in the label decision

`label_translator.py:67-71` is explicit:

> "Accepted for audit-completeness but not used in the label decision — the block_reason branches handle data quality."

The `confidence` argument is marked `# noqa: ARG001` at `:59` and only the block-reason branches at §7.2 tier 1 enforce data-quality gating. Confidence is persisted on the `ForecastEntry` row for downstream consumers (Decision Package narrative, frontend pills) but doesn't shape the label.

## 8. Persistence (`forecasting_step.py:341-366`)

For a successful (non-blocked) forecast:

```python
entry = ForecastEntry(
    forecast_run_id=f"fcst_{uuid4().hex}",
    ...
    method="historical_bootstrap_v1",                                        # the sole predictor stamp
    forecast_valid_until=now + timedelta(days=int(horizon_days * 1.4)),     # 20 * 1.4 = 28 days
    ...
)
forecast_repo.append(entry)
```

Key fields:

- `forecast_run_id` — new uuid per asset per fire (NOT keyed on `(asset, date, method)`).
- `method = "historical_bootstrap_v1"` (`:349`).
- `forecast_valid_until = now + 28 days` (20 horizon × 1.4 buffer).
- `confidence_level`, `freshness`, `label`, `block_reason`, `prob_positive`, `prob_loss_gt_5pct`, `expected_volatility_annualized`, `p10/p50/p90_log_return`.
- `is_eligible_for_suggestions:bool = (label in ACTIONABLE_LABELS)` — derived; downstream consumers filter on this.

**Persistence-failure isolation**: if `forecast_repo.append(entry)` raises, the per-asset result lands in `persistence_failures` (`:367-375`) — the loop continues with the next asset. Per T-007 §4: "`succeeded` and `blocked_by_reason` count only **persisted** rows".

### 8.1 Storage table

The forecasts table is created by the storage migrations (T-003) — the actual table name is `forecasts` per `packages/storage/src/ai_trading_agent_storage/metadata.py` (one row per `forecast_run_id`).

### 8.2 Blocked rows still persist

Per `forecasting_step.py:385-438` — a `_persist_blocked_forecast(...)` helper builds a placeholder `ForecastEntry` for each blocked asset:

- `label = "Geblokkeerd"`
- `confidence_level = "Laag"`
- `p10/p50/p90 = Decimal("0")`
- `prob_positive = Decimal("0.5")`
- `prob_loss_gt_5pct = Decimal("0.5")`
- `expected_volatility_annualized = Decimal("0")`
- `block_reason = <one of 5 from §4>`

This means the `forecasts` table contains exactly one row per universe asset per morning_briefing fire — including blocked placeholders. Consumers (Decision Package composer at T-007 §11, action-draft composer at T-007 `worker-actions-and-reconciliation.md` §1) filter on `block_reason IS NULL`.

## 9. End-to-end timeline (one asset)

For a 252-close history, 10000 resamples, single asset:

| t (ms) | Tier | Action |
|---|---|---|
| 0 | Orchestrator | step 9 gate fires; calls `run_forecasting_step` (T-011 §6) |
| ~10 | Worker | universe resolver returns N `ConidWithContext` records |
| ~20 | Worker (per asset) | `close_provider.list_recent_closes(conid, 252)` — DB query |
| ~30 | Worker (per asset) | gate 2 stale check + gate 3 history-length check |
| ~30 | Worker | `compute_historical_bootstrap_forecast(...)` enters |
| ~50 | numpy | `np.random.default_rng(rng_seed)` + block-bootstrap loop (10000 × 4 blocks = 40k random samples) |
| ~80 | numpy | quantiles + means + std + sqrt |
| ~90 | Worker | gate 5 volatility check (`> 1.00`?) |
| ~95 | Worker | `derive_confidence` + `translate_to_label` (pure-function tier check) |
| ~100 | Worker → DB | INSERT `ForecastEntry` row |

For N=20 universe assets, the full forecast loop is roughly N × ~80 ms = ~1.6 s of CPU + N DB roundtrips. The dominant time is in numpy bootstrap, not I/O.

`ForecastingStepResult` is then folded into the morning-chain audit row under key `"forecast"` (T-011 §6 step 12).

## 10. Two volatility thresholds — distinct constants

There are **two volatility-related cutoffs**, easy to confuse:

| Constant | File:line | Threshold | Effect |
|---|---|---|---|
| `EXCESSIVE_VOLATILITY_THRESHOLD` | `forecasting_step.py:71` | `Decimal("1.00")` | gate 5: blocks the forecast with `block_reason="excessive_volatility"` |
| `_IMPLAUSIBLE_VOLATILITY_THRESHOLD` | `label_translator.py:44` | `Decimal("0.50")` | inside the label translator: re-checks vol and emits `Geblokkeerd / implausible_volatility` |

A forecast with `expected_volatility_annualized = 0.80` (annualised 80%) passes gate 5 (`< 1.00`) BUT trips the label translator's check (`> 0.50`) → ends up with `label="Geblokkeerd"`, `block_reason="implausible_volatility"`. So gate 5 is the upper-upper bound (>100% vol is computationally suspect); the label translator's lower threshold is the practical "this looks like noise, don't act on it" gate.

**Both gates exist by design** (T-007 §4 + §6 documents the split). The split is currently undocumented at any single point; surfacing here as a Phase 1c clarity finding.

## 11. Failure paths

| Failure | Handling | Audit signal |
|---|---|---|
| `close_provider.list_recent_closes` raises | gate 1 catches → block_reason="missing_asset_listing"; placeholder row persisted | `forecasts.block_reason` |
| Empty close list | same as above | same |
| Stale close (> 3 days) | gate 2 → "stale_market_data"; placeholder row persisted | same |
| Insufficient closes (< 200) | gate 3 → "insufficient_history"; placeholder | same |
| Bootstrap raises non-`BootstrapInsufficientHistoryError` | gate 4 → "computation_error"; placeholder | same |
| `BootstrapInsufficientHistoryError` | folds to gate 3 ("insufficient_history") | same |
| Excessive volatility (> 1.00) | gate 5 → "excessive_volatility"; placeholder | same |
| Volatility 0.50–1.00 | passes upstream gates; label translator re-blocks → `Geblokkeerd / implausible_volatility`; **real** row (with bootstrap data) persisted | row has `label="Geblokkeerd"` + non-zero quantiles |
| `forecast_repo.append` raises | per-asset isolation → `persistence_failures` counter; no row written | absent from `forecasts` table |
| Whole-step exception | T-011 §6 step 9 catches → `forecast_details = {"error": "forecasting_runner_exception"}`; folded into morning-chain audit row | `scheduled_run_audit.error_details_json` |

The "never raises" contract is honoured at the per-asset + at the step level. The orchestrator additionally wraps the entire forecasting call in its own try/except (T-011 §6 control-flow point 9).

## 12. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis:

1. **ADR-0003 7-vs-1 predictor gap re-confirmed.** Worker ships `historical_bootstrap_v1` only. No GBM / momentum / mean-reversion / QVM modules. No ensemble combiner. Per ADR, explicit Phase 4 deferral.
2. **6-label vocabulary is the canonical Dutch label set** — locked by product brainstorm 2026-05-25 §Q4. `Sterk dalend / Onbepaald` 8-bucket vocabulary the T-007 task spec assumed does NOT exist.
3. **`gaps_in_last_60_days=0` hardcoded** at `forecasting_step.py:331`. Confidence deriver's gap-aware path is unreachable today; in practice every passing asset gets Hoog or Gemiddeld (never Laag from this path).
4. **Two volatility thresholds** (gate 5: 1.00 annualised; label translator: 0.50 annualised). Both intentional but undocumented at one point. T-015 §10 surfaces this.
5. **Forecast freshness scale = 3 days** vs market-data freshness scale = 15/30 minutes (T-014 §2). Per-data-domain freshness policy needed for clarity. T-014 §9.4 already flagged.
6. **`is_eligible_for_suggestions` is derived from `label in ACTIONABLE_LABELS`** — the set `{Kopen, Verminderen, Verkopen}` per T-007 §11. `Houden / Bekijken / Geblokkeerd` do NOT generate suggestions.
7. **Blocked rows persist with placeholder values** (zero quantiles, prob 0.5, vol 0). Downstream consumers MUST filter on `block_reason IS NULL` to avoid feeding noise into Decision Package composition.
8. **No per-asset rate limiting** — forecasting step iterates the full universe synchronously per fire. For 20 assets × ~80 ms = 1.6s CPU; scales linearly. Phase 4: parallelisation or sampling.
9. **`rng_seed` is plumbed through** but the default scheduler-driven invocation passes `rng_seed=None` (random) — golden-test reproducibility only kicks in when the test harness threads a fixed seed.

## 13. References

- `docs/reality/components/worker-forecasting-and-decision-package.md` §§1-6 — the source-of-truth module docs (T-007).
- `docs/reality/components/portfolio-predictors.md` — predictor protocol + backtester (T-002).
- `docs/reality/components/portfolio-money-and-accounting.md` — Decimal-as-string discipline (T-002).
- `docs/reality/workflows/morning-chain-orchestration.md` §6 — orchestrator gate that triggers this flow (T-011).
- `docs/reality/workflows/market-data-pipeline.md` §3 — Path A supplies the close-history this flow consumes (T-014).
- `docs/decisions/0003-forecast-engine-architecture.md` — locked intent (re-cited verbatim in §1).
- T-016 (future) — calibration evaluation flow consumes `forecasts` rows past `forecast_valid_until`.
- T-017 (future) — Decision Package composition consumes non-`Geblokkeerd` `forecasts` rows.
- T-018 (future) — action-draft composer routes off `is_eligible_for_suggestions`.
- T-023 (future) — AI explanation reads Decision Package + forecast for the deterministic narrative template.
- T-024 (future) — predictor backtest + leaderboard sits adjacent to this flow but does not write to `forecasts`.
