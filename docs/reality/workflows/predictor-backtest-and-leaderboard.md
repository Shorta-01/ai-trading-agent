# Predictor Backtest + Leaderboard — Backtester Shipped, Lifecycle Surfaces Absent

**Scope.** End-to-end trace of the predictor lifecycle surface — from the walk-forward backtest harness (`predictor_backtester.py`, 409 LOC) through the `predictor_backtest_runs` storage table (migration `0041`) to the 4 leaderboard / backtest API routes (`status_routes.py:3298…:3704`). Plus the predictor registry inventory (6 modules in portfolio package; orchestrator supports 3, defers 2; worker calls only `historical_bootstrap_v1`) and the 4-stage-entry / shadow-mode / retirement infrastructure status (mostly absent).

**Intent**: `docs/intent/predictor-lifecycle.md` (locked 2026-05-26). **Decision**: `docs/decisions/0014-predictor-lifecycle.md`. **Component reality**: T-002 `docs/reality/components/portfolio-predictors.md`, T-007 `docs/reality/components/worker-forecasting-and-decision-package.md` (where ADR-0003 1-of-7 originated). **Sibling workflows**: T-015 `docs/reality/workflows/forecast-generation-and-labelling.md` (ADR-0003 re-confirmed 4th time), T-016 `docs/reality/workflows/forecast-calibration-and-prediction-diary.md` (calibration metrics that would feed retirement watch), T-023 `docs/reality/workflows/ai-explanation-and-budget.md` (AI-TS Case-B finding).

## 0. TL;DR

| Intent locked behaviour | Reality | Status |
|-------------------------|---------|--------|
| Walk-forward backtest, 12mo window / 1mo test / monthly step | `predictor_backtester.py`: 252-day window / 21-day horizon / **5-day step** (weekly, not monthly) | **Shipped with methodology drift §10.1** |
| Look-ahead bias prevention via `published_at` filter | `published_at` columns exist on some domain tables; backtester does NOT consult them | **Gap §10.2** |
| Transaction cost simulation (TOB + IBKR commission + half-spread) | Backtester deducts none of these from fold returns; intent §1 says "A backtest that doesn't simulate transaction costs is not a backtest" | **Gap §10.3** |
| Survivorship correction | Intent itself acknowledges this is a v1 documented limitation | **Intentional v1 gap** |
| Backtest report storage | `predictor_backtest_runs` table from migration `0041` | **Shipped** |
| CI-enforced backtest-on-add gate | Not implemented | **Gap §10.4** |
| Monthly scheduled rebacktest | Not implemented — no APScheduler job for backtest | **Gap §10.5** |
| On-demand backtest button | API route exists (`POST /predictor/backtest/run`); gated off by `predictor_backtest_enabled=False`; no UI button | **Partial — §10.6** |
| Leaderboard 7-column screen | Backend API exists (4 routes); **frontend UI absent** | **Gap §10.7** |
| 4-stage predictor entry path (backtest → shadow → 3mo observation → user-decision promotion) | None of the 4 stages have infrastructure | **Gap §10.8** |
| Shadow-mode infrastructure | No `shadow` column on any table; no weight-zero force; no filtering | **Gap §10.9** |
| 6-month miscalibration retirement watch | Not implemented — no rolling-calibration watcher | **Gap §10.10** |
| Weight floor 10% / ceiling 40% | Code uses 5% floor / 40% ceiling (`predictor_feedback.py:47-48`) citing "§22.5" | **Direct contradiction §10.11** |
| 7-predictor ensemble (ADR-0003) | Worker runs **1 predictor** (`historical_bootstrap_v1`); portfolio package defines 6 predictor modules; orchestrator supports 3 + defers 2; worker invokes none of them | **ADR-0003 5th re-confirmation §10.12** |
| Prediction diary linkage with shadow flag | `ForecastEntry` has no shadow column | **Gap §10.13** |

**Net summary**: the backtest harness + leaderboard API are shipped and substantial (~409 + ~500 LOC). The full lifecycle surfaces around them (CI gate, shadow infrastructure, observation tracking, retirement, leaderboard UI, 7-predictor ensemble) are absent. The system can backtest individual predictors and serve a JSON leaderboard, but it cannot do anything else from the intent's lifecycle spec.

## 1. The walk-forward backtest harness — `predictor_backtester.py`

**Module**: `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py` (409 LOC).

