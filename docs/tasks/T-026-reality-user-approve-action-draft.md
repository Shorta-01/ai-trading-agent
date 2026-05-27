```yaml
id: T-026
title: Write reality doc for user-approve-action-draft workflow
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/user-approve-action-draft.md` does not exist (verified). Every code site is already cited in T-018 + T-008 reality docs:
  - T-018 `action-draft-composition-and-approval.md` — the full functionality doc (covers composer + 11 A-K gates + state machines + frontend overview).
  - T-008 `web-components-feature-grids.md` §2 — `<ActionDraftGrid>` per-row actions.
  - `apps/web/components/ActionDraftGrid.tsx:130-195` (the 3 per-row action handlers — `handleApprove`, `handleDismiss`, `handleDelete`).
  - `apps/web/app/ibkr-acties/page.tsx:173-177` (the dashboard host, "Te keuren" tab).
  - `apps/api/src/portfolio_outlook_api/action_draft.py:654-693` (POST `/action-draft/{id}/approve` route).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **user-action workflow** narrative for the JA approval ritual.
  - `user-approve-action-draft.md` — user-perspective trace of the JA ritual: user lands on `/ibkr-acties` "Te keuren" tab → sees the per-row card with price + quantity + notional → clicks "Goedkeuren" → `window.prompt` asks for `JA` → typed-literal client-side compare → API call POST `/action-draft/{id}/approve` → state transition `proposed|edited → user_approved` via `update_status(actor="user")` → row turns green with "Goedgekeurd" badge → out-of-date banner says "IBKR-verzending wordt in een toekomstige update toegevoegd" (despite submission infrastructure existing). Distinct from T-018 which covered the full composition + approval functionality.
- **Step 3 (one-line change):** write one user-action workflow reality doc tracing the JA approval ritual end-to-end.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; user journey enumerated (4-step narrative from dashboard arrival → row in "Goedgekeurd" state); JA token literal cited (`ActionDraftGrid.tsx:141`); client-side-only enforcement documented (server doesn't validate token); 3 per-row actions documented with their 3 different browser-native dialog patterns; out-of-date "future update" banner text documented as Phase 1c finding; state transition + `actor="user"` audit documented; ≥ 7 Phase 1c findings on the user-action surface; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — action-draft composition + dry-run pipeline (T-018 — merged sibling), submission sweep (T-019 — merged sibling), order cancel (T-027 — next), AI explanation surface (T-023 — merged sibling).

## Goal

Produce one user-action workflow reality doc narrating the JA approval ritual from the user's perspective — dashboard arrival → row review → click "Goedkeuren" → type JA → submission → "Goedgekeurd" badge. Focus on (a) what the user sees, (b) what they type, (c) why JA is **client-side-only** (AGENTS.md §3.2 has a security blind spot here — re-documented as Phase 1c finding), (d) the out-of-date "future update" banner text that contradicts shipped submission infrastructure.

## Context

`depends_on:` T-018. T-018 covered composer + safety gates + state machine + JA token; T-026 narrows to the per-row user action surface and surfaces the AGENTS.md §3.2 client-only enforcement gap.

## Touch scope

Create:
- `docs/reality/workflows/user-approve-action-draft.md`

Read: T-018 reality doc + `<ActionDraftGrid>` + `/ibkr-acties/page.tsx` + the API approve route.

## Acceptance criteria

- [ ] Output file exists.
- [ ] User journey enumerated (4-step narrative: arrive → review row → JA prompt → see green badge).
- [ ] JA token literal cited (`ActionDraftGrid.tsx:141` `expectedToken = "JA"`).
- [ ] Client-side-only enforcement documented (server `/approve` route does not validate any token — `action_draft.py:678-688` shows the route only state-transitions).
- [ ] 3 per-row actions documented with their 3 browser-native dialog types — `window.prompt` for Goedkeuren + Dismiss reason, `window.confirm` for Delete.
- [ ] Out-of-date "Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd." banner text documented as Phase 1c finding (`ActionDraftGrid.tsx:341-342`; submission infrastructure IS shipped per T-019).
- [ ] State transition documented — `update_status(new_status="user_approved", transition_actor="user")` at `action_draft.py:679-684`.
- [ ] ≥ 7 Phase 1c findings on the user-action surface.
- [ ] No source modification.

## Out of scope

- Action-draft composition + 11 A-K dry-run gates (T-018 — merged sibling).
- Submission sweep + 12 Tier-1 gates (T-019 — merged sibling).
- User-cancel-submitted-order (T-027 — next).
- AI explanation surface (T-023 — merged sibling).
- `<ActionDraftEditForm>` (edit flow — out of scope per T-018; only the approve path is in T-026 scope).

## Verification

- File exists.
- All 3 per-row actions cited.
- JA token client-side-only enforcement cited.
- Out-of-date banner text + the contradiction with T-019 cited.
- ≥ 7 Phase 1c findings.

## Notes

T-026 is the second of the 11 Track 1a Reality Workflows. Important re-confirmation: AGENTS.md §3.2 ("no order without explicit user approval") is enforced **client-side only**. The API approve endpoint trusts the client to have gated. This is the most safety-critical user-action finding in the audit — a buggy or malicious client could approve drafts without ever showing a prompt. T-018 §5.3 originated this finding; T-026 surfaces it again from the user-action angle.
