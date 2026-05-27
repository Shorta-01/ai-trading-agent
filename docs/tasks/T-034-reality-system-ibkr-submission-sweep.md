```yaml
id: T-034
title: Write reality doc for system-ibkr-submission-sweep workflow
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/system-ibkr-submission-sweep.md` does not exist (verified). Every code site is already cited in T-019 + T-020 + T-031 reality docs:
  - T-019 `ibkr-order-submission-lifecycle.md` — full functionality coverage of the submission sweep (12 Tier-1 gates, Tier-2 account-ID re-read, single `place_order` call, IBKR callback families, 3 audit tables).
  - T-020 §2.3 + §10.1 — single-flight lock shared with reconciler + the wiring gap (NOT wired to APScheduler).
  - T-031 §2.3 — lock shared with morning chain at 06:00.
  - T-032 §6 — lock contention model.
  - `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:178-339` (the `SubmissionSweep` class + `tick()` method).
  - `apps/worker/src/portfolio_outlook_worker/scheduler.py:130-175` (the worker scheduler — does NOT register `SubmissionSweep.tick`).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **system-tick workflow** narrative for the submission sweep.
  - `system-ibkr-submission-sweep.md` — system-perspective trace: APScheduler would (intended) → `SubmissionSweep.tick()` → single-flight lock → market-hours gate → list `user_approved` drafts FIFO by `user_approved_at` → 12-gate safety re-check per draft → tier-2 account-ID re-read → `place_order(contract, order)` → first eligible draft submitted, sweep returns (one-per-tick break) → audit row written. **But the tick is NOT actually wired in production** (T-020 §10.1 originating finding). The class is unit-tested + has a public `tick()` method described as "Wired into APScheduler" in the docstring, but the worker scheduler at `scheduler.py:130-175` registers only 3 jobs (pre_briefing + hourly + heartbeat) — none of which invoke `SubmissionSweep.tick`. This means user-approved drafts pile up indefinitely; the only path that ever sends them to IBKR is one that doesn't exist yet.
- **Step 3 (one-line change):** write one system-tick workflow reality doc tracing the submission sweep + re-surface the wiring gap from the system-tick angle.
- **Step 4 (overall measurable):** yes — eight acceptance criteria: file exists; intended trigger + `tick()` entry documented; 5-stage tick body documented (lock + market-hours + queue poll + 12-gate eval + submit-or-break); locked one-per-tick discipline documented (`break` at `:337` per T-019 §4.1); the production-wiring gap re-surfaced as dominant finding (no APScheduler job invokes `tick()`); user-visible consequences documented (user-approved drafts pile up); audit row composition documented; ≥ 7 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — submission internals (T-019 — merged sibling; T-034 only re-surfaces from system-tick angle), reconciliation tick (T-035 future), action draft approval (T-026 — merged user-action sibling).

## Goal

Produce one system-tick workflow reality doc tracing the submission sweep as a SYSTEM tick — the **intended** APScheduler invocation, the 5-stage tick body, the locked one-per-tick discipline, and the **dominant finding: the tick is not actually wired**. Surface the user-visible consequence: drafts the user approves never get submitted unless the sweep is manually invoked or wired in.

## Context

`depends_on:` T-019. T-019 covered the submission flow at functionality level; T-020 §10.1 originated the "no APScheduler wiring" finding; T-031 + T-032 documented the lock-sharing model. T-034 narrows to the system-tick angle + makes the wiring gap operationally vivid.

## Touch scope

Create:
- `docs/reality/workflows/system-ibkr-submission-sweep.md`

Read: T-019 reality doc + `submission_sweep.py` + `scheduler.py` (worker — confirms no wiring).

## Acceptance criteria

- [ ] Output file exists.
- [ ] Intended trigger documented (`SubmissionSweep.tick()` at `submission_sweep.py:217`; docstring claims "Wired into APScheduler" at `:179-184`).
- [ ] 5-stage tick body documented (lock + market-hours gate + queue poll + 12-gate evaluation + submit-or-break).
- [ ] Locked one-per-tick discipline documented (`break` at `:337` after the first successful submit).
- [ ] **Production-wiring gap re-surfaced as dominant finding** — grep proof that nothing outside the module + tests instantiates `SubmissionSweep`; `scheduler.py:130-175` registers no job that invokes `tick()`.
- [ ] User-visible consequences documented (user-approved drafts pile up; T-026 user-action surface UI sees no badge update).
- [ ] Audit row composition documented (`SubmissionSweepResult` with mode literal: `completed | skipped_locked | skipped_market_closed | no_drafts | error`).
- [ ] ≥ 7 Phase 1c findings.
- [ ] No source modification.

## Out of scope

- Submission lifecycle internals (T-019 — merged sibling; the 12 Tier-1 gates, place_order call shape, audit tables).
- Reconciliation tick (T-035 — future sibling).
- Action draft approval (T-026 — merged user-action sibling).
- Worker-side cancel adapter (T-019 §4.8 — separate gap).

## Verification

- File exists.
- `SubmissionSweep` only-in-tests grep proof cited.
- 5-stage tick body documented.
- Wiring gap surfaced as dominant finding.
- ≥ 7 Phase 1c findings.

## Notes

T-034 is the 4th of 5 system-tick workflows. The dominant finding is operationally severe and re-surfaces the T-020 §10.1 originating finding from a new angle: **the submission sweep tick that intent and code both describe as "wired into APScheduler" is not actually wired**. The user approves a draft (T-026 JA ritual); the draft status flips to `user_approved`; and then nothing happens. The dashboard shows "Goedgekeurd" + the out-of-date banner ("IBKR-verzending wordt in een toekomstige update toegevoegd" — T-026 §10.5). The banner text turns out to be **accidentally truthful**: the IBKR submission infrastructure exists (T-019) but is not invoked. Phase 1c will need to either wire `SubmissionSweep.tick()` into the worker scheduler OR document that submission is intentionally deferred to a later phase.