**Entry points**:
- `walk_forward_backtest` — `:113` — pure walk-forward iterator returning `tuple[FoldOutcome, ...]`.
- `walk_forward_score` — aggregator that computes Brier + hit-rate + Sharpe + max-drawdown from fold outcomes.
- `run_predictor_backtest` — `:307` — top-level orchestrator entry called by the API route at §3.1.

### 1.1 Locked defaults (`:59-62`)

```python
DEFAULT_WINDOW_DAYS: Final[int] = 252  # ~1 trading year
DEFAULT_HORIZON_DAYS: Final[int] = 21  # ~1 trading month
DEFAULT_STEP_DAYS: Final[int] = 5      # one fold per trading week
MIN_FOLDS_FOR_METRICS: Final[int] = 2
```

**Methodology drift vs intent §1**: intent says "Rolling 12-month training window / 1-month test window / **Monthly step**". Reality: 252 trading days (~12 months ✓) / 21 trading days (~1 month ✓) / **5 trading days = weekly step**. The reality runs ~4× more folds than the intent specifies — more statistical power, but each fold's test window overlaps with adjacent folds' training windows, which intent's monthly-step design intentionally avoided. §10.1.

### 1.2 Fold sliding (`:150-191`)

```text
for end in range(window_days, last_fold_end + 1, step_days):
    window_bars = bars[end - window_days : end]
    test_bars = bars[end : end + horizon]
    predictor.fit(window_bars)
    prediction = predictor.predict(...)
    realised = test_bars[-1].close vs test_bars[0].close
    yield FoldOutcome(...)
```

The window slides by `step_days` (= 5 trading days = ~1 week). Each fold reuses ~95% of the prior fold's training data; only the 5 newest bars enter and the 5 oldest exit. This is the operative reason for the methodology drift — intent's monthly step would yield ~12 folds per year of history; the weekly step yields ~50.

### 1.3 `FoldOutcome` payload (`:69-82`)

```python
@dataclass(frozen=True)
class FoldOutcome:
    fold_index: int
    bars_used: int
    predicted_prob_gain: float
    predicted_direction: str
    predicted_return_pct: float
    realised_return_pct: float
    realised_indicator: int  # 1 if realised return > 0 else 0
    realised_direction: str
    direction_match: bool
```

**Note**: `realised_return_pct` is the raw price-return of the test bar — **no transaction-cost deduction**. Intent §1 mandates "TOB + IBKR commission + half-spread" be subtracted from every fold's realised return. Reality: gross returns only. §10.3.

### 1.4 Direction match (`:84-110`)

Direction labels use the locked 6-label vocabulary (T-015 §3 — `Kopen / Verminderen / Verkopen / Houden / Bekijken / Geblokkeerd` map to `STRONG_UP / SLIGHT_UP / FLAT / SLIGHT_DOWN / STRONG_DOWN`). Up-vs-up and down-vs-down count as matches. Sign mismatches don't. Flat-vs-flat counts as a match.

### 1.5 Look-ahead bias prevention — absent (§10.2)

Grep across `predictor_backtester.py:1-409` for `published_at`, `simulated_time`, `point_in_time`, `look_ahead` returns **zero hits**. The backtester reads from `Sequence[HistoricalBar]` and slides over it by index — there is no `published_at <= simulated_time` filter.

The `published_at` field exists on some domain tables (`packages/domain/src/portfolio_outlook_domain/market_calendar.py`, `sources.py`) but is not consumed by the backtester. **A late-published earnings release with a `published_at` after the fold's simulated date would still leak into the fold's "training" window** if it were in `bars`. Intent §1's "mandatory timestamp discipline" is not enforced.

## 2. Backtest report storage — `predictor_backtest_runs`

**Migration**: `packages/storage/alembic/versions/0041_predictor_backtest_runs.py:23-51`. Created mid-2026.

### 2.1 Columns

| Column | Type | Notes |
|--------|------|-------|
| `run_id` | Text PK | UUID per run |
| `model_code` | Text | `historical_bootstrap_v1` / `momentum_v1` / etc. |
| `asset_symbol` | Text | the asset the backtest ran against |
| `started_at` | DateTime tz | run start |
| `completed_at` | DateTime tz | run end (NULL if in-flight) |
| `status` | enum | `succeeded` / `skipped` / `failed` |
| `window_days / horizon_days / step_days` | Integer | the parameters used (allowing post-hoc audit of methodology drift §10.1) |
| `fold_count` | Integer | number of folds executed |
| `brier_score / hit_rate / sharpe_ratio / max_drawdown` | Decimal | aggregate metrics over fold outcomes |
| `explanation_nl` | Text | Dutch one-line summary of the run outcome |
| `blocking_reason` | Text | populated when status=`skipped` or `failed` |

