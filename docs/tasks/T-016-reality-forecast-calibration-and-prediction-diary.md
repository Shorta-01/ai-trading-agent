```yaml
id: T-016
title: Write reality doc for forecast calibration + prediction diary flows
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/forecast-calibration-and-prediction-diary.md` does not exist (verified). T-016 covers **two distinct evaluation flows**:
  - Flow A (calibration) — already cited in T-007 `worker-forecasting-and-decision-package.md` §3 (`apps/worker/.../forecasting/calibration_step.py`, 179 lines, runs at 06:00 pre_briefing).
  - Flow B (prediction diary) — new reads inline: `apps/api/.../prediction_diary_sync.py` (312 lines — `evaluate_prediction_diary`, 3-horizon evaluation, 5 outcome labels) + `packages/portfolio/.../prediction_diary_eval.py` (175 lines — `evaluate_diary_outcomes`, the outcome-classification helper).
  - Storage migrations: `0049_forecasts_and_calibration_diary.py`, `0032_prediction_diary_entries.py`, `0042_prediction_diary_per_predictor.py`.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the workflow doc covering both calibration + prediction-diary evaluation flows.
  - `forecast-calibration-and-prediction-diary.md` — two flows + 2 (or 3) storage tables + 4 hit_status (Flow A) + 5 outcome labels (Flow B) + 3 horizons (Flow B) + ADR-0003 calibration-correction-layer gap surfaced.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing both evaluation flows end-to-end.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; Flow A documented (worker calibration_step + 4 hit_status + `calibration_diary` table); Flow B documented (API prediction_diary_sync + 5 outcome labels + 3 horizons + `prediction_diary_entries` table); both flows' trigger models documented; ADR-0003 mandatory calibration correction layer gap surfaced; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — forecast generation (T-015), Decision Package composition (T-017), backtest leaderboard (T-024 — adjacent), AI explanation (T-023).

## Goal

Produce one workflow reality doc tracing both forecast-evaluation flows:

1. **Flow A — Calibration**: worker `calibration_step.py` runs at 06:00 pre_briefing, evaluates forecasts past `forecast_valid_until`, computes `hit_status` against p10/p90 band, writes `calibration_diary` rows.
2. **Flow B — Prediction Diary**: API `prediction_diary_sync.evaluate_prediction_diary` runs on-demand via `POST /prediction-diary/evaluate`, iterates `AssetSuggestionRecord`s, computes outcome labels across 3 horizons (1d/1w/1m), writes `prediction_diary_entries` rows.

Plus the ADR-0003 mandatory-calibration-correction-layer gap (intent: per-predictor + ensemble drift → red/yellow system-health; reality: per-forecast hit_status only).

## Context

`depends_on:` T-002, T-005, T-007. Calibration evaluation closes the loop on forecast quality. Two flows exist — one fully automated (Flow A, worker, daily) and one user-triggered (Flow B, API, on-demand). Both write to separate tables; consumers (backtest leaderboard, frontend `<CalibrationCoverageBadge>`) read different ones.

## Touch scope

Create:
- `docs/reality/workflows/forecast-calibration-and-prediction-diary.md`

Read: T-002 + T-005 + T-007 reality docs + the 2 prediction-diary files inventoried in step 1.

## Acceptance criteria

- [ ] Output file exists.
- [ ] Flow A — worker calibration_step documented (trigger: 06:00 pre_briefing + `normal` mode; algorithm; 4 hit_status cases).
- [ ] Flow B — API prediction_diary_sync documented (trigger: on-demand + scheduled `POST /prediction-diary/evaluate`; algorithm; 5 outcome labels; 3 horizons 1d/1w/1m).
- [ ] Storage tables: `calibration_diary` + `prediction_diary_entries` (+ `prediction_diary_predictor_contributions`).
- [ ] ADR-0003 "mandatory calibration correction layer" gap surfaced (per-forecast vs per-predictor + ensemble drift).
- [ ] No source modification.

## Out of scope

- Forecast generation (T-015 — what produces the rows this flow evaluates).
- Decision Package composition (T-017 — adjacent consumer).
- Predictor backtest leaderboard (T-024 — sibling that consumes calibration data).
- AI explanation (T-023).

## Verification

- File exists.
- All 4 calibration hit_status (`realized_above_p90`, `realized_below_p10`, `realized_within_p10_p90`, `realized_outside_band`) cited.
- All 5 prediction-diary outcomes (`right`, `wrong`, `inconclusive`, `early`, `no_data`) cited.
- All 3 horizons (1d/1w/1m) cited.
- Both flows' storage tables present.

## Notes

T-005 already documented `POST /prediction-diary/evaluate` route. T-016 stitches it together with the calibration story (which T-007 §3 documented at the worker step level) — without T-016 the two halves are documented separately but the dual-flow story is not.
