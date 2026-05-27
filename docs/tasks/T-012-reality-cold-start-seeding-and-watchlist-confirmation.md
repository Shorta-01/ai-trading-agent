```yaml
id: T-012
title: Write reality doc for cold-start seeding + watchlist confirmation flow
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` does not exist (verified). T-012 is a synthesis task — every code site needed is cited in already-merged reality docs:
  - T-007 `worker-orchestration-and-scheduling.md` §9 (12-row starter set, idempotency, 4-table write pattern, race handling, not-yet-wired into orchestrator).
  - T-007 `worker-orchestration-and-scheduling.md` §6 (orchestrator `mode_detected="cold_start"` detection + `seed_runner` invocation + confirmation-state override → `"awaiting_watchlist_confirmation"`).
  - T-005 `api-actions-suggestions-and-watchlists.md` (watchlist confirmation routes).
  - T-008 `web-pages.md` §3.6 + `web-components-feature-grids.md` §11 (`VolglijstColdStartFlow.tsx`, the optimistic archive + BEVESTIG confirmation).
  - T-008 `web-components-status-and-shared.md` §5 (`ColdStartBanner.tsx` polling cadence + state values).
  - T-009 `web-api-client-and-text.md` §2 (the `apiClient.{getColdStartWatchlistItems, confirmWatchlist, deleteColdStartWatchlistItem, getWatchlistConfirmationState}` method catalogue).
- **Step 2 (one-line per touched file):** the one target file does not exist; it will hold the end-to-end cold-start workflow doc covering: initial state (no positions, no watchlist, no confirmation row) → starter seed (12 v1 assets, idempotent via UNIQUE) → state transition `cold_start → awaiting_watchlist_confirmation` → frontend banner + ColdStartFlow → optional archive of starter items → BEVESTIG token → state `unconfirmed → confirmed` → subsequent orchestrator fires move to `mode_detected="normal"`.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing the cold-start seeding + watchlist confirmation flow end-to-end across worker + API + frontend, no source modified.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists at locked filename; trigger conditions documented (worker `mode_detected="cold_start"` rule); 12-row starter set listed; 4 storage tables enumerated with their idempotency keys; frontend confirmation gate documented (literal `"BEVESTIG"` token); subsequent-fire normalisation explained; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — no proposal for what cold-start should do differently; no fix for the "starter_watchlist.seed_starter_watchlist is not yet wired into orchestrator's seed_runner slot" gap (Phase 1c surface, already noted in T-007).

## Goal

Produce one workflow reality doc tracing the cold-start seeding + watchlist confirmation flow end-to-end: orchestrator detection → starter watchlist seed → frontend banner → BEVESTIG confirmation → return-to-normal.

## Context

`depends_on:` T-005, T-007. The cold-start flow is the most user-visible Phase 0 onboarding surface, and it spans three runtime tiers (worker orchestrator + API endpoints + frontend confirmation flow) plus four storage tables. Synthesising it as a single document means future operators don't have to cross-reference 4-5 component docs to understand "what happens the first day a new IBKR account is connected."

## Touch scope

Create:
- `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md`

Read: T-005 + T-007 + T-008 + T-009 reality docs (already on disk after merge of prior PRs).

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Trigger conditions documented (`mode_detected="cold_start"` rule: account `None` OR both position + watchlist counts zero).
- [ ] The 12-row v1 starter set listed (5 broad UCITS ETFs + 5 European blue chips + 2 sector ETFs).
- [ ] 4 storage tables enumerated with idempotency keys: `cold_start_seed_audit` (UNIQUE on `ibkr_account_id`), `watchlist_items` (append per asset), `watchlist_confirmation_state` (upsert), `watchlist_confirmation_audit` (append-only state transitions).
- [ ] Frontend confirmation gate documented (literal `"BEVESTIG"` token at `VolglijstColdStartFlow.tsx:174-177`).
- [ ] Subsequent-fire normalisation explained (cold_start → awaiting_watchlist_confirmation → normal sequence).
- [ ] No source modification.

## Out of scope

- Per-module reality content (T-007 + T-008 + T-009 docs already cover that).
- The "starter_watchlist.seed_starter_watchlist is not yet wired into orchestrator's seed_runner slot" production-wiring gap (already surfaced in T-007 §9; this doc records the *intent* contract).
- Action drafts / forecasting flow (T-011 morning chain covers post-cold-start orchestration).

## Verification

- File exists.
- All 12 starter assets named + cited with their `starter_watchlist.py:NN` ranges.
- The `mode_detected` 3-step sequence (`cold_start` → `awaiting_watchlist_confirmation` → `normal`) appears in the doc with the orchestrator code anchors.

## Notes

T-007 §9 documents that `starter_watchlist.seed_starter_watchlist` is currently NOT wired into the production seed_runner — the contract exists but the wiring is a follow-up integration. This doc records the contract; the integration gap is a Phase 1c finding already raised.
