# Reality — workflow: forecast calibration + prediction diary

**Scope.** Two distinct evaluation flows that close the loop on forecast + suggestion quality:

1. **Flow A — Calibration step** (worker, 06:00 pre_briefing): evaluates *forecasts* past their `forecast_valid_until` against realised closes. Computes `hit_status` against the locked p10/p90 band. Writes `calibration_diary` rows. Fully automated.

2. **Flow B — Prediction diary** (API, on-demand or scheduled): evaluates *suggestions* (acted advice, not raw forecasts) across 3 horizons (1d / 1w / 1m). Computes 5 outcome labels (`right` / `wrong` / `inconclusive` / `early` / `no_data`). Writes `prediction_diary_entries` rows. User-triggered or scheduler-driven.

The two flows have **different consumers, different evaluation semantics, and different storage tables** — and they together close ADR-0003's "mandatory calibration correction layer" partially (per-forecast band evaluation exists; per-predictor + ensemble drift signal does not — re-confirmed Phase 1c gap).

**Sibling reality docs:**

- `docs/reality/components/worker-forecasting-and-decision-package.md` §3 — `calibration_step.py` (T-007).
- `docs/reality/components/api-forecasting-and-market-data.md` — `POST /prediction-diary/evaluate` route + `GET /prediction-diary` (T-005).
- `docs/reality/components/storage-package-and-migrations.md` — migrations 0032, 0042, 0049 for the diary + calibration tables (T-003).
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015) — what produces the `ForecastEntry` rows Flow A evaluates.
- `docs/reality/workflows/morning-chain-orchestration.md` §8 — the orchestrator gate that triggers Flow A.
- `docs/reality/components/web-components-status-and-shared.md` §3 — `<CalibrationCoverageBadge>` consumer that reads Flow A's output.

## 0. TL;DR

**Flow A** runs at 06:00 Brussels every morning. For each expired forecast (`forecast_valid_until` is in the past AND `expired_at` IS NULL), it:

1. Looks up the realised close on the target date.
2. Computes `realized_log_return = ln(realized_close / current_price)`.
3. Decides one of 4 `hit_status` values from the issued p10/p90 band.
4. Appends a `CalibrationDiaryEntry` row.
5. Marks the forecast's `expired_at` so it never re-evaluates.

**Flow B** runs on-demand (or via a future scheduler tick). For each non-stale `AssetSuggestionRecord` linked to a forecast, it:

1. Loads market-data bars covering the suggestion's issue date + 30 days.
2. For each of 3 horizons (`HORIZON_1D_DAYS=1`, `HORIZON_1W_DAYS=7`, `HORIZON_1M_DAYS=30`), looks up the realised price.
3. For each horizon, calls `evaluate_diary_outcomes` to classify into `right` / `wrong` / `inconclusive` / `early` / `no_data` using the `inconclusive_tolerance_pct` (default `0.25`, i.e. 25%).
4. Appends a `PredictionDiaryEntryRecord` row.

**Distinction**: Flow A asks "did the issued p10/p90 band capture the realised price?" (forecast quality at one fixed horizon). Flow B asks "was the directional suggestion right or wrong at 1d / 1w / 1m?" (suggestion-outcome time-series). Both are valid signals of system quality; they cover overlapping but non-identical surfaces.

## 1. Flow A — Calibration step

### 1.1 Trigger

Per `docs/reality/workflows/morning-chain-orchestration.md` §8 + T-007 §3:

The orchestrator at 06:00 Brussels fires `mode_detected="normal"` + `run_type="pre_briefing"` and (when `calibration_runner is not None`) calls `calibration_runner.run()` — which delegates to `run_calibration_step(...)`.

Gate (`orchestrator.py:372-383`): `calibration_runner is not None AND mode_detected == "normal" AND run_type == "pre_briefing"`. **Morning_briefing (07:00) skips this step.** Calibration runs once per day at 06:00.

### 1.2 Entry point

`apps/worker/.../forecasting/calibration_step.py:74-81`:

