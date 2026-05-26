# Prediction diary and calibration — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0006-prediction-diary-and-calibration.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§13, §15)

## Scope

This document covers how the system records its own predictions, evaluates them against realised outcomes, and recalibrates predictor weights based on calibration results.

## 1. Diary architecture: event-sourced

- The **audit log** is the immutable event stream. Every forecast emitted, every fill observed, every calibration recomputation is one event.
- The **prediction diary** is a queryable materialised view derived from the audit log. It can be **rebuilt from the audit log** at any time — the diary is never the source of truth.
- Hard property: deleting the diary and rebuilding it from the audit log produces the same diary, byte-for-byte (modulo tie-breaking on simultaneous timestamps, which is deterministic).

## 2. Diary closeout cadence

- **Continuous, daily.** Each evening (after the close of the relevant market for each forecast's horizon), forecasts whose evaluation window has closed are marked evaluated. Realised return is computed against the actual price; hit / miss is recorded.

## 3. Calibration recomputation cadence

- **Monthly.** Recompute predictor accuracy metrics and update ensemble weights.
- **Rolling window: 6–12 months. Default: 12 months.** Configurable in Category 3 settings (see `docs/intent/settings-and-credentials.md`).

## 4. Predictor down-weighting

When a predictor's calibration drifts:

- **Automatic via weighted-average-by-accuracy.** No special handling — the standard ensemble logic (see `docs/intent/forecast-engine.md` §3) reduces its weight as its rolling accuracy drops.
- **Floor: 10%.** A predictor's weight cannot drop below the floor while it remains in the active set. Below-floor signals trigger the retirement path (§5).

## 5. Predictor retirement: never automatic

The system **does not** retire a predictor automatically.

After **6 months of continuous miscalibration** (default; configurable in Category 3 — doctrine §15), the system surfaces a **system-decision item** in the dashboard actions area (doctrine §10): "Predictor X has been miscalibrated for 6 months. Retire?"

The user decides. The system does not act.

This is symmetric with the shadow-mode promotion path (`docs/intent/predictor-lifecycle.md` §4): faster to add than to remove, biased toward ensemble stability.

## 6. Open questions

- Calibration drift thresholds — per-predictor and ensemble-wide values — doctrine §15
- Calibration window length default (currently 12 months) — doctrine §15
- Predictor retirement threshold default (currently 6 months) — doctrine §15

## 7. Cross-references

- Doctrine §13 (AI scope — calibration is deterministic Python, not AI)
- Doctrine §15 (open questions)
- `docs/intent/forecast-engine.md` (ensemble combination uses the calibrated weights produced here)
- `docs/intent/predictor-lifecycle.md` (retirement path UX; shadow promotion symmetry)
- `docs/intent/decision-package.md` (trust tier reads calibration status)
- `docs/intent/settings-and-credentials.md` (calibration window, retirement threshold)
