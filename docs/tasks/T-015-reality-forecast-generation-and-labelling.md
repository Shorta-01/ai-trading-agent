```yaml
id: T-015
title: Write reality doc for forecast generation + labelling flow
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/460
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/forecast-generation-and-labelling.md` does not exist (verified). T-015 is a focused synthesis — every code site is cited in T-007 `worker-forecasting-and-decision-package.md` (§§2-6) and T-002 portfolio predictor docs. No new files read.
  - T-007 `worker-forecasting-and-decision-package.md` §1 (ADR 0003 intent + 1-of-7-predictors gap), §2 (asset universe resolver), §4 (`forecasting_step.run_forecasting_step` + 5 block reasons), §5 (`historical_bootstrap` math), §6 (label translator + 6-state vocabulary + threshold table).
  - T-002 `portfolio-predictors.md` (predictor protocol + module inventory).
  - T-002 `portfolio-money-and-accounting.md` (Decimal-as-string discipline).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the forecast-generation + labelling workflow doc focused on the per-asset transformation `closes → BootstrapForecastResult → label`.
  - `forecast-generation-and-labelling.md` — single-predictor reality + block-bootstrap math + 5 block reasons + 6-label decision tree + 3-state confidence + Decimal-as-string boundary.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing the per-asset forecast transformation from inputs to persisted `ForecastEntry` row + label.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; ADR 0003 intent + 1-of-7-predictors gap surfaced; block-bootstrap math constants enumerated (window/horizon/resamples/block_size); 5 block reasons documented; 6-label decision tree documented with threshold-table refs; confidence + freshness state machines documented; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — Decision Package composition (T-017), calibration evaluation (T-016), predictor backtesting + leaderboard (T-024), AI explanation (T-023). All four are sibling tasks; T-015 focuses purely on forecast generation + labelling.

## Goal

Produce one workflow reality doc tracing the per-asset forecast generation flow — close-history loading → block-bootstrap (single-predictor `historical_bootstrap_v1`) → freshness + confidence + label decision → persisted `ForecastEntry` row. Documents the **single-predictor reality** against ADR-0003's seven-predictor intent.

## Context

`depends_on:` T-002, T-007. T-007 §1 surfaced the largest intent-vs-reality gap in the worker — ADR 0003 locks 7 predictors with weighted-average ensemble, code ships 1 (`historical_bootstrap_v1`). T-015 is the focused workflow doc that traces what actually runs when the orchestrator's forecasting gate fires at 07:00 morning_briefing.

## Touch scope

Create:
- `docs/reality/workflows/forecast-generation-and-labelling.md`

Read: T-002 + T-007 reality docs (already on disk).

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] ADR 0003 intent quoted verbatim (7 predictors + ensemble) + 1-of-7-predictors gap surfaced.
- [ ] Block-bootstrap math constants enumerated (`DEFAULT_HISTORY_WINDOW_DAYS=252`, `DEFAULT_HORIZON_DAYS=20`, `DEFAULT_NUM_RESAMPLES=10_000`, `DEFAULT_BLOCK_SIZE=5`, `MIN_CLOSES_FOR_FORECAST=200`).
- [ ] 5 block reasons enumerated with their gate conditions.
- [ ] 6-label Dutch vocabulary + decision tree + threshold table cited.
- [ ] 3-state confidence (`Hoog / Gemiddeld / Laag`) + `gaps_in_last_60_days=0` hardcode noted.
- [ ] No source modification.

## Out of scope

- Decision Package composition (T-017).
- Calibration evaluation (T-016 — the 06:00 pre_briefing step).
- Predictor backtesting + leaderboard (T-024).
- AI explanation (T-023).
- Action draft composition (T-018).

## Verification

- File exists.
- `historical_bootstrap_v1` cited as the sole predictor with file:line.
- 6 labels (`Kopen / Verminderen / Verkopen / Houden / Bekijken / Geblokkeerd`) all present.
- 5 block reasons present.

## Notes

The 6-label vocabulary (`label_translator.py:26-28`) is the **canonical Dutch label set** for forecasts in the system. Frontend pills, Decision Package headers, and action-draft routing all key off this enum. The 6 labels were locked by product brainstorm 2026-05-25 §Q4.