```python
def run_calibration_step(
    *,
    forecast_repo,
    diary_repo,
    realized_close_provider,
    now_provider: Callable[[], datetime] = lambda: datetime.now(UTC),
    max_to_evaluate: int = 100,
) -> CalibrationStepResult
```

`max_to_evaluate=100` caps the per-run forecast count — prevents a backlog from monopolising one fire.

### 1.3 Algorithm (T-007 §3, verbatim from `calibration_step.py:3-12`)

> "For each forecast whose `forecast_valid_until` is in the past AND `expired_at` is still NULL:
> 1. Look up the close on the as-of-or-after target date.
> 2. Compute realized log-return = ln(realized_close / current_price).
> 3. Decide the locked `hit_status` from p10/p90.
> 4. Append one `CalibrationDiaryEntry` row.
> 5. Mark the forecast's `expired_at` so it doesn't re-evaluate."

### 1.4 The 4 locked `hit_status` values (`calibration_step.py:62-72`)

| `hit_status` | Condition | Semantics |
|---|---|---|
| `"realized_above_p90"` | `realized > p90` (`:65-66`) | forecast was too pessimistic; realised was outside the upper band |
| `"realized_below_p10"` | `realized < p10` (`:67-68`) | forecast was too optimistic; realised was outside the lower band |
| `"realized_within_p10_p90"` | `p10 <= realized <= p90` (`:69-70`) | forecast band captured the realised value — calibrated correctly |
| `"realized_outside_band"` | (fallback) (`:71`) | catch-all (should be unreachable given the first 3 cover the band) |

`hit_status="realized_within_p10_p90"` is the success signal — it means the forecast's uncertainty range captured the realised outcome. The two outside-the-band states (`realized_above_p90`, `realized_below_p10`) are mis-calibration signals; one direction would suggest systematic under-/over-prediction.

### 1.5 Inputs

- `forecast_repo.list_expired_unprocessed(now=now, limit=max_to_evaluate)` (`calibration_step.py:85-87`) — pulls forecasts past `forecast_valid_until` with `expired_at IS NULL`.
- `realized_close_provider.get_close_on_or_after(ibkr_conid=..., target_date=...)` (`calibration_step.py:94-96`, Protocol at `:33-38`) — looks up the realised price.

### 1.6 Persistence (`calibration_step.py:145-157`)

Two writes per forecast:

1. **Append to `calibration_diary`** — `CalibrationDiaryEntry(forecast_run_id, evaluated_at, realized_log_return, hit_status, realized_close_price)` via `diary_repo.append(...)` (`:145-154`).
2. **Mark forecast expired** — `forecast_repo.mark_expired(forecast_run_id, expired_at)` (`:155-157`) — prevents re-evaluation.

### 1.7 Math precision

`realized_log_return = Decimal(repr(math.log(float(realized_close) / float(forecast.current_price_local)))).quantize(Decimal("0.0000000001"))` (`calibration_step.py:132-138`) — 10 decimal places, float→str→Decimal pattern (T-002 Decimal-as-string discipline).

Passes through `float` for `math.log` but re-wraps via `repr` into Decimal — same pattern as the bootstrap output (T-015 §5.4).

### 1.8 Per-forecast error handling (boundary catches)

All failures surface as `_PerForecastResult(written=False, error="<reason>")`, **never raise** out of `run_calibration_step`:

| Failure | Resulting `error` field | File:line |
|---|---|---|
| Realized-close lookup raised | `str(exc)` | `:92-109` |
| Missing realized close | `"realized_close_not_found"` | `:110-119` |
| Non-positive `current_price_local` | `"current_price_local_not_positive"` | `:121-130` |
| Diary persist raised | (wrapped in try/except) | `:145-179` |

### 1.9 Result

`CalibrationStepResult(forecasts_evaluated, diary_rows_written, per_forecast)` (`:49-59`) with `as_audit_dict()` for the orchestrator's audit-row fold (T-011 §10).