### 2.2 Index

`(model_code, asset_symbol, started_at DESC)` — latest-per-pair lookup is the hot path for the `/predictor/backtest/latest` route (§3.2).

### 2.3 Repository

`SqlAlchemyPredictorBacktestRunRepository` lives in `packages/storage/src/ai_trading_agent_storage/sql_repositories.py`. The repo is the only writer; `run_predictor_backtest` at `predictor_backtester.py:307` is the only caller of `repo.append(...)`.

## 3. The 4 leaderboard / backtest API routes

**Module**: `apps/api/src/portfolio_outlook_api/status_routes.py:3298-3797` (~500 LOC of routes + helpers).

### 3.1 `POST /predictor/backtest/run` (`:3298-3402`)

Accepts `{model_code, asset_symbol, ibkr_conid, window_days?, horizon_days?, step_days?}`. Synchronously calls `run_predictor_backtest`; persists a `predictor_backtest_runs` row.

**Feature gate**: `settings.predictor_backtest_enabled` (`config.py:202` — **defaults to False**). When disabled, the route returns a Dutch help string explaining how to enable. §10.6.

### 3.2 `GET /predictor/backtest/latest` (`:3405-3463`)

Returns the most-recent `predictor_backtest_runs` row per `(model_code, asset_symbol)` pair — the data the leaderboard would render. Always returns the underlying rows even when `predictor_backtest_enabled=False` (read paths are not feature-gated).

### 3.3 `GET /predictor/backtest/history` (`:3466-3523`)

V1.1 Slice 33: returns the full time-series of backtest runs for a single `(model_code, asset_symbol)` pair — feeds a trend chart that does not exist on the frontend.

### 3.4 `GET /predictor/leaderboard` (`:3704-3797`)

The main leaderboard payload. Aggregates the latest Brier score per predictor and computes inverse-Brier auto-weights (`:3769`). Auto-weight formula uses the same `DEFAULT_WEIGHT_CLIP_LOW=0.05` / `DEFAULT_WEIGHT_CLIP_HIGH=0.40` bounds from `predictor_feedback.py:47-48`.

### 3.5 Leaderboard surface vs intent §3 column inventory

| Intent column (§3) | Reality (response field) | Status |
|---------------------|---------------------------|--------|
| Hit rate | `hit_rate` from `predictor_backtest_runs` | **Yes** |
| Average return | derivable from fold outcomes | not aggregated as a column |
| Sharpe | `sharpe_ratio` | **Yes** |
| Max drawdown | `max_drawdown` | **Yes** |
| Current calibration status (green/yellow/red) | not in payload — `forecast_calibration` is a separate table (T-016) | **Gap** |
| Current ensemble weight | `auto_weight_clipped` (inverse-Brier; not the user-adjustable runtime weight, since none exists) | **Partial** |
| Last-backtest score | derived from latest run | **Yes** |

The leaderboard payload covers 5 of 7 intent columns. The "drill-down by asset class / sector / market period / horizon bucket" (intent §3) requires multi-dimensional aggregation that does not exist in the route.

## 4. The predictor registry — 6 modules, 1 runtime

### 4.1 Portfolio-package predictor modules (6 found)

`packages/portfolio/src/portfolio_outlook_portfolio/`:

| Module | Purpose | Wired? |
|--------|---------|--------|
| `baseline_forecast.py` | unclear from grep; likely used in tests | unclear |
| `gbm_predictor.py` | Geometric Brownian Motion | locked in orchestrator `LOCKED_MODEL_CODES` (line 41) |
| `momentum_predictor.py` | momentum factor | line 151 — supported |
| `mean_reversion_predictor.py` | mean-reversion factor | line 157 — supported |
| `qvm_factor_predictor.py` | quality-value-momentum factor | **deferred** to Slice 28 (line 164 — SKIPPED) |
| `ai_ts_predictor.py` | AI time-series predictor (the Case-B from T-023) | **deferred** to Slice 30 (line 166 — SKIPPED) |

