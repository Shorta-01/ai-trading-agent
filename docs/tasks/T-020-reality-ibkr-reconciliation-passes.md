```yaml
id: T-020
title: Write reality doc for IBKR reconciliation passes A/B/C
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/reconciliation.md
decision_ref: docs/decisions/0010-reconciliation-architecture.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/465
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` does not exist (verified). Pure synthesis — every code site is cited in T-004 + T-007 reality docs:
  - T-007 `worker-actions-and-reconciliation.md` §§8-12 — `IbkrReconciler` orchestrator, Passes A / B / C, and the four audit tables.
  - T-007 §6 — `SubmissionSweep` (sibling tick using the same single-flight lock).
  - T-005 `api-actions-suggestions-and-watchlists.md` — the 7 reconciliation routes (6 GET + 1 POST ack).
  - T-004 `api-ibkr-submission-and-watchlists.md` — `placeOrder` boundary (informs Pass A's evidence model).
  - `docs/intent/reconciliation.md` (locked 2026-05-26) — the hybrid cadence + 4-tier B/C/D/E classification intent.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the end-to-end periodic reconciliation tick (3 passes + audit chain) workflow doc.
  - `ibkr-reconciliation-passes-a-b-c.md` — tick trigger → single-flight lock → connection gate → strict Pass A → Pass B → Pass C ordering → 4 append-only audit tables (`reconciliation_run_audit`, `reconciliation_audit`, `unmatched_execution_audit`, `manual_review_queue`) → API surface (6 GET routes + 1 acknowledge POST).
- **Step 3 (one-line change):** write one cited workflow reality doc tracing the reconciler tick end-to-end from APScheduler trigger → terminal audit-row write.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; tick orchestrator + lock + connection gate documented; strict Pass A / Pass B / Pass C ordering documented with the `ReconcilerMode` 4-mode enum; each pass's storage write fan-out documented (Pass A: `executions_repo` + `unmatched_repo` + `reconciliation_audit_repo`; Pass B: `action_draft_repo.apply_lifecycle_transition` + `reconciliation_audit_repo`; Pass C: `action_draft_repo` + `manual_review_repo` + `reconciliation_audit_repo`); 4 audit tables enumerated with their idempotency keys; API surface (6 GET + 1 POST) cited; intent-vs-reality gaps surfaced (4-tier B/C/D/E classification NOT present in code; no production APScheduler wiring; legacy `reconciliation_sync.py` doctrine drift); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — action-draft composition + approval (T-018), submission sweep (T-019), AI explanation (T-023), portfolio valuation (T-021).

## Goal

Produce one workflow reality doc tracing the periodic IBKR reconciliation tick end-to-end — APScheduler trigger (intended) → single-flight lock → IBKR connection gate → strict Pass A (orphaned executions) → Pass B (stale in-flight) → Pass C (24h timeout escalation) → 4 append-only audit tables → API read surface (6 GET routes + 1 acknowledge POST). The doc bridges the intent's 4-tier B/C/D/E classification vs the code's flat divergence-type strings, and re-confirms the production-wiring gap (neither `SubmissionSweep.tick()` nor `IbkrReconciler.tick()` is instantiated in `scheduler.py`).

## Context

`depends_on:` T-004, T-007. T-007 §§8-12 documented the reconciliation modules at module level; T-020 stitches them into the end-to-end "from APScheduler tick to a row in `reconciliation_run_audit`" story. The 3-pass system is the **only** path that detects + heals divergences between local state and IBKR truth — but it currently has no production wiring into APScheduler, which is the single most material finding this doc surfaces.

## Touch scope

Create:
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md`

Read: T-004 + T-005 + T-007 reality docs (already on disk) + reconciliation intent + the 4 reconciliation modules + the API surface.

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Tick orchestrator documented (`IbkrReconciler.tick()` at `reconciler.py:181` + `ReconcilerMode` 4-mode Literal at `:62`).
- [ ] Single-flight lock + connection gate documented (shared with submission sweep; `is_connected()` short-circuit at `:225`).
- [ ] Strict Pass A → Pass B → Pass C order documented (invocations at `:249`, `:260`, `:269`).
- [ ] Each pass's per-row storage write fan-out documented (Pass A heal + unmatched; Pass B status correction; Pass C manual-review escalation at 24h cut-off).
- [ ] 4 audit tables enumerated: `reconciliation_run_audit` (UNIQUE on `reconciliation_run_id`), `reconciliation_audit`, `unmatched_execution_audit` (UNIQUE on `ibkr_exec_id`), `manual_review_queue`.
- [ ] API surface (6 GET routes + 1 acknowledge POST) cited from `reconciliation.py:295-502`.
- [ ] Intent-vs-reality gaps surfaced: (1) 4-tier B/C/D/E classification not present in code; (2) no APScheduler wiring for `IbkrReconciler.tick()` in `scheduler.py`; (3) legacy `reconciliation_sync.py` co-exists with the new Task 135b reconciler; (4) no user-initiated reconciliation trigger route; (5) no 07:00 morning-chain mandatory block.
- [ ] No source modification.

## Out of scope

- Action-draft composition + approval (T-018 — produces the drafts that Passes B + C operate on).
- IBKR submission lifecycle (T-019 — sibling sweep that creates the in-flight drafts Pass B watches).
- AI explanation (T-023).
- Portfolio valuation drift (T-021 — corporate-action drift is intent-classified as D-class but tier classification is absent in code).
- The legacy `reconciliation_sync.py` orchestrator itself (only referenced as doctrine drift — not its own deep dive; that belongs to a future cleanup task).

## Verification

- File exists.
- `IbkrReconciler.tick()` + lock + connection gate cited with file:line anchors.
- Pass A / Pass B / Pass C entry points cited (`pass_a_orphaned_executions.py:125`, `pass_b_stale_in_flight.py:129`, `pass_c_timeout_recovery.py:73`).
- All 4 audit tables cited with their migration anchor (`0053_reconciliation_audit_and_manual_review.py`) + their UNIQUE constraints.
- All 7 API routes cited with file:line anchors.
- Production-wiring gap surfaced (grep proof: `IbkrReconciler` not instantiated outside its own module + tests).

## Notes

T-020 is the sibling of T-019. Together they document the full backstop architecture: the submission sweep creates in-flight state; the reconciler detects divergence and heals it. **Both ticks are intended for APScheduler but neither is currently wired in** — the single most safety-critical finding in the reality audit so far. Phase 1c is likely to recommend both wiring + tier classification implementation. T-020 re-surfaces these without proposing fixes.
