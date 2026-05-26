# Forecast engine — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0003-forecast-engine-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§5, §13, §15)

## Scope

This document specifies the forecast engine: what predictors exist, how they combine, what horizon they cover, how calibration works, and what data they consume. It is consumed by `docs/intent/decision-package.md`, `docs/intent/predictor-lifecycle.md`, and `docs/intent/prediction-diary-and-calibration.md`.

## 1. Predictor scope (v1)

Seven predictors are retained for v1:

1. Historical bootstrap (baseline)
2. GBM (geometric Brownian motion)
3. Momentum
4. Mean reversion
5. QVM (Quality–Value–Momentum factor)
6. AI-TS (AI time-series; case-C feature-generating only — see doctrine §13.2)
7. Ensemble combiner (the meta-predictor that weighs the others)

Whether to simplify this set is **deferred to Phase 4**. The decision waits until Track 1c gap-analysis surfaces which predictors actually contribute signal vs noise. No simplification is made on intuition.

## 2. Horizon

**Primary horizon: 20 trading days (approximately 1 month).** Single horizon for v1.

Multi-horizon forecasting (a second 5-day stream, a third 60-day stream) is a Phase 4 evolution candidate. When to add a second horizon is doctrine §15 open.

## 3. Ensemble combination

Predictors combine into a single ensemble forecast by **weighted average by historical accuracy** (calibrated on recent live performance — see §4).

Weights are bounded:
- **Floor:** 10%. No predictor's weight drops below 10% as long as it is in the active set. Below-floor signals push the predictor toward retirement (see `docs/intent/predictor-lifecycle.md`).
- **Ceiling:** 40%. No predictor's weight exceeds 40%. This is an anti-concentration property — a single hot streak can't dominate the ensemble.

**Hard property: disagreement reduces confidence.** When predictors disagree strongly, the ensemble's confidence score (the value consumed by §5.1 conviction scaling in the doctrine) drops proportionally to the variance across predictors. Disagreement is information; the ensemble does not paper over it.

## 4. Calibration

Calibration is a **mandatory correction layer**, not optional polish.

- **Yellow on system-health** when any individual predictor drifts beyond its threshold (doctrine §15 default to be locked).
- **Red on system-health** when the **ensemble-wide** calibration drifts beyond threshold. Red ensemble calibration **stops new suggestion generation** but does **not** wipe existing forecasts from the dashboard — they remain visible with their trust signal degraded.

Calibration cadence and lifecycle live in `docs/intent/prediction-diary-and-calibration.md`. The default rolling window is **12 months** (configurable in Category 3 settings).

## 5. Data inputs (v1)

Locked for v1:

- **Price + volume:** mandatory. Cannot be turned off.
- **Fundamentals:** ON by default.
- **Earnings calendar suppression:** ON by default — do not generate suggestions in the N-day window around earnings announcements.

Deferred:

- **Macro context** (rates, FX regimes, central-bank calendar): default OFF; Phase 4 evolution candidate.
- **Alternative data** (sentiment, social, satellite, web traffic): default OFF; deferred indefinitely in v1.

Each toggle is in Category 2.1 of `docs/intent/settings-and-credentials.md`.

## 6. Data subscription tier

EODHD **All-In-One** tier (€99.99 / month) is required for v1. The cheaper tiers do not provide fundamentals + earnings together at the breadth needed. See `docs/intent/data-sources.md` for the full data-sources doctrine.

## 7. Out of scope in v1

- LLM-as-forecaster (case B from `docs/intent/ai-usage.md`). The LLM may produce **features** (case C) under three guardrails, but it may not directly emit predictions.
- Reclassifying classical ML models as "AI" (case A). Predictor 7 is the ensemble combiner; it is not an LLM.
- Multi-horizon ensembles (one horizon stream only).
- Regime detection and regime-stratified ensembles (doctrine §15 open).

## 8. Open questions

- Calibration drift thresholds (per-predictor and ensemble-wide) — doctrine §15
- Calibration window length default (currently 12 months) — doctrine §15
- When to add a second forecast horizon stream — doctrine §15
- Regime detection capability — doctrine §15
- Historical-universe data source for survivorship-bias correction — doctrine §15
- Forecast confidence score formal definition — doctrine §15

## 9. Cross-references

- Doctrine §5 (order content — quantity layer 2 consumes the ensemble confidence)
- Doctrine §13 (AI scope — case-C predictor 6 lives here)
- `docs/intent/predictor-lifecycle.md` (backtest, leaderboard, retirement, shadow promotion)
- `docs/intent/prediction-diary-and-calibration.md` (calibration cadence and event-sourced diary)
- `docs/intent/decision-package.md` (where the ensemble forecast lands)
- `docs/intent/data-sources.md` (EODHD tier + IBKR live quote split)
- `docs/intent/settings-and-credentials.md` (data feature toggles in Category 2.1)
