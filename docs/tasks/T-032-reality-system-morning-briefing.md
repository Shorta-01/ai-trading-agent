```yaml
id: T-032
title: Write reality doc for system-morning-briefing-07-00 workflow
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/477
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/system-morning-briefing-07-00.md` does not exist (verified). Every code site is already cited in T-011 + T-015 + T-017 + T-023 reality docs:
  - T-011 `morning-chain-orchestration.md` — full end-to-end functionality doc covering all 3 morning fires.
  - T-015 `forecast-generation-and-labelling.md` — forecasting sub-step (fires only at morning_briefing).
  - T-017 `decision-package-composition.md` — DP composition sub-step (fires only at morning_briefing).
  - T-023 `ai-explanation-and-budget.md` — LLM explanation downstream of orchestrator (fires only at morning_briefing per T-011 §9).
  - T-031 `system-morning-pre-briefing-06-00.md` (just merged) — sibling tick at 06:00; cross-references for what runs at 06:00 vs 07:00.
  - `apps/worker/src/portfolio_outlook_worker/scheduler.py:151-158` (hourly_delta cron registration) + `:204` (`_on_hourly` handler).
  - `apps/worker/src/portfolio_outlook_worker/orchestrator.py:167-180` (`_relabel_morning_briefing` — 07:00 hourly_delta gets relabelled to morning_briefing).
  - `apps/worker/src/portfolio_outlook_worker/orchestrator.py:332-348` (forecasting gate), `:348+` (DP composition gate).
  - `apps/api/src/portfolio_outlook_api/morning_chain.py:1-365` (THE PARALLEL API morning chain — 6 named legs with its own scheduler).
  - `apps/api/src/portfolio_outlook_api/scheduler.py:107, :236-257` (API scheduler driving `run_daily_briefing_job`).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **system-tick workflow** narrative for the 07:00 Brussels morning_briefing fire.
  - `system-morning-briefing-07-00.md` — system-perspective trace: APScheduler `cron hour="7-21", minute=0 Europe/Brussels` → `_on_hourly` handler → `run_orchestrator(run_type="hourly_delta")` → `_relabel_morning_briefing` flips to `"morning_briefing"` if brussels_now_hour == 7 → connectivity + mode → on `mode_detected="normal"`, **all 5 sub-steps fire** (market-data refresh + forecasting + DP composition + calibration SKIPS (06:00 only) + daily briefing + AI explanation downstream) → audit row with 4 populated slots. Distinct from T-011 (full functionality), T-031 (06:00 sibling), T-033 (08:00-21:00 hourly delta — future).
  - Also documents the **doctrine drift**: a SECOND parallel morning chain lives in `apps/api/src/portfolio_outlook_api/morning_chain.py` with its own 6 legs + its own APScheduler (`scheduler.py:107, :236-257`) driven by `SCHEDULER_DAILY_BRIEFING_CRON` — the same config string T-031 §1 documented as IGNORED by the worker scheduler. Two morning chains run in parallel; their interaction is undocumented.
- **Step 3 (one-line change):** write one system-tick workflow reality doc tracing the 07:00 morning_briefing fire end-to-end + surface the worker-vs-API dual-scheduler drift.
- **Step 4 (measurable):** yes — eight acceptance criteria: file exists; APScheduler trigger documented (cron + `_relabel_morning_briefing` clever); 5 sub-steps that RUN documented (market-data + forecasting + DP composition + (skip calibration) + daily briefing + AI explanation downstream); the worker-vs-API dual-scheduler drift documented as dominant finding; LLM cost surfaces at 07:00 (T-023 cross-ref); audit row composition documented (4 populated slots); 6 `mode_detected` outcomes documented; ≥ 10 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — calibration sub-step (T-016 — merged sibling; runs at 06:00 not 07:00), DP composer mechanics (T-017 — merged sibling), forecasting deep dive (T-015 — merged sibling), AI explanation deep dive (T-023 — merged sibling).

## Goal

Produce one system-tick workflow reality doc tracing the 07:00 morning_briefing fire from APScheduler trigger to audit-row write. Focus on (a) what fires at 07:00 specifically (market-data + forecasting + DP composition + daily briefing + AI explanation downstream — 5 sub-steps), (b) the `_relabel_morning_briefing` mechanism that makes 07:00 special (the cron is `hour="7-21"` but only 07:00 gets the morning_briefing label), (c) the worker-vs-API dual-scheduler doctrine drift, (d) the LLM cost surfaces at 07:00 (T-023 — the only fire that triggers Anthropic Claude calls), (e) the 6 `mode_detected` outcomes.

## Context

`depends_on:` T-011, T-015, T-017. T-011 covered all 3 morning fires at functionality level; T-015 covered forecasting; T-017 covered DP composition. T-031 documented the 06:00 sibling tick. T-032 narrows to the 07:00 tick + surfaces the dual-scheduler drift.

## Touch scope

Create:
- `docs/reality/workflows/system-morning-briefing-07-00.md`

Read: T-011 + T-015 + T-017 + T-023 + T-031 reality docs + `scheduler.py` (worker cron) + `orchestrator.py` (relabel + gates) + `morning_chain.py` + `scheduler.py` (API).

## Acceptance criteria

- [ ] Output file exists.
- [ ] APScheduler trigger documented (`scheduler.py:151-158` cron `hour="7-21", minute=0`) + `_relabel_morning_briefing` clever (orchestrator.py:167-180; only 07:00 gets the morning_briefing relabel).
- [ ] 5 sub-steps that RUN documented (market-data refresh + forecasting + DP composition + daily briefing + AI explanation downstream) with their gates.
- [ ] Calibration SKIPS at 07:00 (only fires at pre_briefing 06:00) documented.
- [ ] **Worker-vs-API dual-scheduler doctrine drift documented as dominant finding** — `apps/api/src/portfolio_outlook_api/morning_chain.py` is a parallel 6-leg orchestrator with its own APScheduler.
- [ ] LLM cost surface at 07:00 (T-023 cross-ref) — the only fire that costs Anthropic Claude tokens.
- [ ] Audit row composition documented (`market_data` + `forecast` + `decision_package` slots populated; `calibration` slot empty).
- [ ] 6 `mode_detected` outcomes × morning_briefing matrix documented.
- [ ] ≥ 10 Phase 1c findings.
- [ ] No source modification.

## Out of scope

- Calibration sub-step (T-016 — merged sibling; runs at 06:00 not 07:00).
- DP composer mechanics (T-017 — merged sibling).
- Forecasting deep dive (T-015 — merged sibling).
- AI explanation deep dive (T-023 — merged sibling).
- 06:00 pre_briefing fire (T-031 — merged sibling).
- 08:00-21:00 hourly_delta fires (T-033 — future task).

## Verification

- File exists.
- `_relabel_morning_briefing` mechanism cited with file:line.
- Dual-scheduler drift documented with both module paths.
- LLM cost surface cited per T-023.
- ≥ 10 Phase 1c findings.

## Notes

T-032 is the 2nd of 5 system-tick workflows. The dominant finding is the **dual-scheduler doctrine drift**: the worker scheduler (`apps/worker/src/.../scheduler.py`) fires the morning chain at fixed `hour="7-21"`; the API scheduler (`apps/api/src/.../scheduler.py`) fires its own parallel chain at whatever `SCHEDULER_DAILY_BRIEFING_CRON` says (default `"30 6 * * *"` = 06:30). The same config string is **read by both** schedulers but **only honored by the API scheduler**. Two independent morning chains run; their coordination is undocumented; their interaction at shared storage tables (forecast_predictions, decision_packages, action_drafts) is unverified.
