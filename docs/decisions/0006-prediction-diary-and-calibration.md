# 0006 — Adopt the prediction-diary and calibration lifecycle

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/prediction-diary-and-calibration.md`, `docs/intent/forecast-engine.md`, `docs/intent/predictor-lifecycle.md`, doctrine §13, §15.

## Context

T-016 (`forecast-calibration-and-prediction-diary.md` reality) raised three coupled questions:

1. Is the diary the source of truth, or a view?
2. How often do we recompute calibration?
3. When does a predictor get down-weighted vs retired?

A single combined decision is cleaner than three small ones because the three questions are tightly coupled: the diary architecture constrains the calibration cadence, which constrains the retirement signal.

## Decision

Adopt the combined architecture defined in `docs/intent/prediction-diary-and-calibration.md`:

- **Event-sourced.** Audit log is the immutable source of truth; the prediction diary is a queryable materialised view, rebuildable from the audit log.
- **Continuous daily diary closeout.** Forecasts are marked evaluated as their windows close.
- **Monthly calibration recomputation.** Rolling 6–12 month window, default 12 months. Configurable in Category 3 settings.
- **Predictor down-weighting is automatic** via the weighted-average-by-accuracy logic in `docs/intent/forecast-engine.md`. 10% floor.
- **Predictor retirement is never automatic.** After 6 months of continuous miscalibration (default, configurable), the system surfaces a system-decision item in the dashboard actions area. User decides.

## Alternatives considered

- **Diary as source of truth (not derivative).** Rejected: violates AGENTS.md "no silent data correction" — if the diary diverges from the audit log, there's no recovery path. Event-sourcing keeps the audit log canonical.
- **Daily calibration recomputation.** Rejected: too noisy. Monthly with a 12-month window matches the 20-day forecast horizon's relevant time scale.
- **Automatic predictor retirement** when a threshold is crossed. Rejected: a market regime shift can put every predictor briefly out of calibration. Automatic retirement would denude the ensemble during exactly the period when we need it most. User decision adds an explicit check.

## Consequences

- T-016 reality describes existing diary infrastructure against this intent and surfaces gaps.
- The system-decision item pattern (predictor retirement surfaces in actions area) becomes a template reused by `docs/intent/predictor-lifecycle.md` (shadow promotion) and `docs/intent/reconciliation.md` (D-class items) and `docs/intent/belgian-tax.md` (speculative-classification awareness).
- Calibration drift thresholds and retirement threshold defaults remain open in doctrine §15.
