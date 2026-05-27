```yaml
id: T-025
title: Write reality doc for user-confirm-starter-watchlist workflow
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/user-confirm-starter-watchlist.md` does not exist (verified). Pure synthesis — every code site is already cited in T-012 + T-008 + T-009 reality docs:
  - T-012 `cold-start-seeding-and-watchlist-confirmation.md` — the full end-to-end functionality doc (covers the worker + storage + API + frontend full flow).
  - T-008 `web-components-feature-grids.md` §11 — `<VolglijstColdStartFlow>`.
  - T-008 `web-components-status-and-shared.md` §5 — `<ColdStartBanner>`.
  - T-008 `web-pages.md` §3.6 — `/volglijst` page.
  - T-005 `api-actions-suggestions-and-watchlists.md` — `watchlist_confirmation_routes.py` (5 routes).
  - `apps/web/components/VolglijstColdStartFlow.tsx:1-225` (the user-input form).
  - `apps/web/components/ColdStartBanner.tsx:1-93` (the 60s-polled global banner).
  - `apps/api/src/portfolio_outlook_api/watchlist_confirmation_routes.py:45 LOCKED_CONFIRMATION_PHRASE = "BEVESTIG"`, `:200-284 POST /watchlist/confirm`, `:139-198 GET /watchlist/confirmation-state`.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **user-action workflow** narrative for the BEVESTIG confirmation ritual.
  - `user-confirm-starter-watchlist.md` — user-perspective trace of the BEVESTIG ritual: banner sighting (60s poll) → click "Naar Volglijst" → see 12-row starter set → optionally delete rows (optimistic UI) → type `BEVESTIG` literal Dutch token (case-sensitive uppercase) → submit → 4-validation chain on the API side → state transition `unconfirmed → confirmed` → banner disappears → next morning chain runs `mode_detected="normal"`. Distinct from T-012 (which covered the cold-start mechanism end-to-end at the system level).
- **Step 3 (one-line change):** write one user-action workflow reality doc tracing the BEVESTIG confirmation ritual end-to-end.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; user journey enumerated (banner → page → input → submit); 4-validation chain on the API side documented; LOCKED_CONFIRMATION_PHRASE literal cited (case-sensitive); optimistic-UI archive flow documented; inline Dutch error rendering documented (5 distinct error states); audit chain from user perspective (`watchlist_confirmation_audit` write); ≥ 5 Phase 1c findings on the user-action surface; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — cold-start seed mechanism (T-012 already merged sibling — T-025 cross-references it; does not re-document the seed), worker orchestrator detection (T-007 §6, also covered in T-012). T-025 is the user-action surface only.

## Goal

Produce one user-action workflow reality doc narrating the BEVESTIG ritual from the user's perspective — banner sighting → page navigation → input → submission → state-transition. Focus on (a) what the user sees, (b) what the user types, (c) what error states render inline, (d) the audit trail from a user-facing perspective. T-012 covered the system mechanics; T-025 covers the user journey.

## Context

`depends_on:` T-012. The cold-start functionality was end-to-end documented in T-012; T-025 is the user-action overlay focused narrowly on the user's BEVESTIG ritual surface — what they see, what they type, what errors appear, what state transitions happen as a result of their action.

## Touch scope

Create:
- `docs/reality/workflows/user-confirm-starter-watchlist.md`

Read: T-012 reality doc + the 3 frontend components (`<ColdStartBanner>`, `<VolglijstColdStartFlow>`, `/volglijst/page.tsx`) + the API confirmation routes.

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] User journey enumerated (4-5 step narrative from banner sighting → confirmation success).
- [ ] `LOCKED_CONFIRMATION_PHRASE = "BEVESTIG"` cited (case-sensitive uppercase Dutch literal) at `watchlist_confirmation_routes.py:45`.
- [ ] 4-validation chain documented (phrase match, account configured, state pre-condition, row count > 0).
- [ ] Optimistic-UI archive flow documented (`handleArchive` at `VolglijstColdStartFlow.tsx:56-68` — client-side filter without server round-trip wait).
- [ ] Inline Dutch error rendering documented — at least 5 distinct error strings the user can see.
- [ ] Audit chain documented from user perspective (`watchlist_confirmation_audit` `unconfirmed → confirmed` write with `actor="user"`).
- [ ] ≥ 5 Phase 1c findings specific to the user-action surface.
- [ ] No source modification.

## Out of scope

- Cold-start seed mechanism (T-012 — merged sibling; the worker-side seed_runner + storage upserts).
- Worker orchestrator cold-start detection (T-007 §6, covered in T-012 §1).
- Asset-search via the contract picker (`<AssetIdentityPicker>` — used after confirmation; T-008).
- Post-confirmation normal-mode morning chain (T-011 — merged sibling).

## Verification

- File exists.
- All 3 frontend components cited with file:line.
- `LOCKED_CONFIRMATION_PHRASE` literal cited.
- All 4 validation gates cited.
- ≥ 5 Phase 1c findings.

## Notes

T-025 opens Track 1a Reality Workflows (T-025…T-035, 11 tasks total). The pattern for this track: per-user-action or per-system-tick doc, narrower in scope than the per-functionality workflow docs of T-011-T-024. Each task should be ~200-300 lines, focused on the actor (user or system tick) rather than the underlying mechanism. The mechanism docs (T-011…T-024) become the reference targets; T-025…T-035 stitch the user/system viewpoints on top.
