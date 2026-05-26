# Predictor lifecycle — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0014-predictor-lifecycle.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§13, §15)

## Scope

This document specifies the full lifecycle of a predictor in the ensemble: how it enters (backtest, shadow mode, promotion), how it lives (leaderboard visibility), and how it leaves (retirement). It is the source consumed by Phase 1 task T-024 (`predictor-backtest-and-leaderboard.md` reality) and Phase 4 tasks that touch the predictor stack.

## 1. Backtest methodology

### Walk-forward, mandatory

- **Rolling 12-month training window.**
- **1-month test window.**
- **Monthly step.**
- Every backtest report shows the per-step results; aggregated metrics (hit rate, Sharpe, max drawdown) are computed over the test windows, not the training windows.

### Look-ahead bias prevention

Mandatory **timestamp discipline**:

- Every data point carries `published_at`. The backtest framework **refuses** to read any data point with `published_at > simulated_time`.
- Earnings, news, calendar events: same rule. If the news was published at 14:32 and the backtest simulated time is 14:30, the news is not visible.
- Violations fail the backtest loudly; no silent skip.

### Transaction costs — mandatory

- **TOB rates per instrument type.** Sourced from `docs/intent/belgian-tax.md` and T-022 reality.
- **IBKR commission per fill.** Per the existing IBKR fee schedule.
- **Half-spread per trade.** 5 bps for liquid ETFs, 20 bps for less liquid stocks. Default classes; per-instrument override supported.

A backtest that doesn't simulate transaction costs is **not a backtest** — it's marketing.

### Survivorship correction

**Documented limitation in v1.** Every backtest report includes an explicit caveat: "Survivorship-bias correction is not applied. Historical universes that include delisted / acquired / failed instruments are not available in v1."

Phase 4 evolution candidate: add a historical-universe data source. Doctrine §15 open.

### Regime stratification

**Deferred to Phase 4.** v1 backtests report blended metrics; regime-stratified leaderboards would need a regime-detection capability that doesn't exist yet (doctrine §15 open).

## 2. Backtest cadences

- **On-add.** CI-enforced. When a new predictor module is added, CI checks that a backtest report file accompanies it. v1 enforcement is a **weak gate**: CI checks the file exists. Phase 4 evolution candidate: tighten to schema validation of the report contents.
- **Monthly scheduled.** Every active predictor is rebacktested with the most recent month of data appended; the rolling-12-month window slides forward.
- **Regime-triggered.** Phase 4 candidate (depends on regime detection).
- **On-demand.** From Category 5 of `docs/intent/settings-and-credentials.md` — "on-demand backtest trigger" button.

## 3. Leaderboard — Option C (chosen)

A read-only screen, linked from the prediction track record screen (T-016b — `docs/reality/functionality/prediction-track-record-screen.md`). Not a separate top-level entry.

### Columns per predictor

- Hit rate
- Average return
- Sharpe
- Max drawdown
- Current calibration status (green / yellow / red)
- Current ensemble weight (with 10% floor and 40% ceiling reminder)
- Last-backtest score

### Drill-down per predictor

- By asset class (equity / ETF / bond)
- By sector
- By market period (bull / sideways / bear — heuristic in v1; real regime detection deferred)
- By horizon bucket (1-week / 2-week / 4-week subset of the 20-day primary)

### Sortable columns

All columns sortable. Default sort: current ensemble weight, descending.

### Time-window toggle

3-month / 6-month / 12-month / all-time. **Default: 6-month.**

### Phase 4 evolution candidates (out of scope v1)

- Pairwise correlation across predictors
- Ensemble contribution decomposition
- Leave-one-out simulation (what would the ensemble look like without predictor X?)

### Read-only

The leaderboard does not allow direct retirement / promotion actions. Decisions still surface in the dashboard **actions area** as system-decision items (per doctrine §10 "system-decision actions").

## 4. Four-stage entry path for new predictors

1. **Backtest report.** CI-enforced (per §2). A new predictor cannot land in the codebase without an accompanying backtest.
2. **Merge as shadow-mode.** Ensemble weight fixed at **0**. The predictor's predictions are written to the prediction diary but do **not** affect live decisions. The predictor appears on the leaderboard with a `shadow` badge.
3. **3-month observation period (default; configurable in Category 3 — see `docs/intent/settings-and-credentials.md`).** During the observation period, the predictor must demonstrate:
   - **Live calibration within tolerance** (same thresholds the active ensemble uses).
   - **Live hit rate within 25% of backtest projection** (configurable). If live performance falls outside this band, the predictor stays in shadow longer or is reverted.
4. **User-decision promotion.** Once the observation period is complete and the criteria are met, the system surfaces a **system-decision item** in the dashboard actions area: "Predictor X has completed shadow-mode observation. Promote to active?" The user decides; the system does not promote automatically.

## 5. Lifecycle symmetry

- **3-month shadow** → promotion eligibility surfaces as system-decision item.
- **6-month miscalibration** → retirement eligibility surfaces as system-decision item.

**Faster to add than to remove.** This is intentional: the system is biased toward ensemble stability. A bad week doesn't trigger retirement; a bad week of a shadow predictor doesn't accelerate promotion.

## 6. After promotion

- The predictor enters the active ensemble.
- Weight evolves per **standard weighted-average-by-accuracy logic** (see `docs/intent/forecast-engine.md` §3).
- Floor 10%, ceiling 40%.
- No special handling — the predictor is now ordinary.

## 7. Shadow predictors on the leaderboard

- Visible with an explicit `shadow` status badge.
- Same metrics columns as active predictors.
- Drill-down available.
- Cannot be promoted from the leaderboard screen — promotion surfaces in actions area only (§4).

## 8. Open questions

- Shadow-mode promotion threshold (25% of backtest hit rate) — value tuning (doctrine §15)
- Predictor retirement threshold (6 months) — value tuning (doctrine §15)
- Regime detection capability (would enable regime-triggered backtests and regime-stratified leaderboard) (doctrine §15)
- Historical-universe data source for survivorship-bias correction (doctrine §15)

## 9. Cross-references

- Doctrine §13 (AI scope: predictor 6 — AI-TS — lives under case-C guardrails from `docs/intent/ai-usage.md`)
- Doctrine §15 (open questions)
- `docs/intent/forecast-engine.md` (where active predictors combine)
- `docs/intent/prediction-diary-and-calibration.md` (where calibration metrics come from)
- `docs/intent/settings-and-credentials.md` (Category 3 hosts shadow / retirement thresholds; Category 5 hosts on-demand backtest)
- `docs/intent/dashboard-and-order-flow.md` (system-decision items for promote / retire surface in actions area)
- Existing reality target: T-024 `docs/reality/functionality/predictor-backtest-and-leaderboard.md`
