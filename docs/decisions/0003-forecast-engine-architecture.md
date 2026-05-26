# 0003 — Adopt the forecast engine architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/forecast-engine.md`, `docs/intent/prediction-diary-and-calibration.md`, `docs/intent/predictor-lifecycle.md`, doctrine §5 and §13.

## Context

During the T-011 to T-024 functional review on 2026-05-26, the discussion around T-015 (`forecast-generation-and-labelling.md` reality) and T-016 (`forecast-calibration-and-prediction-diary.md` reality) revealed three open architectural questions:

1. How many predictors should v1 carry?
2. What is the primary forecast horizon, and is it singular or multi-?
3. What is the rule for combining predictor outputs into an ensemble forecast?

Without a written answer, each subsequent task (decision package composition, dashboard trust signal, leaderboard) would re-litigate the same points from scratch.

## Decision

Adopt the forecast-engine architecture defined in `docs/intent/forecast-engine.md`:

- **Seven predictors retained** for v1. Simplification deferred to Phase 4 after gap-analysis verdict.
- **Single 20 trading day horizon** (~ 1 month). Multi-horizon is a Phase 4 candidate.
- **Weighted-average-by-historical-accuracy** ensemble with a 10% weight floor and 40% ceiling. Strong predictor disagreement reduces combined confidence by design.
- **Mandatory calibration correction layer** with yellow / red on system-health for per-predictor / ensemble drift. Red ensemble drift stops new suggestion generation but keeps existing forecasts visible.
- **EODHD All-In-One** data tier required.

## Alternatives considered

- **Trim to three predictors before Phase 1 reality.** Rejected: without Track 1c gap analysis, the decision would be intuition-driven. Phase 4 has the right data.
- **Multi-horizon ensembles in v1** (e.g. parallel 5-day / 20-day / 60-day streams). Rejected: the UI surface already takes work to land coherently for one horizon; adding two more triples the complexity for marginal signal gain.
- **Simple unweighted average ensemble.** Rejected: ignores the historical-accuracy signal; equivalent to giving a bad predictor the same say as a good one.

## Consequences

- Phase 1 reality tasks (T-015, T-016, T-024) describe existing code against this intent; gaps surface in T-046 (`03-quant-and-forecasting-gaps.md`).
- The 10%/40% bound is a hard constraint future predictor work must respect.
- Phase 4 will queue: predictor-set simplification review, multi-horizon evaluation, regime detection, survivorship-bias correction.
