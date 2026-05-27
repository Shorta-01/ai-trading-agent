```yaml
id: T-028
title: Write reality doc for user-acknowledge-manual-review workflow
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/user-acknowledge-manual-review.md` does not exist (verified). Every code site is already cited in T-020 + T-008 reality docs:
  - T-020 `ibkr-reconciliation-passes-a-b-c.md` §5 (Pass C 24-hour escalation that produces the queue rows) + §6.4 (`manual_review_queue` table) + §7.5 (`POST /reconciliation/manual-review/{id}/acknowledge` route, the only mutating route in the reconciliation surface).
  - `apps/web/app/admin/reconciliation/page.tsx:1-390` (the full admin reconciliation page with Pending Manual Review section).
  - `apps/web/components/ReconciliationStatusWidget.tsx:1-201` (the dashboard card linking to the admin page).
  - `apps/api/src/portfolio_outlook_api/reconciliation.py:437-473` (the acknowledge route — idempotent, does NOT touch the underlying draft).
  - `apps/web/lib/apiClient.ts:1677-1685` (`acknowledgeManualReview` TS binding).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **user-action workflow** narrative for acknowledging Pass-C-escalated manual review queue rows.
  - `user-acknowledge-manual-review.md` — user-perspective trace of the acknowledge ritual: dashboard `<ReconciliationStatusWidget>` shows the pending count with warn flag → user clicks the card → navigates to `/admin/reconciliation` → sees "Wacht op handmatige beoordeling" table with the queue rows → clicks "Bevestig" → `window.prompt` for optional note → POST `/reconciliation/manual-review/{id}/acknowledge` → row's `resolution_status` flips to `acknowledged` → page refreshes (full 4-endpoint re-fetch) → row removed from "pending" list → **the underlying Action Draft is NOT touched** (idempotent route + draft stays in `requires_manual_review` forever). Distinct from T-020 (which covered the 3-pass mechanism end-to-end at the system level).
- **Step 3 (one-line change):** write one user-action workflow reality doc tracing the acknowledge ritual end-to-end + surface the "the draft never moves" expectation gap.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; user journey enumerated (dashboard widget → admin page → table → Bevestig → note prompt → row gone); admin-only route gating documented (no actions-area surface despite intent §3 D-class doctrine); table-based UI documented (vs per-row cards in T-026/T-027); `window.prompt` for note + `window.alert` for error (3rd browser-native dialog type pattern across the user-action surfaces); idempotent acknowledge documented (no state change to underlying draft); the "permanent `requires_manual_review` state" expectation gap surfaced as dominant finding; ≥ 7 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — reconciliation tick mechanism (T-020 — merged sibling), Pass C escalation logic (T-020 §5), unmatched-executions surface (also on the admin page but different row type).

## Goal

Produce one user-action workflow reality doc narrating the acknowledge ritual from the user's perspective — dashboard widget sighting → navigate to admin page → table review → Bevestig click → optional note → row disappears from pending list. The dominant finding is the expectation gap: clicking Bevestig **acknowledges that the user has seen the queue row** but does NOT touch the underlying draft. The draft remains in `requires_manual_review` forever; the queue row is the only thing that moves. The user is effectively closing a notification, not resolving a case.

## Context

`depends_on:` T-020. T-020 §5 documented Pass C escalation (drafts in `awaiting_reply_timeout` for ≥ 24h → `requires_manual_review` + one `manual_review_queue` row); §7.5 documented the acknowledge route as the ONLY mutating reconciliation route. T-028 stitches the user-action overlay on top.

## Touch scope

Create:
- `docs/reality/workflows/user-acknowledge-manual-review.md`

Read: T-020 reality doc + `<ReconciliationStatusWidget>` (dashboard card) + `/admin/reconciliation/page.tsx` (the page with the Bevestig table) + the API acknowledge route.

## Acceptance criteria

- [ ] Output file exists.
- [ ] User journey enumerated (dashboard card → admin page → table row → Bevestig → optional note → row gone).
- [ ] Surface lives on `/admin/reconciliation` admin route documented; absence from dashboard "actions area" surfaced as intent §3 + doctrine §10 gap.
- [ ] Table-based UI documented; contrast with per-row cards in T-026/T-027.
- [ ] `window.prompt` for note + `window.alert` for error documented; the 3rd distinct browser-native dialog pattern across the user-action surfaces (after T-025 `<input>`/T-026 `prompt`/T-027 `confirm`).
- [ ] Acknowledge route documented as **idempotent + draft-unaffecting** (intent: queue housekeeping, NOT case resolution).
- [ ] The "permanent `requires_manual_review` state" finding surfaced as dominant — no path moves the draft out without separate intervention.
- [ ] ≥ 7 Phase 1c findings.
- [ ] No source modification.

## Out of scope

- Reconciliation tick mechanism (T-020 — merged sibling).
- Pass A / Pass B / Pass C logic deep dives (T-020 §3-§5).
- Unmatched-executions surface (also on `/admin/reconciliation` but different row type; T-020 §7.6).
- `<ReconciliationStatusWidget>` deep dive (T-008 covers it at component level; T-028 cites it only as the entry point to the admin page).
- 4-tier B/C/D/E classification (T-020 §10.3 — already flagged as absent from code).

## Verification

- File exists.
- All 3 frontend surfaces cited (dashboard widget + admin page + acknowledge call).
- API route idempotency + draft-unaffecting documented.
- Permanent `requires_manual_review` state surfaced as dominant finding.
- ≥ 7 Phase 1c findings.

## Notes

T-028 is the 4th of 11 Track 1a Reality Workflows. The user-action surface here represents the most **conceptually misleading** ritual in the audit: the word "Bevestig" (= "Confirm") in this context means "I confirm I have seen this notification", NOT "I confirm the resolution of this case". The underlying draft is not moved. This mirrors the T-027 finding ("clicking Annuleer doesn't actually cancel anything at IBKR") in structure: the UI action looks operationally meaningful but is actually a thin notification-housekeeping action. The two findings together suggest a systematic pattern of "action UI surfaces" that disconnect from "action effects in the world".