Backtest orchestrator supports 3 of these 6 modules (GBM + momentum + mean-reversion); defers 2 (QVM + AI-TS); the status of `baseline_forecast.py` is ambiguous.

### 4.2 Worker runtime — 1 predictor

`apps/worker/src/portfolio_outlook_worker/forecasting/forecasting_step.py:349, :406`:

```python
method="historical_bootstrap_v1",
```

Hard-coded at both DB-write sites in the forecasting step. **The worker invokes none of the portfolio-package predictors at runtime**. The 6 modules above can be backtested via the API surface (§3.1) but their predictions are never integrated into the production forecast ensemble that the morning chain consumes.

### 4.3 ADR-0003 1-of-7 — 5th re-confirmation

ADR-0003 locks a 7-predictor ensemble. T-007 (originating), T-014 §10, T-015 §10 (3rd), T-016 §11 (4th), and T-024 (5th) all re-confirm the gap. The shipping picture as of T-024:

- **Worker runtime**: 1 predictor (`historical_bootstrap_v1`) — same as T-015 found.
- **Portfolio package**: 6 modules defined.
- **Backtest orchestrator**: 3 supported, 2 deferred, 1 ambiguous.
- **Active ensemble**: still 1 — the worker is the only path into the live ensemble; nothing from the portfolio modules reaches `ForecastEntry`.

The gap is not "predictors don't exist" — they do, in the portfolio package, with backtest support. The gap is that **the worker never wires them in**. Closing ADR-0003 would require wiring 6 portfolio-package modules into `forecasting_step.py`, not building new predictors.

## 5. The 4-stage predictor entry path — coverage map

| Intent §4 stage | Reality | Status |
|------------------|---------|--------|
| **(1) Backtest report on PR** | Backtest can be run on-demand via API; no CI-enforced presence-check on predictor PRs | **Gap §10.4** |
| **(2) Merge as shadow-mode with weight=0** | No `shadow` column anywhere; predictor_feedback weights are inverse-Brier auto-computed; no "force 0 if shadow" path | **Gap §10.9** |
| **(3) 3-month observation period** | No `shadow_start_date` / `observation_period_start` / `promotion_eligibility_at` column; no settings field for the observation period length | **Gap §10.14** |
| **(4) User-decision promotion via actions-area system-decision item** | No code path generates such an item; the action-draft composer (T-018) does not emit predictor-promotion items | **Gap §10.15** |

**Score: 0 of 4 stages implemented end-to-end.** The backtest tooling exists (§1-3) but the lifecycle wrapping around it is entirely absent.

## 6. Weight floor / ceiling — the direct intent contradiction

`packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py:45-48`:

```python
# Per-predictor clip band — locked by §22.5: lower 5%, upper 40% so no
# single predictor dominates and no predictor falls fully silent.
DEFAULT_WEIGHT_CLIP_LOW: Final[Decimal] = Decimal("0.05")
DEFAULT_WEIGHT_CLIP_HIGH: Final[Decimal] = Decimal("0.40")
```

**Intent §6**: "Floor 10%, ceiling 40%."

**Code**: "Lower 5%, upper 40% — locked by §22.5."

The code comment cites a different source (§22.5) than the intent doc (§6). The ceilings match (40%); the floors disagree (5% vs 10%). Operationally: a low-performing predictor in the active ensemble drops to 5% weight in reality, half of what intent permits as the minimum. Intent's "no predictor falls fully silent" property is preserved, but with a more aggressive minimum than intent locked.

This is the **first direct numeric contradiction** found in the reality audit between code and intent. Other findings have been about absent surfaces; this one is about a specific number being wrong. §10.11.

## 7. Shadow-mode + retirement — entirely absent

### 7.1 No shadow infrastructure (§10.9)

Grep across `packages/storage/src/ai_trading_agent_storage/metadata.py` for `shadow`, `is_active`, `mode`, `status` on any predictor-related table returns **zero matches**. No column to mark a predictor as shadow; no code path to force its weight to 0; no filter to exclude shadow predictions from the live ensemble.

Consequence: a new predictor cannot be merged as "shadow" today. The available options are: (a) merge it as active (intent forbids without 3-month observation), or (b) merge it with the orchestrator gate set to "deferred" (the current state of QVM + AI-TS — §4.1), which means it doesn't run at all, not even in shadow.

### 7.2 No retirement watch (§10.10)

