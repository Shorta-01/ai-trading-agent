```yaml
id: T-012b
title: Write reality doc for data-maturation-and-confidence-buildup functionality
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/functionality/data-maturation-and-confidence-buildup.md` does not exist (verified). Investigated the question "does explicit maturation logic exist?" by grep + read:
  - `packages/portfolio/src/portfolio_outlook_portfolio/baseline_forecast.py:36` (`MINIMUM_BARS_REQUIRED = 60`), `:193-204` (`_confidence_from_sample_size`).
  - Per-predictor min-bars: `BASELINE_FORECAST_MIN_BARS`, `MOMENTUM_MIN_BARS`, `MEAN_REVERSION_MIN_BARS`, `QVM_MIN_BARS`.
  - `apps/web/components/CalibrationCoverageBadge.tsx` + `apps/api/src/portfolio_outlook_api/forecast_routes.py:467` (`/calibration/coverage`).
  - T-015 (forecast generation) + T-016 (calibration + prediction diary) for cross-reference.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the data-maturation + confidence-buildup functionality reality doc.
  - `data-maturation-and-confidence-buildup.md` — documents that explicit maturation logic DOES exist (sample-size confidence curve 0.40→0.95 + per-predictor min-bars gates + 3-state calibration coverage badge) but is (a) bound to the single shipped predictor `historical_bootstrap_v1` (ADR-0003), (b) sample-size-driven not time-since-deployment-driven, (c) per-predictor min-bars for the 6 unwired predictors defined-but-unused. The "day 1 → mature operation" story is partially implemented via the bar-count proxy.
- **Step 3 (one-line change):** write one functionality-level reality doc answering the maturation question.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; the investigative question answered (maturation logic exists — not a pure gap); the sample-size confidence curve documented (0.40 at 60 bars → 0.95 at 252); per-predictor min-bars gates documented; calibration coverage 3-state surface documented; limitations surfaced (bound to single predictor, sample-size not time-driven); cross-references + Phase 1c framing; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — T-015/T-016 deep dives (merged siblings); T-016b / T-021b remaining functional-review additions.

## Goal

Produce one functionality-level reality doc answering the queue.md T-012b investigative question: "how do the system's suggestions evolve from day 1 (low data, low confidence) to mature operation? If no explicit maturation logic exists, the file says so and the finding becomes a Phase 1c gap entry." The answer: **explicit maturation logic DOES exist** (not a pure gap) — sample-size confidence curve + per-predictor min-bars + calibration coverage — but with limitations worth surfacing.

## Context

`depends_on:` T-005 (API forecast routes), T-007 (worker forecasting). T-015 documented forecast generation; T-016 documented calibration. T-012b answers the specific "data maturation over time" question that the 2026-05-26 functional review flagged.

## Touch scope

Create:
- `docs/reality/functionality/data-maturation-and-confidence-buildup.md`

Read: T-005 + T-007 + T-015 + T-016 reality docs + `baseline_forecast.py` + `CalibrationCoverageBadge.tsx` + `forecast_routes.py`.

## Acceptance criteria

- [ ] Output file exists at `docs/reality/functionality/data-maturation-and-confidence-buildup.md`.
- [ ] Investigative question answered (maturation logic exists — not a pure gap).
- [ ] Sample-size confidence curve documented (`_confidence_from_sample_size`: 0.40 at 60 bars → 0.95 at 252).
- [ ] Per-predictor min-bars gates documented.
- [ ] Calibration coverage 3-state surface documented.
- [ ] Limitations surfaced (bound to single predictor; sample-size not time-since-deploy).
- [ ] No source modification.

## Out of scope

- T-015 forecast-generation deep dive (merged).
- T-016 calibration deep dive (merged).
- ADR-0003 predictor gap (T-046 — merged; cross-ref only).
- T-016b prediction-track-record screen (next functional-review addition).
- T-021b performance review (last).

## Verification

- File exists.
- Maturation logic confirmed-to-exist (not gap).
- Confidence curve cited.
- Limitations surfaced.

## Notes

T-012b is the 3rd of 5 functional-review additions. Unlike T-011b (where the queried functionality was absent), T-012b finds the queried functionality **present** — the system has a genuine sample-size-driven confidence-buildup mechanism. The doc's value is documenting the mechanism + its limitations (bound to one predictor; bar-count proxy not deployment-age). This is the rare functional-review addition where the answer is "yes, it exists, here's how".
