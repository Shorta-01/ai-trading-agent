```yaml
id: T-011
title: Write reality doc for morning-chain orchestration end-to-end
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/morning-chain-orchestration.md` does not exist (verified). T-011 is a synthesis task — no new code reads required. Cross-referenced reality docs already cite every code site needed:
  - T-007 `worker-orchestration-and-scheduling.md` (scheduler + `run_orchestrator` + mode_detected enum + 3 jobs + lifespan + single-flight lock + `_safe_append` audit pattern).
  - T-007 `worker-forecasting-and-decision-package.md` (asset universe resolver + calibration step + forecasting step + historical bootstrap + label translator + market-data step + EODHD + decision-package composer + Dutch explanation template + orchestration).
  - T-007 `worker-actions-and-reconciliation.md` cross-reference for "the orchestrator stops after DP composition; action-drafts/submission/reconciliation are separately wired".
  - T-006 `api-infrastructure-and-ai.md` §11 (Anthropic Claude provider + budget cap — only the explanation surface is actually called from the worker chain).
  - T-005 `api-forecasting-and-market-data.md` (the API-side mirror of the morning-chain endpoints).
- **Step 2 (one-line per touched file):** the one target file does not exist; it will hold the end-to-end morning-chain workflow doc.
  - `morning-chain-orchestration.md` — full chain spec: triggers (06:00 pre_briefing + 07:00 morning_briefing relabelled hourly), lock acquisition, mode detection (6 modes), per-step invocation order + gating conditions, audit-row writes (`scheduled_run_audit` + per-step diaries), failure paths (mode_detected + outcome literal pair), explicit out-of-scope (action drafts / submission / reconciliation run on separate scheduler ticks).
- **Step 3 (one-line change):** write one cited workflow reality doc that traces the 06:00 + 07:00 Brussels morning chain end-to-end from APScheduler trigger to decision-package persistence, citing every code site already documented in T-005/T-006/T-007.
- **Step 4 (measurable):** yes — five acceptance criteria: file exists at the locked filename; trigger model documented (cron + tz + APScheduler job IDs); all 5 morning-chain steps invocation order documented in the orchestrator's gating logic; audit trail enumerated (where rows are written); explicit out-of-scope section (action drafts / submission / reconciliation); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — no per-module reality content duplicated (cross-references suffice); no proposals for what the morning chain *should* do (gap analysis lives in Track 1c); no action-draft / submission / reconciliation walks (T-018, T-019, T-020 will produce those).

## Goal

Produce one workflow reality doc covering the morning-chain orchestration end-to-end — APScheduler trigger at 06:00 pre_briefing + 07:00 morning_briefing → single-flight lock → mode detection → market-data + forecasting + decision-package + AI explanation + calibration step invocations → audit-row writes → run completion.

## Context

`depends_on:` T-007. T-007's three reality docs (`worker-orchestration-and-scheduling.md`, `worker-forecasting-and-decision-package.md`, `worker-actions-and-reconciliation.md`) document the per-module reality; T-011 documents how those modules chain together at runtime. The output is the canonical reference for understanding "what runs at 06:00 and 07:00 Brussels each day", which is the most-asked operational question. Cross-referenced reality docs make this synthesis possible without re-reading source.

## Touch scope

Create:
- `docs/reality/workflows/morning-chain-orchestration.md`

Read: T-005 + T-006 + T-007 reality docs (already on disk after merge of T-005/T-006/T-007 PRs).

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Trigger model documented: 06:00 pre_briefing + 07:00 morning_briefing (relabelled hourly_delta), with the locked APScheduler cron expressions + Brussels timezone.
- [ ] Each step's invocation order documented in the orchestrator's gating logic, with file:line refs to the orchestrator's gate.
- [ ] Audit-row writes enumerated (`scheduled_run_audit` + per-step diaries) with the storage repository names.
- [ ] Explicit out-of-scope section recording that action drafts / submission / reconciliation are NOT part of the morning chain.
- [ ] No source modification.

## Out of scope

- Per-module reality content (T-007 docs already cover that).
- Action drafts / IBKR submission / reconciliation flows (T-018, T-019, T-020).
- Gap analysis between intent (ADR 0003 7-predictor ensemble) and reality (1-predictor historical bootstrap) — that's Phase 1c T-046.

## Verification

- File exists.
- The 6 `mode_detected` values from T-007 `worker-orchestration-and-scheduling.md` §6 all appear in the workflow doc.
- The 5 morning-chain step invocation gates from T-007 `worker-orchestration-and-scheduling.md` §6 control-flow section all appear, with their gating conditions cited.

## Notes

T-007 §6.5 explicitly documents the orchestrator "stops after Decision Package composition" — that surface is the natural boundary of the morning-chain doc. The submission sweep (T-007 `worker-actions-and-reconciliation.md` §6) and the reconciler (`worker-actions-and-reconciliation.md` §8) register their own APScheduler jobs and run on different cadences (FIFO sweep / per-tick reconciliation tick).
