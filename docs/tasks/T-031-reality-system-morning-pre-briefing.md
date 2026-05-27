```yaml
id: T-031
title: Write reality doc for system-morning-pre-briefing-06-00 workflow
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/476
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/system-morning-pre-briefing-06-00.md` does not exist (verified). Every code site is already cited in T-011 + T-016 reality docs:
  - T-011 `morning-chain-orchestration.md` — full end-to-end functionality doc covering all 3 morning fires.
  - T-016 `forecast-calibration-and-prediction-diary.md` — the calibration sub-step (the unique work of the 06:00 fire).
  - T-014 `market-data-pipeline.md` — the market-data sub-step (also runs at 06:00).
  - `apps/worker/src/portfolio_outlook_worker/scheduler.py:50, :141-149, :201-202` — `_PRE_BRIEFING_JOB_ID` + cron registration + `_on_pre_briefing` handler.
  - `apps/worker/src/portfolio_outlook_worker/orchestrator.py:50` (`RunType`), `:312-330` (market-data gate), `:372-383` (calibration gate).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **system-tick workflow** narrative for the 06:00 Brussels pre_briefing fire.
  - `system-morning-pre-briefing-06-00.md` — system-perspective trace: APScheduler fires `cron hour=6, minute=0 Europe/Brussels` → `_on_pre_briefing` → `run_orchestrator(run_type="pre_briefing")` → connectivity + mode detection → on `mode_detected="normal"`, run market-data refresh (EODHD EOD + FX) + calibration step (score yesterday's expired forecasts) → 2 of 5 morning-chain steps skipped (forecasting + DP composition + daily briefing all wait for 07:00 morning_briefing) → `worker_run_audit` row written. Distinct from T-011 (which covered all 3 morning fires end-to-end at functionality level).
- **Step 3 (one-line change):** write one system-tick workflow reality doc tracing the 06:00 pre_briefing fire end-to-end + clarify what runs vs what doesn't.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; APScheduler trigger documented (cron + timezone + job id); 2 sub-steps that run (market-data + calibration) documented with gates; 3 sub-steps that skip (forecasting + DP composition + daily briefing) documented with skip-gate rationale; audit row composition documented; 6 `mode_detected` outcomes documented per T-011 cross-reference; ≥ 7 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — full chain (T-011 — merged sibling), calibration deep dive (T-016 — merged sibling), market-data deep dive (T-014 — merged sibling).

## Goal

Produce one system-tick workflow reality doc tracing the 06:00 pre_briefing fire from APScheduler trigger to audit-row write. Focus on (a) what runs at 06:00 specifically (market-data + calibration), (b) what's deliberately skipped (forecasting / DP composition / daily briefing — all wait for 07:00), (c) why the system splits the work this way (refresh inputs first, score yesterday's predictions, then at 07:00 produce new forecasts), (d) the 6 `mode_detected` outcomes and which ones change behavior.

## Context

`depends_on:` T-011, T-016. T-011 covered all 3 morning fires (06:00 pre_briefing, 07:00 morning_briefing, 08:00-21:00 hourly_delta) end-to-end; T-016 covered the calibration sub-step + prediction diary; T-014 covered market-data pipeline. T-031 narrows to the 06:00 tick specifically — what it does, what it skips, why.

## Touch scope

Create:
- `docs/reality/workflows/system-morning-pre-briefing-06-00.md`

Read: T-011 + T-016 + T-014 reality docs + `scheduler.py` (cron wiring) + `orchestrator.py` (sub-step gates).

## Acceptance criteria

- [ ] Output file exists.
- [ ] APScheduler trigger documented (`scheduler.py:141-149` cron `hour=6, minute=0 Europe/Brussels`; job id `_PRE_BRIEFING_JOB_ID = "pre_briefing"`).
- [ ] 2 sub-steps that RUN documented (market-data refresh + calibration step) with their gates cited.
- [ ] 3 sub-steps that SKIP documented (forecasting / DP composition / daily briefing) with skip-gate rationale.
- [ ] Audit row composition documented (`worker_run_audit` payload structure with `market_data` + `calibration` slots).
- [ ] 6 `mode_detected` outcomes documented (cross-reference T-011 §4); which outcomes change pre_briefing behavior.
- [ ] ≥ 7 Phase 1c findings specific to the pre_briefing tick.
- [ ] No source modification.

## Out of scope

- Full morning chain (T-011 — merged sibling; covers all 3 fires).
- Calibration deep dive (T-016 — merged sibling).
- Market-data deep dive (T-014 — merged sibling).
- 07:00 morning_briefing fire (T-032 — next task).
- Hourly_delta fires (T-033 — future task).

## Verification

- File exists.
- APScheduler cron registration cited.
- Run-vs-skip step matrix documented.
- Audit row structure documented.
- ≥ 7 Phase 1c findings.

## Notes

T-031 opens the 5-doc system-tick sub-track of Track 1a Reality Workflows (T-031…T-035). The pre_briefing fire is the **lightest** of the three morning fires — it only refreshes inputs and scores yesterday. The heavy lifting (forecasting + DP composition + AI explanation) happens at 07:00. The architectural rationale is to have fresh inputs (market data) AND a fresh calibration score available at 07:00 when the forecasting step decides predictor weights. Splitting these into 06:00 + 07:00 fires gives the system a 1-hour buffer for either fire to slip without blocking the user-visible 07:00 briefing.