Intent §5 mandates "6-month miscalibration → retirement eligibility surfaces as system-decision item". Reality: no rolling 6-month calibration watcher exists. `forecast_calibration` table (T-016 §3) is read per-call by the morning chain but is never aggregated over a 6-month rolling window to produce a retirement-eligibility signal.

The retirement surface (a system-decision item in the actions area) would also need to be wired — T-018 documents 0 predictor-related system-decision items.

### 7.3 No prediction-diary shadow flag (§10.13)

`ForecastEntry` (T-016 §1, migration `0049`) has no `is_shadow` / `shadow` / `mode` column. Even if shadow-mode infrastructure existed, the prediction diary would be unable to distinguish a shadow prediction from a live one — intent §4 step 2 mandate that "shadow predictions are written to the prediction diary" is structurally unimplementable today.

## 8. End-to-end timeline — an on-demand backtest

| t | Site | Event |
|---|------|-------|
| 0 | operator | `POST /predictor/backtest/run` with `{model_code, asset_symbol}` |
| 0 | `status_routes.py:3298` | route handler entered |
| 0+ε | `settings.predictor_backtest_enabled` check | aborts with Dutch help string if False |
| 0+ε | bars fetched from `market_data_*` (T-014) | historical price series loaded |
| 0+ε | `predictor_backtester.py:307` `run_predictor_backtest` | orchestrator entered |
| 0+ε | `walk_forward_backtest` (`:113`) | folds iterated (252-day window, 5-day step) |
| 0+ε | `walk_forward_score` | Brier + hit-rate + Sharpe + max-DD computed |
| 0+ε | `repo.append(...)` | `predictor_backtest_runs` row persisted |
| 0+ε | route returns | JSON with metrics + Dutch explanation |
| later | another operator | `GET /predictor/leaderboard` reads the row + computes inverse-Brier auto-weight |

There is no scheduled monthly rebacktest (§10.5). There is no CI presence check (§10.4). There is no UI button (§10.6). The path exists; the surfaces around it are missing.

## 9. Failure paths

1. **Insufficient bars** → backtester returns `MIN_FOLDS_FOR_METRICS=2`-gated empty result; status=`skipped` with `blocking_reason="insufficient_history"`.
2. **Predictor crashes during fold** → exception caught at orchestrator; status=`failed`, error message in `blocking_reason`.
3. **`predictor_backtest_enabled=False`** → route returns 200 with Dutch help; no row persisted.
4. **Look-ahead-tainted prediction** → not detected; fold proceeds as if data were valid (§10.2 / §1.5).
5. **Backtest underestimates real cost** → not detected; intent §1 "TOB + commission + spread" deductions skipped (§10.3).

## 10. Phase 1c surface (15 findings)

