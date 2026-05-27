```yaml
id: T-018
title: Write reality doc for action-draft composition + approval flow
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/463
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/action-draft-composition-and-approval.md` does not exist (verified). Single inline read for the portfolio state-machine vocabulary (`packages/portfolio/.../action_draft_state_machine.py:37-136`). Other code sites already cited in:
  - T-002 `portfolio-guards-and-state-machines.md` — `action_draft_safety.py` dry-run pipeline.
  - T-007 `worker-actions-and-reconciliation.md` §1 (composer) + §13 (state-machine transitions).
  - T-005 `api-actions-suggestions-and-watchlists.md` — `action_draft.py` + `action_draft_submission.py` + `action_draft_sync.py` API routes.
  - T-008 `web-components-feature-grids.md` §§1-2 — `<ActionDraftEditForm>` + `<ActionDraftGrid>`.
  - T-009 `web-api-client-and-text.md` §2 — `apiClient` action-draft methods.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the full action-draft composition + approval workflow doc.
  - `action-draft-composition-and-approval.md` — composer (worker-side pure function) → 11 A-K safety gates in dry-run pipeline → `proposed` initial state → user edit / dismiss / delete / approve via frontend → BEVESTIG-token-equivalent confirmation → submission to IBKR submission sweep → two-vocabulary state-machine map (portfolio enum vs storage transitions).
- **Step 3 (one-line change):** write one cited workflow reality doc tracing action-draft composition + approval end-to-end.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; composer entry points (`compose_action_draft_from_decision_package` + `compose_action_draft_user_supplied`) documented; dry-run pipeline with 11 A-K safety gates documented; both state-machine vocabularies (portfolio enum + storage map) mapped with cross-references; frontend approval flow with confirmation gating documented; hard `safe_for_submission=False` floor documented; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — IBKR submission lifecycle (T-019), reconciliation passes (T-020), AI explanation (T-023). Out-of-scope for this doc because they happen AFTER `user_approved`; T-018 covers compose → approval boundary only.

## Goal

Produce one workflow reality doc tracing action-draft composition + approval end-to-end — from worker composer (decision-package-driven OR user-supplied) → 11 A-K dry-run safety gates → `proposed` initial state → user actions (edit / dismiss / delete / approve via BEVESTIG-equivalent confirmation) → handoff to IBKR submission sweep (`user_approved` terminal of T-018 scope).

## Context

`depends_on:` T-002, T-005, T-007, T-008. Action drafts are the **only path** through which the system can submit an order to IBKR. The composer is pure-function (worker side); the API serves the read/edit/approve routes; the frontend `<ActionDraftGrid>` is the user's primary review surface. T-018 stitches these four halves into one end-to-end doc and clarifies the two state-machine vocabularies (the portfolio enum vs the storage transition map).

## Touch scope

Create:
- `docs/reality/workflows/action-draft-composition-and-approval.md`

Read: T-002 + T-005 + T-007 + T-008 + T-009 reality docs + the portfolio state-machine module.

## Acceptance criteria

- [ ] Output file exists.
- [ ] Composer entry points documented (`compose_action_draft_from_decision_package` + `compose_action_draft_user_supplied`).
- [ ] Dry-run pipeline + 11 A-K safety gates documented (sizing, cash, mode, position, hold-time, etc.).
- [ ] Both state-machine vocabularies mapped: portfolio enum (`DRAFT → SAFETY_CHECKED → USER_APPROVED → ...`) + storage `_ACTION_DRAFT_TRANSITIONS` map (`proposed → edited → user_approved → submitted → ...`).
- [ ] Frontend approval flow documented (`<ActionDraftGrid>` + `<ActionDraftEditForm>` + JA confirmation token).
- [ ] Hard `safe_for_submission=False` floor + initial `status="proposed"` documented.
- [ ] No source modification.

## Out of scope

- IBKR submission lifecycle (T-019 future — picks up at `user_approved → submitted`).
- IBKR reconciliation passes A/B/C (T-020 future).
- AI explanation (T-023 future).
- Action-draft sync route (covered by T-005 — administrative; not the user flow).

## Verification

- File exists.
- Both state vocabularies cited with file:line anchors.
- The 11 A-K gates enumerated.
- JA token confirmation cited at `<ActionDraftGrid>` anchor.
- `safe_for_submission=False` cited.

## Notes

The two-state-vocabulary island (portfolio enum vs storage map) is the largest piece of architectural drift in the action-draft surface. T-007 §13 already documented the transition keys the worker writes (`submitted → accepted → working → ...`); T-018 documents the user-facing pre-submission vocabulary (`proposed → edited → user_approved → ...`) and bridges them. Phase 1c is likely to recommend unifying these.
