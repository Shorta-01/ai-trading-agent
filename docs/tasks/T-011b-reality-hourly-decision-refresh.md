```yaml
id: T-011b
title: Write reality doc for hourly-decision-refresh functionality
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/functionality/hourly-decision-refresh.md` does not exist (verified). The "hourly decision refresh" concept already exhaustively covered by T-033 `system-hourly-delta-runs.md` (286 lines documenting that all 4 sub-step gates exclude `run_type="hourly_delta"` — the intended "lighter hourly run that keeps the action list current" does not actually run). T-007 covers worker orchestrator + scheduler; T-031 + T-032 cover the morning fires the hourly was supposed to delta against.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the functionality-level reality doc for what the "hourly decision refresh" intent maps to in code.
  - `hourly-decision-refresh.md` — documents that the carry-forward concept maps to T-033's `hourly_delta` run type, which **does not refresh decisions** — name-vs-behavior mismatch already verdicted in T-033 §6. The intended functionality is absent; the cron fires 14× daily at 08:00-21:00 but all substantive sub-steps exclude `hourly_delta` from their gates. The actions area stays static from 07:00 onward. Cross-references T-033 + T-046 (no monthly rebacktest) + Track 1c gaps.
- **Step 3 (one-line change):** write one functionality-level reality doc documenting the intent-vs-reality of "hourly decision refresh".
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; intent (per queue.md spec) of "lighter hourly run that keeps the action list current between 07:00 evaluations" documented; reality per T-033 (empty fires) documented; intent-vs-reality gap surfaced explicitly; cross-references to T-033 + T-046 + Track 1c gap items; recommendations deferred (Track 1c covers via T-046 §11 monthly rebacktest + general T-033 §10 name-vs-behavior fix); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — T-011c (dashboard composition) next; T-012b / T-016b / T-021b remaining functional-review additions.

## Goal

Produce one functionality-level reality doc clarifying what the queued "hourly-decision-refresh" feature actually maps to in code. The answer is **nothing functional** — T-033 already documented the gap. T-011b's job is to (a) acknowledge the intent (lighter hourly refresh of decisions), (b) point at T-033 + T-046 for the reality, (c) note this is a known gap surfaced multiple times in the audit. This is a thin reality doc; it exists to close the loop on the functional-review-additions ledger.

## Context

`depends_on:` T-007 (worker orchestrator + scheduler). Already mostly documented in T-033 (`system-hourly-delta-runs.md`) merged 2026-05-27. T-011b is the carry-forward "functionality" file the 2026-05-26 functional review requested.

## Touch scope

Create:
- `docs/reality/functionality/hourly-decision-refresh.md`

Read: T-007 + T-033 + T-046 (quant rebacktest gap) reality docs.

## Acceptance criteria

- [ ] Output file exists at `docs/reality/functionality/hourly-decision-refresh.md`.
- [ ] Intent of "lighter hourly run that keeps the action list current between 07:00 evaluations" documented (per queue.md T-011b spec).
- [ ] Reality per T-033 (empty fires; all 4 sub-step gates exclude `hourly_delta`) documented.
- [ ] Intent-vs-reality gap surfaced explicitly.
- [ ] Cross-references to T-033 + T-046 + Track 1c gap items.
- [ ] No source modification.

## Out of scope

- T-033 deep-dive content (already merged sibling).
- T-046 quant items (already merged sibling).
- T-011c dashboard composition (next).
- T-012b / T-016b / T-021b remaining functional-review additions.

## Verification

- File exists.
- T-033 cross-reference cited.
- Intent vs reality gap explicit.

## Notes

T-011b is one of 5 carry-forward tasks from the 2026-05-26 functional review. These tasks address gaps the functional review identified after the initial Phase 1 docs were merged. T-011b is the smallest of the 5 — it largely re-surfaces T-033's findings under the canonical filename the functional review specified. The other 4 functional-review additions (T-011c, T-012b, T-016b, T-021b) are more substantive.