1. **Methodology drift: weekly step, not monthly** — `predictor_backtester.py:61` uses `DEFAULT_STEP_DAYS=5`; intent §1 mandates monthly step. Reality yields ~4× more folds with overlapping windows. More statistical power; less methodological match to intent.
2. **Look-ahead bias prevention absent in backtester** — `published_at` fields exist on some domain tables but are never consulted by `predictor_backtester.py`. Intent §1 "mandatory timestamp discipline" not enforced.
3. **Transaction cost simulation absent in backtest** — fold returns are raw price moves; no TOB / commission / half-spread deduction. Intent §1: "A backtest that doesn't simulate transaction costs is not a backtest — it's marketing." Direct rebuttal.
4. **CI-enforced backtest-on-add gate absent** — intent §2 mandates "weak gate" CI presence check on predictor PRs; `.github/workflows/ci.yml` has no such rule.
5. **Monthly scheduled rebacktest absent** — intent §2 mandates "Every active predictor is rebacktested with the most recent month of data appended". No APScheduler job for backtest; no recurring tick.
6. **On-demand backtest UI button absent** — API route exists (`POST /predictor/backtest/run`) but feature-gated off by default + no frontend button. Intent §2 mentions a "button in Category 5 of settings".
7. **Leaderboard UI absent** — backend serves the data via 4 routes; no frontend page renders it. Intent §3 mandates a "read-only screen linked from prediction track record screen (T-016b)". T-016b itself is still queued (not started).
8. **4-stage predictor entry path implemented at 0 of 4 stages** — backtest tooling exists (stage 1's tooling), but the CI gate (stage 1's enforcement), shadow merge (stage 2), 3-month observation (stage 3), and promotion system-decision item (stage 4) are all absent.
9. **Shadow-mode infrastructure absent** — no `shadow` column anywhere; no weight-zero force; no shadow-aware ensemble combiner. New predictors today can only enter as "active" or "deferred-not-running"; the safe "active-but-invisible" mode of intent §4 step 2 is unimplementable.
10. **6-month miscalibration retirement watch absent** — no rolling calibration window aggregator; no retirement system-decision item generator.
11. **Weight floor 5% vs intent's 10% — direct numeric contradiction** — `predictor_feedback.py:47` uses `DEFAULT_WEIGHT_CLIP_LOW=0.05`, citing `§22.5`; intent `predictor-lifecycle.md` §6 mandates 10%. Only the floor disagrees; ceiling matches at 40%. First numeric contradiction found in the reality audit.
12. **ADR-0003 1-of-7 — 5th re-confirmation** — worker runtime invokes only `historical_bootstrap_v1` despite portfolio package defining 6 predictor modules and the backtest orchestrator supporting 3 of them. Closing the gap requires wiring 6 modules into `forecasting_step.py:349, :406`; the modules themselves exist.
13. **Prediction-diary shadow flag absent** — `ForecastEntry` (T-016 §1) has no `is_shadow` column. Even if shadow-mode existed, intent §4 step 2's "shadow predictions written to prediction diary" mandate is structurally unimplementable.
14. **3-month observation period tracking absent** — no `shadow_start_date` / `observation_period_start` / `promotion_eligibility_at` column on any table; no settings field for the period length. Intent §4 step 3 + §5 has no storage to land on.
15. **User-decision promotion system-decision item generator absent** — no code emits "Predictor X has completed shadow-mode observation. Promote to active?" The action-draft composer (T-018) handles only trade-side system-decision items, not predictor-lifecycle items. Intent §4 step 4 dangling.

## 11. Out of scope (re-confirmed)

- **AI explanation surface** (T-023 — merged sibling; the AI-TS Case-B finding §10.11 of T-023 is the deferred `ai_ts_predictor.py` listed here in §4.1).
- **Market data pipeline** (T-014 — merged sibling; the source of bars the backtester consumes).
- **Forecast generation** (T-015 — merged sibling; documents the worker's single-predictor reality).
- **Forecast calibration + prediction diary** (T-016 — merged sibling; would feed the retirement watch if §10.10 were implemented).
- **Architecture review** (Track 1b T-036…T-043 future).
- **Gap analysis** (Track 1c T-044…T-049 future).
- **Performance review screen** (queue T-021b future; the closest cousin of the leaderboard intent §3 — both are read-only "show your work" surfaces that don't exist today).

## 12. References

- `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py:1-409` (walk-forward harness)
- `packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py:45-48` (weight bounds — §10.11)
- `packages/portfolio/src/portfolio_outlook_portfolio/baseline_forecast.py`, `gbm_predictor.py`, `momentum_predictor.py`, `mean_reversion_predictor.py`, `qvm_factor_predictor.py`, `ai_ts_predictor.py` (6 predictor modules — §4.1)
- `packages/portfolio/src/portfolio_outlook_portfolio/ensemble_combiner.py:72` (`weight_normalised`)
- `apps/api/src/portfolio_outlook_api/status_routes.py:3298, :3405, :3466, :3704` (4 leaderboard / backtest routes)
- `apps/api/src/portfolio_outlook_api/config.py:202` (`predictor_backtest_enabled` feature gate)
- `apps/worker/src/portfolio_outlook_worker/forecasting/forecasting_step.py:349, :406` (hard-coded `method="historical_bootstrap_v1"`)
- `packages/storage/alembic/versions/0041_predictor_backtest_runs.py:23-51`
- `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` (`SqlAlchemyPredictorBacktestRunRepository`)
- `docs/intent/predictor-lifecycle.md` (locked 2026-05-26)
- `docs/decisions/0014-predictor-lifecycle.md`
- `docs/decisions/ADR-0003` (the 7-predictor lock)
- `docs/reality/components/portfolio-predictors.md` (T-002)
- `docs/reality/components/worker-forecasting-and-decision-package.md` (T-007)
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015)
- `docs/reality/workflows/forecast-calibration-and-prediction-diary.md` (T-016)
- `docs/reality/workflows/ai-explanation-and-budget.md` (T-023 — Case-B finding on the deferred `ai_ts_predictor.py`)