### 1.10 Frontend consumer — `<CalibrationCoverageBadge>`

Per T-008 `web-components-status-and-shared.md` §3:

- Polls `apiClient.getCalibrationCoverage(windowDays=90)` once on mount (no interval).
- Aggregates `calibration_diary` rows over the last 90 days.
- Renders one of 3 pills (`Kalibratie: goed` / `matig` / `te weinig data`) based on hit-rate floors `0.60` / `0.40` and `MIN_SAMPLE_SIZE = 10`.

The 90-day window is fixed; the badge shows up only when forecasts past their validity-until period accumulate enough samples.

## 2. Flow B — Prediction diary

### 2.1 Trigger

Per T-005:

- **On-demand**: `POST /prediction-diary/evaluate` route (handler at `status_routes.py:2477` per T-006 §5; route line 2477 — `run_prediction_diary_evaluation`). User-triggered from the frontend or operator CLI.
- **Scheduled**: `prediction_diary_sync_enabled:bool=False` (T-006 §2, `apps/api/.../config.py:155`) — default OFF; can be flipped on for a future scheduler-driven cadence.

### 2.2 Entry point

`apps/api/.../prediction_diary_sync.py:164-265`:

```python
def evaluate_prediction_diary(
    *,
    suggestions: Iterable[AssetSuggestionRecord],
    forecasts_by_id: dict[str, AssetForecastRecord],
    bars: Iterable[MarketDataBarRecord],
    repo: _DiaryRepoProtocol,
    inconclusive_tolerance_pct: Decimal = DEFAULT_INCONCLUSIVE_TOLERANCE_PCT,
) -> PredictionDiaryReport
```

Docstring (`:172`): "Persist one diary entry per suggestion that has a linked forecast."

### 2.3 The 3 locked horizons (`prediction_diary_sync.py:41-43`)

```python
HORIZON_1D_DAYS = 1
HORIZON_1W_DAYS = 7
HORIZON_1M_DAYS = 30
```

Each horizon gets independently evaluated; one diary row carries all three outcomes. **Note**: the horizons are calendar-day deltas, not trading-day. For a Monday suggestion, the 1d horizon target is Tuesday; for a Friday suggestion, it lands on Saturday (weekend → falls forward to next trading day via `_realised_price_at` lookup).

### 2.4 The 5 locked outcome labels (`prediction_diary_eval.py:31-35`)

| Outcome | When emitted | Semantics |
|---|---|---|
| `right` | realised return is within tolerance + same direction as the suggestion | suggestion landed where expected |
| `wrong` | realised return is opposite to the suggestion's direction | suggestion was directionally wrong |
| `inconclusive` | realised return is within `inconclusive_tolerance_pct` of the issued p50 → no clear signal | flat outcome |
| `early` | direction is right but magnitude is below the tolerance (early signal not yet realised) | suggestion may yet land |
| `no_data` | no realised price was found at the target date | data gap |

### 2.5 Inconclusive tolerance — locked default

`prediction_diary_eval.py:39`:

```python
DEFAULT_INCONCLUSIVE_TOLERANCE_PCT: Final[Decimal] = Decimal("0.25")
```

