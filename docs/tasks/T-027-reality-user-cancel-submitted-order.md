```yaml
id: T-027
title: Write reality doc for user-cancel-submitted-order workflow
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/user-cancel-submitted-order.md` does not exist (verified). Every code site is already cited in T-019 + T-008 reality docs:
  - T-019 `ibkr-order-submission-lifecycle.md` §4.8 + §10.4 — `cancel_order` worker-side wiring gap.
  - T-008 `web-components-feature-grids.md` — `<IbkrSubmissionGrids>`.
  - `apps/api/src/portfolio_outlook_api/action_draft.py:770-867` (POST `/action-draft/{id}/cancel-submitted` route + `_CANCELLABLE_STATUSES`).
  - `apps/web/components/IbkrSubmissionGrids.tsx:170-301` (cancel button + `handleCancel` + cancellable predicate).
  - `apps/web/components/SubmissionLifecycleDrawer.tsx` (the lifecycle drawer that shows cancellation_request events).
  - `apps/web/lib/apiClient.ts:1593-1599` (`cancelSubmittedActionDraft` TS binding).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **user-action workflow** narrative for the order-cancellation surface.
  - `user-cancel-submitted-order.md` — user-perspective trace of the cancel ritual: user on `/ibkr-acties` "Actief bij IBKR" tab → sees the red "Annuleer" button only for `cancellable = {submitted, accepted, working, partially_filled}` → clicks → `window.confirm` yes/no → POST `/action-draft/{id}/cancel-submitted` (server flips status to `pending_cancellation` + writes one `ibkr_submission_lifecycle` row with `event_type='cancellation_request'`) → row badge flips to "Annulering aangevraagd" → **and then nothing happens** because the worker has no loop that picks up `pending_cancellation` drafts to issue the actual `cancelOrder` call (T-019 §4.8 / §10.4 originating finding). The cancellation request is written but never executed.
- **Step 3 (one-line change):** write one user-action workflow reality doc tracing the cancel ritual end-to-end + surface the worker-side wiring gap from the user-action angle.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; user journey enumerated (4-step narrative); `_CANCELLABLE_STATUSES` cited (`action_draft.py:774-776`); confirm-only-not-token confirmation pattern documented (compared with BEVESTIG/JA gravity asymmetry); 2-write pattern documented (status flip + lifecycle row); worker-side wiring gap re-surfaced as the dominant finding (cancel writes are persistent never-executed records); ≥ 7 Phase 1c findings on the user-action surface incl. the worker-execution gap; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — approval flow (T-026 — merged sibling), submission lifecycle (T-019 — merged sibling), reconciliation passes (T-020 — merged sibling).

## Goal

Produce one user-action workflow reality doc narrating the cancel ritual from the user's perspective — `/ibkr-acties` "Actief bij IBKR" tab → red "Annuleer" button → `window.confirm` → API call → status flips to `pending_cancellation` → row badge updates → **request hangs because the worker has no loop to execute it**. The dominant finding is the user-visible deadlock: the cancel surface looks operational (button responds, status updates, badge renders) but the cancellation is never actually sent to IBKR.

## Context

`depends_on:` T-019. T-019 §4.8 + §10.4 originated the cancel-not-wired finding; T-027 surfaces it from the user-action angle and documents what the user sees vs what actually happens at IBKR.

## Touch scope

Create:
- `docs/reality/workflows/user-cancel-submitted-order.md`

Read: T-019 reality doc + `<IbkrSubmissionGrids>` (cancel button) + `<SubmissionLifecycleDrawer>` (the audit-trail surface the user inspects after) + the API cancel route.

## Acceptance criteria

- [ ] Output file exists.
- [ ] User journey enumerated (4-step narrative: arrive → see Annuleer button → click → confirm → see status change).
- [ ] `_CANCELLABLE_STATUSES = {submitted, accepted, working, partially_filled}` cited (`action_draft.py:774-776`).
- [ ] `window.confirm` (yes/no, not typed token) cancel pattern documented; gravity asymmetry vs BEVESTIG (T-025) and JA (T-026) noted.
- [ ] 2-write API behaviour documented: status flip to `pending_cancellation` + `ibkr_submission_lifecycle` row with `event_type='cancellation_request'`.
- [ ] **Worker-execution gap re-surfaced as the dominant Phase 1c finding** — cancel writes are persistent never-executed records.
- [ ] Cancel-only-from-actief-tab UX documented; `/ibkr-acties` tab structure cited.
- [ ] ≥ 7 Phase 1c findings on the user-action surface.
- [ ] No source modification.

## Out of scope

- Submission lifecycle (T-019 — merged sibling; the path to `submitted` that creates the rows the user can cancel).
- Approval flow (T-026 — merged sibling; how rows reach `submitted`).
- Reconciliation passes (T-020 — merged sibling; how `pending_cancellation` rows might eventually become `cancelled` via Pass B if the broker side cancels).
- `<SubmissionLifecycleDrawer>` deep dive (T-008 covers it at component level; T-027 cites it in the post-cancel audit-trail viewing only).
- Worker `cancel_order` adapter Protocol implementation (T-019 §4.8 originating finding; T-027 only re-surfaces).

## Verification

- File exists.
- `_CANCELLABLE_STATUSES` literal cited.
- `window.confirm` text cited.
- 2-write pattern cited (lifecycle audit row).
- Worker-execution gap surfaced as dominant finding.
- ≥ 7 Phase 1c findings.

## Notes

T-027 is the third of the 11 Track 1a Reality Workflows. The user-action surface here is the **most operationally misleading** in the entire frontend: every signal tells the user the cancel succeeded (button responds, status badge updates, no error) but the broker side never gets the request. A user could click Annuleer, see the badge change to "Annulering aangevraagd", close the browser, and a fill could land 30 minutes later because the worker never sent `cancelOrder`. Phase 1c-critical finding.
