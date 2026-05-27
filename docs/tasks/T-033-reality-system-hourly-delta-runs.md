```yaml
id: T-033
title: Write reality doc for system-hourly-delta-runs workflow
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/478
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/system-hourly-delta-runs.md` does not exist (verified). Every code site is already cited in T-011 + T-031 + T-032 reality docs:
  - T-011 `morning-chain-orchestration.md` — full end-to-end functionality doc; §11 outcome matrix shows hourly_delta does nothing substantive.
  - T-031 `system-morning-pre-briefing-06-00.md` (merged) — 06:00 sibling tick.
  - T-032 `system-morning-briefing-07-00.md` (merged) — 07:00 sibling tick; documented `_relabel_morning_briefing` mechanism.
  - `apps/worker/src/portfolio_outlook_worker/scheduler.py:151-158` (the single `_on_hourly` cron fires both morning_briefing at 07:00 + hourly_delta at 08:00-21:00).
  - `apps/worker/src/portfolio_outlook_worker/orchestrator.py:50` (`RunType` Literal includes `hourly_delta`), `:178` (relabel skip for hour != 7), `:312-383` (all 4 sub-step gates explicitly exclude `hourly_delta`).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **system-tick workflow** narrative for the 14 hourly_delta fires (08:00-21:00) per day.
  - `system-hourly-delta-runs.md` — system-perspective trace: APScheduler `cron hour="7-21", minute=0` fires `_on_hourly → run_orchestrator(run_type="hourly_delta")` 15× daily, but only the 07:00 fire gets relabelled to `morning_briefing`; the other 14 fires (08:00 through 21:00) **stay as `hourly_delta` and do zero substantive work** because all 4 sub-step gates explicitly exclude `hourly_delta` (market-data: pre_briefing/morning_briefing only; forecasting + DP: morning_briefing only; calibration: pre_briefing only). What hourly_delta DOES do: lock acquire + connectivity probe + mode detection + (cold-start seed if mode=cold_start) + audit row with empty payload. The name "hourly delta" suggests intra-day data refresh that does NOT exist. **Dominant finding**.
- **Step 3 (one-line change):** write one system-tick workflow reality doc tracing the hourly_delta fires + surface the "name promises a delta refresh that doesn't happen" finding.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 14-fires-per-day cadence documented (08:00-21:00); ALL 4 sub-step gates that EXCLUDE hourly_delta cited; the actual work done (lock + connectivity + mode + cold-start handling + empty-payload audit row) documented; intent-vs-reality gap surfaced (name suggests intra-day delta refresh; reality is empty-payload heartbeat); audit row composition documented (empty `audit_payload = {}`); ≥ 7 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — 06:00 pre_briefing (T-031 — merged sibling), 07:00 morning_briefing (T-032 — merged sibling), submission sweep (T-019 — merged sibling), reconciliation tick (T-035 future).

## Goal

Produce one system-tick workflow reality doc tracing the 14 hourly_delta fires per day from APScheduler trigger to audit-row write. Focus on (a) what fires (cron `hour="7-21"`), (b) what happens at 08:00-21:00 (lock + connectivity + mode + cold-start handling + empty-payload audit), (c) the dominant finding: **the name "hourly delta" suggests intra-day data refresh that doesn't actually happen**, (d) the cost of the 14 empty fires (audit rows + lock contention with submission sweep + reconciler).

## Context

`depends_on:` T-011. T-011 covered all 3 morning fires at functionality level + the outcome matrix showing hourly_delta does nothing. T-031 + T-032 documented the 06:00 + 07:00 ticks. T-033 narrows to the 08:00-21:00 hourly_delta fires + surfaces the name-vs-behavior gap.

## Touch scope

Create:
- `docs/reality/workflows/system-hourly-delta-runs.md`

Read: T-011 + T-031 + T-032 reality docs + `scheduler.py` + `orchestrator.py` (gates).

## Acceptance criteria

- [ ] Output file exists.
- [ ] 14-fires-per-day cadence documented (08:00 through 21:00; 07:00 is the morning_briefing per T-032's relabel).
- [ ] All 4 sub-step gates that EXCLUDE hourly_delta cited with file:line.
- [ ] Actual work done documented (lock + connectivity + mode detection + cold-start handling + empty-payload audit row).
- [ ] Intent-vs-reality gap surfaced as dominant finding ("hourly delta" name promises intra-day refresh that does NOT happen).
- [ ] Empty `audit_payload = {}` composition documented.
- [ ] ≥ 7 Phase 1c findings.
- [ ] No source modification.

## Out of scope

- 06:00 pre_briefing fire (T-031 — merged sibling).
- 07:00 morning_briefing fire (T-032 — merged sibling).
- Submission sweep tick (T-019 — merged sibling; T-034 future).
- Reconciliation tick (T-020 — merged sibling; T-035 future).
- Daily briefing API morning_chain (T-032 §5).

## Verification

- File exists.
- 4 gate exclusions cited.
- Empty audit payload documented.
- Name-vs-behavior gap surfaced.
- ≥ 7 Phase 1c findings.

## Notes

T-033 is the 3rd of 5 system-tick workflows. The dominant finding is **architectural mismatch between name and behavior**: "hourly delta" suggests a per-hour data refresh + delta computation; reality is 14 essentially-empty fires per day. The fires DO produce audit rows (so observability is preserved) and DO run cold-start detection (so day-1 onboarding works if user happens to register at 14:00). But the substantive work the name implies — intra-day market-data refresh, delta forecasting against newer prices, fresh action drafts mid-day — none of that happens. This is the largest "expectation-vs-reality" gap in the system-tick suite.