**25% tolerance.** A realised return within ±25% of the issued p50 lands in `inconclusive` (Flow B's "flat" bucket). The config field `prediction_diary_inconclusive_tolerance_pct:str="0.25"` (T-006 §2, `apps/api/.../config.py:156`) is the env-override surface — runtime can adjust this without code change.

### 2.6 Per-suggestion build (`_build_entry`, `prediction_diary_sync.py:100-161`)

For each suggestion + linked forecast:

1. Look up realised prices at 3 horizons via `_realised_price_at(bars_for_conid, target_date)` (`:84-98`) — picks first available bar at or after the target date.
2. Call `evaluate_diary_outcomes(...)` (`:116-128` in `prediction_diary_eval.py:116`) — per-horizon classification.
3. Build `PredictionDiaryEntryRecord(entry_id=f"diary_{uuid4().hex}", suggestion_id, forecast_id, ibkr_conid, symbol, currency, issued_at, issued_action_label{_nl}, issued_confidence_label, issued_horizon_days, issued_price, issued_p10/p50/p90_price, issued_prob_gain, issued_prob_loss, user_decision=None, realized_price_1d/1w/1m, realized_return_pct_1d/1w/1m, outcome_label_1d/1w/1m, outcome_explanation_nl, last_evaluated_at, created_at, updated_at)` (`:129-161`).

The row carries the **full snapshot of issued values** alongside the realised values — so the diary table is a self-contained read-without-joins source for the backtest leaderboard (T-024) and frontend audit views.

### 2.7 Failure paths (`evaluate_prediction_diary`, `:164-265`)

| Failure | Counter | Mechanism |
|---|---|---|
| Suggestion has no `forecast_id` | `skipped_no_forecast += 1` (`:186-194`) | logged failure `{"suggestion_id": ..., "reason": "no_linked_forecast"}` |
| Forecast lookup misses | `skipped_no_forecast += 1` (`:195-199`) | logged failure `{"suggestion_id": ..., "reason": "forecast_not_found"}` |
| Build-row exception | `failed += 1` | result `PredictionDiaryReport(failures=[...])` |

The function returns `PredictionDiaryReport(total, persisted, skipped_no_forecast, failed, failures)` — same "never raises" pattern as Flow A.

### 2.8 Per-predictor contributions table

Migration `0042_prediction_diary_per_predictor.py` adds a `prediction_diary_predictor_contributions` table. This decomposes one diary entry into per-predictor outcome rows — supports a future per-predictor calibration drift signal (ADR-0003 intent §1.4 — see §3 below). **Currently unused by the main `evaluate_prediction_diary` write path** (the code I read doesn't populate it). Phase 1c surface: the table exists but the per-predictor decomposition is not wired in the current evaluation pipeline.

## 3. ADR-0003 — calibration correction layer gap

`docs/decisions/0003-forecast-engine-architecture.md:28` locks the intent:

> "**Mandatory calibration correction layer** with yellow / red on system-health for per-predictor / ensemble drift. Red ensemble drift stops new suggestion generation but keeps existing forecasts visible."

**Reality** (re-confirmed Phase 1c surface):

| Intent component | Reality |
|---|---|
| Per-forecast band evaluation (4 hit_status) | ✓ Flow A implements this |
| Per-predictor drift signal | ✗ — Flow A is single-predictor by definition (only `historical_bootstrap_v1` exists per T-015 §2) so per-predictor drift collapses to "the predictor's drift". Per-predictor table `prediction_diary_predictor_contributions` exists but is not written. |
| Ensemble-wide drift signal | ✗ — no ensemble combiner exists (T-015 §2) so no ensemble drift to measure |
| Yellow / red on system-health | ✗ — no system-health gate based on calibration; `<CalibrationCoverageBadge>` shows `goed` / `matig` / `te weinig data` but does not block suggestion generation when red |
| "Red ensemble drift stops new suggestion generation" | ✗ — suggestion generation never reads calibration_diary or prediction_diary_entries as a gate |

**Conclusion**: Flow A covers the data-collection floor of the ADR-0003 calibration layer; Flow B covers the suggestion-outcome diary. Neither closes the "red drift stops suggestion generation" loop. This is the closest Phase 4 gap to the ADR-0003 7-vs-1 predictor gap — they're complementary parts of the same locked-but-unbuilt forecast-quality system.

## 4. Storage tables

Per T-003 + the migrations inventoried:

| Table | Migration | Op | Flow | Key | Where read |
|---|---|---|---|---|---|
| `calibration_diary` | `0049_forecasts_and_calibration_diary.py` | append + forecast `mark_expired` UPDATE | A | composite (`forecast_run_id`, `evaluated_at`) | `<CalibrationCoverageBadge>` aggregation; future T-024 leaderboard |
| `prediction_diary_entries` | `0032_prediction_diary_entries.py` | append (one per suggestion) | B | `entry_id` (uuid) | `<DecisionPackageDetail>` (T-008 §3), future T-024 leaderboard |
| `prediction_diary_predictor_contributions` | `0042_prediction_diary_per_predictor.py` | (declared, not yet populated by main write path) | B (future) | composite | future per-predictor drift signal |

### 4.1 Idempotency

- **Flow A** is idempotent via the `expired_at` flip — a forecast can be evaluated exactly once. A second evaluation attempt skips because `list_expired_unprocessed` filters `expired_at IS NULL`.
- **Flow B** is NOT idempotent — repeated evaluations of the same suggestion write multiple rows (each with a fresh `entry_id`). Consumers must dedupe by `(suggestion_id, last_evaluated_at)` if they need a single canonical entry per suggestion. Phase 1c surface.

## 5. End-to-end timelines

### 5.1 Flow A — 06:00 pre_briefing fire

| t (ms) | Tier | Action |
|---|---|---|
| 0 | Orchestrator | step 11 gate fires; calls `run_calibration_step` (T-011 §8) |
| ~10 | Worker | `forecast_repo.list_expired_unprocessed(now=now, limit=100)` — returns N expired forecasts |
| ~50 | Worker (per forecast) | `realized_close_provider.get_close_on_or_after(conid, target_date)` — DB read |
| ~55 | Worker (per forecast) | `math.log(realized / current_price)` → Decimal quantize |
| ~60 | Worker (per forecast) | `_classify_hit_status(realized, p10, p90)` (one of 4 cases) |
| ~70 | Worker (per forecast) → DB | INSERT `calibration_diary` + UPDATE `forecasts.expired_at` |
| ~80 | Worker | Returns `CalibrationStepResult` |

For N=20 expired forecasts at ~80 ms each = ~1.6 s. The default `max_to_evaluate=100` caps the per-fire cost; a backlog of >100 expired forecasts would spread across multiple days.

### 5.2 Flow B — on-demand evaluation

| t (ms) | Tier | Action |
|---|---|---|
| 0 | Frontend / operator | `POST /prediction-diary/evaluate` |
| ~10 | API | Route enters; calls `evaluate_prediction_diary(...)` |
| ~50 | API | Load suggestions (one query) + forecasts (one query) + bars (one query covering all conids) |
| ~80 | API | Build `forecasts_by_id` dict + `bars_by_conid` dict |
| ~100 | API (per suggestion) | `_build_entry` — 3 horizon lookups + `evaluate_diary_outcomes` call |
| ~110 | API (per suggestion) → DB | INSERT `prediction_diary_entries` |
| ~150 | API | Returns `PredictionDiaryReport` |

For N=50 suggestions × ~30 ms each = ~1.5 s. Memory-bound on `bars_by_conid` if bars are loaded for many distinct conids.

## 6. Failure paths consolidated

| Failure | Flow | Surface | Audit row |
|---|---|---|---|
| Orchestrator gate fails (mode != normal, etc.) | A | calibration skipped | no `calibration_diary` row; orchestrator audit row carries `"calibration": null` |
| `forecast_repo.list_expired_unprocessed` raises | A | logged; step returns empty result | no `calibration_diary` row |
| Per-forecast realised-close missing | A | `_PerForecastResult(error="realized_close_not_found")` | counter in `CalibrationStepResult.per_forecast` |
| Per-forecast realised-close lookup raises | A | `_PerForecastResult(error=str(exc))` | counter |
| Diary persist raises | A | `_PerForecastResult(error=...)` | counter; forecast's `expired_at` NOT marked → will retry next morning |
| `prediction_diary_sync_enabled=False` AND no manual trigger | B | no evaluation runs | n/a |
| Suggestion has no `forecast_id` | B | `skipped_no_forecast += 1` | failure list entry |
| Forecast row missing | B | same | same |
| Build-row exception | B | `failed += 1` | failure list entry |

The "diary persist raises but `expired_at` not marked" path (Flow A) is the only case where retries happen automatically — the forecast stays in the unprocessed pool until the next 06:00 fire. Other failures are recorded silently in the per-forecast result list.

## 7. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis:

1. **ADR-0003 calibration correction layer is half-built.** Per-forecast band evaluation exists (Flow A); per-predictor + ensemble drift signal does not. Phase 4 candidate.
2. **`prediction_diary_predictor_contributions` table exists but is unused.** Migration 0042 declared the schema; the main write path (`evaluate_prediction_diary`) does not populate it. Dead schema or future-feature placeholder. Phase 1c clarification needed.
3. **Flow B is not idempotent.** Repeated evaluations of the same suggestion write multiple rows. Consumers must dedupe. Phase 4: add a UNIQUE on `(suggestion_id, last_evaluated_at)` or a "latest only" view.
4. **Flow B `prediction_diary_sync_enabled` is OFF by default** (`apps/api/.../config.py:155`). Production environments that haven't flipped the flag will accumulate no diary entries — `<DecisionPackageDetail>` panel that reads them will look empty. T-061 already documented the default-OFF pattern across the codebase.
5. **Horizons are calendar-day**, not trading-day. A Friday suggestion's 1d horizon target is Saturday → falls forward to Monday via `_realised_price_at`. This biases the 1d signal slightly toward Monday-overnight effects. Same observation as T-007 §9 for the Decision Package composer.
6. **`<CalibrationCoverageBadge>` does NOT block suggestion generation.** Even when calibration is in the `te weinig data` or `matig` state, suggestion generation continues. Per ADR-0003, red drift should stop new suggestion generation — but no such gate exists today.
7. **Flow A's `max_to_evaluate=100` cap is per-fire**, not per-account or per-symbol. A user with 200 expired forecasts would see 100 evaluate at one 06:00 fire and the rest at the next. Forecasts older than ~2 days could pile up if the worker is unavailable. Phase 4: configurable backfill cadence.
8. **`DEFAULT_INCONCLUSIVE_TOLERANCE_PCT = 0.25` is generous.** A 25% tolerance means any return within ±25% of the issued p50 lands in `inconclusive`. For a 20-day forecast with a typical p50 return of ~1%, the band is ±0.25% — narrow. For a high-vol asset with p50=5%, the band is ±1.25% — quite wide. Phase 4: per-asset-class tolerance or absolute (vs percentage) tolerance.
9. **Flow A's "single-predictor" reality means `hit_status` IS the per-predictor calibration signal today** — there's only one predictor, so per-forecast = per-predictor. When (if) ADR-0003's 7-predictor intent is honoured, Flow A's evaluation needs to be per-predictor row, not per-forecast row.

## 8. Out of scope

- **Forecast generation** (T-015) — what produces the rows Flow A evaluates.
- **Decision Package composition** (T-017, future) — adjacent consumer.
- **Backtest leaderboard** (T-024, future) — heavy consumer of both diary tables.
- **AI explanation** (T-023, future).
- **Suggestion generation** (T-005 / T-017 sibling) — produces the rows Flow B evaluates.

## 9. References

- `docs/reality/components/worker-forecasting-and-decision-package.md` §3 — `calibration_step.py` source-of-truth doc (T-007).
- `docs/reality/components/api-forecasting-and-market-data.md` — API prediction-diary routes (T-005).
- `docs/reality/components/web-components-status-and-shared.md` §3 — `<CalibrationCoverageBadge>` consumer (T-008).
- `docs/reality/components/storage-package-and-migrations.md` — calibration + diary table migrations (T-003).
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015) — what produces the `ForecastEntry` rows.
- `docs/reality/workflows/morning-chain-orchestration.md` §§8, 10 — orchestrator gate + audit-row fold (T-011).
- `docs/decisions/0003-forecast-engine-architecture.md:28` — locked "mandatory calibration correction layer" intent.
