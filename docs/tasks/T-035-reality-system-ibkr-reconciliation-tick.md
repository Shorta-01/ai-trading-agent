```yaml
id: T-035
title: Write reality doc for system-ibkr-reconciliation-tick workflow
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/reconciliation.md
decision_ref: docs/decisions/0010-reconciliation-architecture.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/system-ibkr-reconciliation-tick.md` does not exist (verified). Every code site is already cited in T-020 + T-034 reality docs:
  - T-020 `ibkr-reconciliation-passes-a-b-c.md` — full functionality coverage of the 3 passes + 4 audit tables + intent cadence vs reality.
  - T-034 `system-ibkr-submission-sweep.md` (merged) — parallel system-tick doc surfacing the same APScheduler wiring gap from the submission angle.
  - `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py:62, :139, :181-202` (`ReconcilerMode` Literal, class, `tick()` entry).
  - `apps/worker/src/portfolio_outlook_worker/scheduler.py:130-175` (worker scheduler — does NOT register `IbkrReconciler.tick`).
  - `docs/intent/reconciliation.md` §1 (intent cadence: 15min market hours + 1h off-hours + 5 event triggers).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **system-tick workflow** narrative for the reconciliation tick.
  - `system-ibkr-reconciliation-tick.md` — system-perspective trace of `IbkrReconciler.tick()`: intended APScheduler invocation → single-flight lock → connectivity gate → strict Pass A → B → C ordering (per T-020 §3-§5) → `reconciliation_run_audit` row written via `complete_run`. **The tick is NOT wired in production**, mirroring T-034's submission-sweep finding. All 5 intent-§1 event triggers (15min cadence, 1h cadence, 07:00 morning-chain block, after-fill, after-reconnect, on-demand) are missing. The only path that ever runs the 3 passes is unit tests.
- **Step 3 (one-line change):** write one system-tick workflow reality doc tracing the reconciler tick + close out Track 1a Reality Workflows by re-surfacing the wiring gap parallel to T-034.
- **Step 4 (overall measurable):** yes — eight acceptance criteria: file exists; intended trigger documented (`tick()` + 4-mode `ReconcilerMode` Literal); strict Pass A → B → C ordering documented per T-020 §3; intent cadence (15min/1h/5 triggers) vs reality (none wired) documented; the wiring gap re-surfaced as dominant finding with grep proof; cross-reference to T-034 (parallel sibling pattern); user-visible consequences documented (divergences accumulate undetected); ≥ 7 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — pass internals (T-020 — merged sibling), submission sweep tick (T-034 — merged sibling).

## Goal

Produce one tight system-tick workflow reality doc tracing the reconciliation tick — the intended APScheduler trigger, the 4-mode outcome literal, the strict pass ordering, and **the dominant finding: the tick is not wired in production**. Close out Track 1a Reality Workflows (T-025…T-035) by mirroring T-034's structure for the reconciliation peer.

## Context

`depends_on:` T-020. T-020 covered the 3 passes end-to-end at functionality level; T-034 documented the parallel submission-sweep wiring gap. T-035 narrows to the reconciliation tick from the system perspective + closes Track 1a.

## Touch scope

Create:
- `docs/reality/workflows/system-ibkr-reconciliation-tick.md`

Read: T-020 + T-034 reality docs + `reconciler.py` + `scheduler.py` (worker — confirms no wiring).

## Acceptance criteria

- [ ] Output file exists.
- [ ] Intended trigger documented (`IbkrReconciler.tick()` at `reconciler.py:181`; docstring claim "APScheduler" at `:142`).
- [ ] 4-mode `ReconcilerMode` Literal documented (`completed | skipped_locked | skipped_disconnected | error`).
- [ ] Strict Pass A → B → C ordering documented (per T-020 §3-§5).
- [ ] Intent cadence (15min market hours / 1h off-hours / 5 event triggers from `docs/intent/reconciliation.md` §1) documented vs reality (none wired).
- [ ] **Wiring gap re-surfaced as dominant finding** — grep proof + cross-reference to T-034 parallel pattern.
- [ ] User-visible consequences documented (divergences accumulate undetected; if user-cancel runs at 14:00 and Pass A would have detected the IBKR-side fill, but Pass A never runs, the dashboard shows the wrong state until manual intervention).
- [ ] ≥ 7 Phase 1c findings.
- [ ] No source modification.

## Out of scope

- Pass internals (T-020 — merged sibling; T-035 only re-surfaces from system-tick angle).
- Submission sweep tick (T-034 — merged sibling; parallel pattern referenced).
- API reconciliation routes (T-020 §7 — already documented).
- 4-tier B/C/D/E classification (T-020 §10.3 — already flagged absent).

## Verification

- File exists.
- `IbkrReconciler` only-in-tests grep proof cited.
- 4-mode literal cited.
- 5 intent event triggers documented as missing.
- Cross-reference to T-034 documented.
- ≥ 7 Phase 1c findings.

## Notes

T-035 is the 5th and final system-tick workflow + closes Track 1a Reality Workflows (T-025…T-035) entirely. The dominant finding mirrors T-034: the reconciliation tick is intended for APScheduler but isn't wired. Combined with T-034, **both back-stop infrastructure ticks (submission sweep + reconciliation) are missing their scheduling layer**. This is the most safety-critical pattern in the workflow audit: the system has the code to submit orders + the code to detect divergences after submission, but neither ever runs in production. With Track 1a closed, Phase 1c can begin synthesizing the architectural review (Track 1b T-036…T-043) and gap analysis (Track 1c T-044…T-049).
