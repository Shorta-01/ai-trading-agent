# Gap Analysis 03 — Quant and Forecasting Gaps

**Scope.** Predictor / forecasting / backtest / calibration / leaderboard gaps. Distinct from T-044 (missing user-facing features), T-045 (incomplete implementations), T-047 (AI provider gaps), T-048 (operational gaps). Each entry uses the Track 1c 6-part format.

**Dominant gap**: ADR-0003 mandates a 7-predictor ensemble; the worker runs 1 (`historical_bootstrap_v1`). Six predictor modules exist in `packages/portfolio/`; the backtest orchestrator supports 3; only the bootstrap fires in production.

## 0. Gap matrix at a glance

13 quant-specific gap entries.

| # | Gap | Effort | MoSCoW |
|---|-----|--------|--------|
| 1 | ADR-0003 1-of-7 predictors (6th re-confirmation) | L | **Must** |
| 2 | Weight floor 5% vs intent 10% (first numeric contradiction in audit) | S | **Must** |
| 3 | Backtest transaction costs not deducted from fold returns | M | **Must** |
| 4 | Look-ahead bias prevention absent in backtester | M | Should |
| 5 | Backtest methodology drift (weekly step vs intent's monthly) | S | Should |
| 6 | Shadow-mode infrastructure absent | L | Should |
| 7 | 3-month observation period tracking absent | M | Should |
| 8 | 6-month retirement watch absent | L | Should |
| 9 | 4-stage predictor entry path 0-of-4 implemented | L | Should |
| 10 | CI-enforced backtest-on-add gate absent | S | Could |
| 11 | Monthly scheduled rebacktest absent | S | Could |
| 12 | On-demand backtest UI button absent | S | Could |
| 13 | No prediction-diary shadow flag + no promotion system-decision generator | M | Could |

**Distribution**: 3 Must + 6 Should + 4 Could. **Effort**: 5 S + 4 M + 4 L. All 3 effort sizes + 3 MoSCoW ratings exercised.

## 1. ADR-0003 1-of-7 predictors

- **Name**: Wire the remaining 6 predictor modules into the worker forecasting step.
- **Why it matters**: ADR-0003 locks a 7-predictor ensemble. The worker runtime invokes only `historical_bootstrap_v1` (per T-007 §6 + T-015 §3 + T-024 §4.2). The portfolio package defines **6 predictor modules** (`baseline_forecast.py`, `gbm_predictor.py`, `momentum_predictor.py`, `mean_reversion_predictor.py`, `qvm_factor_predictor.py`, `ai_ts_predictor.py`). The backtest orchestrator supports 3 (GBM, momentum, mean-reversion); defers 2 (QVM, AI-TS); the status of `baseline_forecast.py` is ambiguous. **None of the 6 modules reach `ForecastEntry` rows in production.** The "ensemble" is a single predictor.
- **Why this isn't T-044**: the predictors **exist as code**. Adding new predictors is build-work; wiring existing modules is integration work.
- **Where it would live**: `apps/worker/src/portfolio_outlook_worker/forecasting/forecasting_step.py:349, :406` — replace the hard-coded `method="historical_bootstrap_v1"` with iteration over the 6 portfolio-package predictors + ensemble combining via `predictor_feedback.py:195-269` (inverse-Brier weights).
- **Effort**: **Large** — 6 modules to wire, ensemble math to validate, per-predictor tests, calibration loop updated to track per-predictor outcomes. Each predictor's interface verified against `PredictorProtocol`.
- **Dependency**: T-046 §6 (shadow-mode) ideally lands first so new predictors can enter at weight=0. Without shadow, the wire-in itself is the production rollout.
- **MoSCoW**: **Must**. Closing this is the codebase's largest doctrinal gap.
- **Originating reality**: T-007 (originating), T-015 §10, T-016 §11, T-022 §10.1, T-024 §10.12 (5 re-confirmations) + T-046 (6th).

## 2. Weight floor 5% vs intent 10% — first numeric contradiction in audit

- **Name**: Change `DEFAULT_WEIGHT_CLIP_LOW` from `0.05` to `0.10`.
- **Why it matters**: `packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py:47-48` ships `DEFAULT_WEIGHT_CLIP_LOW = Decimal("0.05")` citing "§22.5". Intent §6 of `predictor-lifecycle.md` mandates "Floor 10%, ceiling 40%". Only the floor disagrees; ceiling matches at 40%. **This is the first direct numeric contradiction between code and intent found in the entire Track 1a audit.**
- **Why this isn't T-044**: the weight bound exists; the value is wrong.
- **Where it would live**: `predictor_feedback.py:47` constant change + update comment to cite intent §6 (replacing the "§22.5" reference). Plus test updates for the new clip behavior.
- **Effort**: **Small** — single constant + comment + tests.
- **Dependency**: None code-wise. Requires confirming the intent is the binding source vs whatever "§22.5" referenced.
- **MoSCoW**: **Must**. Code-intent numeric drift is a doctrine-discipline issue; the fix is trivial.
- **Originating reality**: T-024 §6 + §10.11.

## 3. Backtest transaction costs not deducted from fold returns

- **Name**: Deduct TOB + IBKR commission + half-spread from each `FoldOutcome.realised_return_pct`.
- **Why it matters**: Intent §1 of `predictor-lifecycle.md` is direct: **"A backtest that doesn't simulate transaction costs is not a backtest — it's marketing."** The current `walk_forward_backtest` (T-024 §1.3) computes `realised_return_pct` as the raw price-return of the test bar. **No TOB deduction. No IBKR commission. No half-spread.** Backtest results overstate performance by the realised transaction cost per round-trip (~0.35% TOB + ~10bps commission + ~5-20bps half-spread = ~0.5-0.7% per round-trip). Compounded across 50 folds, this can be the difference between "predictor wins" and "predictor loses".
- **Why this isn't T-044**: the backtester exists; the cost-simulation is missing from inside it.
- **Where it would live**: `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py` — extend `FoldOutcome` with `gross_return_pct` + `net_return_pct` + per-component cost fields. Use `compute_tob` (T-022 §1.3) for TOB; new commission lookup + half-spread defaults per intent §1 (5 bps liquid ETFs, 20 bps less liquid stocks).
- **Effort**: **Medium** — cost-deduction logic + per-instrument classification (TOB security class, liquidity bucket) + tests + storage extension.
- **Dependency**: T-022 §1 `compute_tob` already exists. Per-instrument liquidity classification needs a source (probably `assets_master.liquidity_bucket` if it exists; otherwise a config table).
- **MoSCoW**: **Must**. Intent's "not a backtest, it's marketing" framing is unusually strong.
- **Originating reality**: T-024 §1.3 + §10.3.

## 4. Look-ahead bias prevention absent in backtester

- **Name**: Enforce `published_at <= simulated_time` filtering across all backtest data reads.
- **Why it matters**: Intent §1 mandates "mandatory timestamp discipline" — the backtest framework **refuses** to read any data point with `published_at > simulated_time`. T-024 §1.5 grep-proved that `published_at` is **never consulted** by the backtester. `MarketBar.published_at` and similar fields exist on some domain tables but the backtester slides over `Sequence[HistoricalBar]` by index, not by timestamp filter. A late-published earnings release with `published_at` after the fold's simulated date would still leak into the fold's training window if it were in the bars.
- **Why this isn't T-044**: the column exists on data; the backtester just doesn't filter on it.
- **Where it would live**: `predictor_backtester.py:113` (`walk_forward_backtest`) — add a `simulated_time` cursor per fold + filter all data inputs to `published_at <= simulated_time`. Plus tests with deliberately late-published rows confirming filter applies.
- **Effort**: **Medium** — cursor pattern + per-data-type filter helpers + thorough tests (the failure mode is silent — leaked data still produces valid-looking outputs).
- **Dependency**: Item 3 — both touch the same fold-iteration code; combine in one change.
- **MoSCoW**: Should. Without it, backtest results may be inflated by look-ahead leakage. With single-predictor reality (item 1), the impact is bounded.
- **Originating reality**: T-024 §1.5 + §10.2.

## 5. Backtest methodology drift (weekly step vs intent's monthly)

- **Name**: Change `DEFAULT_STEP_DAYS` from `5` (weekly) to `21` (monthly) OR document the deliberate drift.
- **Why it matters**: Intent §1 specifies "Monthly step". Reality at `predictor_backtester.py:61` is `DEFAULT_STEP_DAYS = 5` — weekly. The weekly step yields **~4× more folds** with overlapping training windows. More statistical power per backtest but each fold's test bar overlaps with adjacent folds' training data. Intent's monthly step was a deliberate choice to avoid this overlap.
- **Why this isn't T-044**: the step exists; the value is debatable.
- **Where it would live**: `predictor_backtester.py:61` constant change + update intent doc OR update code to match intent.
- **Effort**: **Small** — single constant + tests (some may need to update fold expectations).
- **Dependency**: None.
- **MoSCoW**: Should — methodological clarity matters; trade-off intentional.
- **Originating reality**: T-024 §1.1 + §10.1.

## 6. Shadow-mode infrastructure absent

- **Name**: Add shadow-mode column to predictor state + filter logic for ensemble exclusion.
- **Why it matters**: Intent §4 of `predictor-lifecycle.md` mandates step 2: "Merge as shadow-mode. Ensemble weight fixed at 0. The predictor's predictions are written to the prediction diary but do not affect live decisions." T-024 §10.9 grep-proved: no `shadow` column anywhere; no weight-zero force; no filter to exclude shadow predictions. **New predictors today can only enter as "active" or "deferred-not-running"; the safe "active-but-invisible" mode is unimplementable.** Combined with item 1, this blocks the 4-stage entry path entirely.
- **Why this isn't T-044**: this is back-end infrastructure not user-facing UI.
- **Where it would live**: New `predictor_lifecycle_state` table (or `predictor_registry` extension) with columns: `predictor_code`, `mode` enum {`shadow`, `active`, `deferred`, `retired`}, `mode_started_at`, `promotion_eligible_at`. Plus `forecast_predictions` extension with `is_shadow` boolean. Plus `predictor_feedback.py` weight-clip override (weight=0 if mode=shadow).
- **Effort**: **Large** — new table + lifecycle state-machine + ensemble-combiner update + tests + migration of existing data + documentation.
- **Dependency**: Items 1, 7, 8, 9 all depend on this. Closing T-046's quant gaps in order: shadow infra (this) → observation tracking (item 7) → retirement watch (item 8) → 4-stage path (item 9) → close ADR-0003 via item 1.
- **MoSCoW**: Should. Required for safe predictor rollout (item 1's Must lift) but technically item 1 could land without shadow mode if the new predictors are deemed safe to ship live.
- **Originating reality**: T-024 §10.9.

## 7. 3-month observation period tracking absent

- **Name**: Add observation-period tracking columns + threshold logic.
- **Why it matters**: Intent §4 step 3 of `predictor-lifecycle.md`: "3-month observation period... the predictor must demonstrate live calibration within tolerance + live hit rate within 25% of backtest projection." T-024 §10.14 grep-proved: no `shadow_start_date`, no `promotion_eligibility_at`, no thresholds in settings.
- **Why this isn't T-044**: this is back-end tracking, not UI.
- **Where it would live**: Extension of item 6's `predictor_lifecycle_state` table with `mode_started_at`, `promotion_eligible_at`. Thresholds: `Category 3 trading_settings` extension (also currently absent per T-029 §8 — cross-ref to T-048 settings infrastructure).
- **Effort**: **Medium** — schema + rolling-window calibration comparison + settings field + tests.
- **Dependency**: Item 6 (shadow infra) provides the row this lives on.
- **MoSCoW**: Should.
- **Originating reality**: T-024 §10.14.

## 8. 6-month retirement watch absent

- **Name**: Build rolling-6-month calibration watcher with system-decision item for retirement eligibility.
- **Why it matters**: Intent §5 of `predictor-lifecycle.md`: "6-month miscalibration → retirement eligibility surfaces as system-decision item." T-024 §10.10 grep-proved: no rolling 6-month calibration aggregator + no retirement system-decision item generator. Combined with the absent system-decision infrastructure generally (T-018 / T-028 cross-ref), the entire retirement-eligibility pipeline is missing.
- **Why this isn't T-044**: closely related to T-044 §12 (speculative classification system-decision items) but predictor-lifecycle-specific.
- **Where it would live**: New `predictor_calibration_rollup` materialised view OR scheduled aggregation. Plus system-decision item generator (the broader missing piece per T-044 §12 cross-ref). Plus the dashboard actions-area surface to render decisions.
- **Effort**: **Large** — aggregation pipeline + decision-item infrastructure + UI surface. The 2 dependencies (system-decision infra + actions-area UI) are themselves multi-effort items.
- **Dependency**: Item 6 (shadow infra has the lifecycle row). System-decision item generator (cross-ref T-018-related — also absent).
- **MoSCoW**: Should.
- **Originating reality**: T-024 §10.10.

## 9. 4-stage predictor entry path 0-of-4 implemented

- **Name**: Implement the full intent §4 4-stage path: backtest CI gate → shadow merge → 3-month observation → user-decision promotion.
- **Why it matters**: T-024 §10.8 documented: **0 of 4 stages are implemented end-to-end**. Backtest tooling exists (stage 1's tooling per T-024 §1) but the CI gate (1's enforcement, item 10 below) + shadow merge (2 — item 6) + observation (3 — item 7) + promotion system-decision (4 — item 14 + cross-ref T-044 §12) all absent.
- **Why this isn't T-044**: this is back-end orchestration; the user-facing surface (promotion item) is partly T-044 territory.
- **Where it would live**: Composite of items 6 + 7 + 8 + 10 + 14. T-046 lists this as a "summary" gap to capture the cumulative effort.
- **Effort**: **Large** — sum of dependent items.
- **Dependency**: Items 6, 7, 8, 10, 14 (this gap is the composite). Closing each closes part of this.
- **MoSCoW**: Should — composite work; not blocking single-predictor v1.
- **Originating reality**: T-024 §10.8.

## 10. CI-enforced backtest-on-add gate absent

- **Name**: Add a CI check that every new predictor module PR includes a backtest report file.
- **Why it matters**: Intent §2: "On-add. CI-enforced. When a new predictor module is added, CI checks that a backtest report file accompanies it. v1 enforcement is a weak gate: CI checks the file exists." T-024 §10.4 grep-proved no such CI rule exists in `.github/workflows/ci.yml`. A new predictor PR can land without any backtest evidence.
- **Why this isn't T-044**: CI tooling, not user feature.
- **Where it would live**: New `.github/workflows/predictor-backtest-gate.yml` (or inline in `ci.yml`) running a path-filter check: if `packages/portfolio/src/.../*_predictor.py` changed, require `packages/portfolio/tests/backtests/<predictor>_backtest.{md,json}` to exist.
- **Effort**: **Small** — ~30 LOC of CI YAML + a sample backtest-report template + docs.
- **Dependency**: None.
- **MoSCoW**: Could — weak gate per intent's own framing; nice-to-have.
- **Originating reality**: T-024 §10.4.

## 11. Monthly scheduled rebacktest absent

- **Name**: Add APScheduler job that rebacktests every active predictor monthly with rolling-window slide.
- **Why it matters**: Intent §2: "Monthly scheduled. Every active predictor is rebacktested with the most recent month of data appended; the rolling-12-month window slides forward." T-024 §10.5 grep-proved no APScheduler job exists for backtest. Combined with item 1 (only 1 predictor), the gap is dormant — there's no ensemble to monthly-re-evaluate. With items 1 + 11 closed, predictor weights would refresh per intent.
- **Why this isn't T-044**: this is back-end orchestration.
- **Where it would live**: `apps/worker/src/portfolio_outlook_worker/scheduler.py` — new monthly cron job invoking `run_predictor_backtest` per active predictor.
- **Effort**: **Small** — cron registration + handler that iterates active predictors + tests.
- **Dependency**: Items 1, 6 (need active + shadow predictors to backtest).
- **MoSCoW**: Could.
- **Originating reality**: T-024 §10.5.

## 12. On-demand backtest UI button absent

- **Name**: Add the Category 5 "On-demand backtest trigger" button to settings UI.
- **Why it matters**: Intent §2: "On-demand. From Category 5 of settings — 'on-demand backtest trigger' button." T-024 §3.1 documented `POST /predictor/backtest/run` exists but is feature-gated off (`predictor_backtest_enabled=False` default) + no UI button surfaces it.
- **Why this isn't T-044**: the API exists, only the frontend trigger is missing — closer to "incomplete" than "missing feature".
- **Where it would live**: Extension of `apps/web/app/instellingen/page.tsx` (Category 5 not yet implemented per T-029 §3) OR new admin page `apps/web/app/admin/predictors/page.tsx` (predictor leaderboard already in T-044 §4 — could combine).
- **Effort**: **Small** — button + confirmation + API call + result rendering.
- **Dependency**: T-044 item 4 (predictor leaderboard UI) — natural co-location.
- **MoSCoW**: Could.
- **Originating reality**: T-024 §3.1 + §10.6.

## 13. No prediction-diary shadow flag + no promotion system-decision generator

- **Name**: Add `is_shadow` to `ForecastEntry` + build predictor-promotion system-decision item generator.
- **Why it matters**: Composite of T-024 §10.13 + §10.15. (a) `ForecastEntry` (per T-016 §1, migration `0049`) has no `is_shadow` column — even if shadow infra existed (item 6), the prediction diary would be unable to distinguish shadow from live predictions. (b) Intent §4 step 4 mandates a system-decision item ("Predictor X has completed shadow-mode observation. Promote to active?") — no code emits this. The action-draft composer (T-018) handles only trade-side system-decision items.
- **Why this isn't T-044**: back-end infrastructure for predictor lifecycle.
- **Where it would live**: (a) `ForecastEntry` schema extension + Alembic migration. (b) New `predictor_promotion_decisions` table + worker job that scans observation-eligible predictors and emits decision items.
- **Effort**: **Medium** — schema + write-site updates + decision-item generator.
- **Dependency**: Items 6, 7. Without those, this has nothing to flag.
- **MoSCoW**: Could.
- **Originating reality**: T-024 §10.13 + §10.15.

## 14. Cross-reference: gap coverage across Track 1c siblings

| Gap | Covered in T-046 | Cross-ref to | Reason |
|-----|------------------|--------------|--------|
| Predictor leaderboard UI (T-024 §10.7) | No | T-044 (item 4) | User-facing surface |
| On-demand backtest UI (T-024 §10.6) | Item 12 (briefly) | T-044 (item 4 co-location) | UI button |
| AI-TS predictor Case B drift (T-024 §4.1 + T-023 §10.11) | No | T-047 | AI integration deep dive |
| System-decision item generator (T-018-related) | Items 8, 13 (referenced) | T-044 (item 12 speculative-class) + T-048 | Cross-cutting infrastructure |
| Trading settings Category 3 (T-029 §8) | Item 7 (referenced) | T-048 | Settings infrastructure |
| ADR-0003 1-of-7 (T-024 §10.12) | **Item 1 — covered fully** | (none) | Core T-046 territory |

## 15. Summary

13 quant-specific gap entries. **Distribution**: 3 Must + 6 Should + 4 Could. The 3 Musts are the quant correctness floor:

- **Item 1**: ADR-0003 — close the 1-of-7 gap. The codebase's largest single doctrinal gap, 6th re-confirmation.
- **Item 2**: Weight floor 5%→10% — the first numeric contradiction in the audit. Trivial fix, doctrine-discipline-critical.
- **Item 3**: Backtest transaction costs — intent says "not a backtest, it's marketing" if costs are absent. Direct intent rebuttal.

The 6 Shoulds form the **predictor lifecycle infrastructure**: shadow (6) → observation (7) → retirement (8) → 4-stage entry (9). Plus methodological items: look-ahead prevention (4), methodology drift (5).

The 4 Coulds are nice-to-haves: CI gate (10), monthly rebacktest (11), on-demand UI button (12), shadow flag + decision generator (13).

**Total quant work to close all 13 gaps**: meaningful but bounded. Item 1 (the Large lift) is by far the highest-leverage — it converts the system from "1-predictor 'ensemble'" to "actual ensemble". Items 2 + 3 are very small / very high-value. Phase 2 backlog should sequence: 2 (trivial) → 3 → 1 (the main lift) → 6-9 (lifecycle infra) → 4-5 (methodology) → 10-13 (process polish).

## 16. References

- T-007 `worker-orchestration-and-scheduling.md`, `worker-forecasting-and-decision-package.md` (worker forecasting reality)
- T-015 `forecast-generation-and-labelling.md` (forecast pipeline + ADR-0003 originating)
- T-016 `forecast-calibration-and-prediction-diary.md` (calibration + diary)
- T-024 `predictor-backtest-and-leaderboard.md` (T-046's primary source — 15 findings map mostly 1:1)
- T-022 `belgian-tax-computation.md` (`compute_tob` available for item 3)
- T-029 `user-edit-trading-settings.md` §8 (Category 3 absent — cross-ref for items 7+)
- T-044 §4, §12 (cross-references)
- T-045 (incomplete-implementation siblings)
- `docs/intent/predictor-lifecycle.md` (locked 2026-05-26 — the primary intent source)
- `docs/decisions/ADR-0003` (the 7-predictor lock)
- `docs/intent/forecast-engine.md` (where active predictors combine)
- `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py:1-409` (the existing harness)
- `packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py:47-48` (the 5% floor — item 2)
- `apps/worker/src/portfolio_outlook_worker/forecasting/forecasting_step.py:349, :406` (the 1-predictor lock — item 1)
