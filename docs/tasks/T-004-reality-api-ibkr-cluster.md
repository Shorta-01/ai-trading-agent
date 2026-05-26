```yaml
id: T-004
title: Write reality docs for the API IBKR cluster
phase: P1
status: locked
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Goal

Produce three reality docs covering the 26-module IBKR sub-cluster inside `apps/api/`, split by responsibility.

## Context

The IBKR cluster is the largest single sub-tree in the API. 26 modules grouped into connection/status, sync/snapshot, and submission/watchlists. ADR 0002 and 0003 plus `docs/integrations/ibkr-api-research.md` are the relevant intent inputs. `depends_on:` —.

## Touch scope

Create:
- `docs/reality/components/api-ibkr-connection-and-status.md`
- `docs/reality/components/api-ibkr-sync-and-snapshot.md`
- `docs/reality/components/api-ibkr-submission-and-watchlists.md`

Read: all 26 `apps/api/src/portfolio_outlook_api/ibkr_*.py` files; ADR 0002, 0003; `docs/integrations/ibkr-api-research.md`; AGENTS.md (for the no-live-trading boundary).

## Acceptance criteria

- [ ] Three output files at the locked filenames.
- [ ] Each file lists its in-scope modules.
- [ ] Read-only safety boundary documented per file: explicit cite of any `placeOrder` / `cancelOrder` call sites (or assertion that none exist in that sub-cluster).
- [ ] Account-mode detection (paper / live / unknown) is documented in `api-ibkr-connection-and-status.md` with file:line refs.
- [ ] Storage write paths (which snapshot tables each module persists into) are documented with refs in `api-ibkr-sync-and-snapshot.md`.
- [ ] Submission state machine is documented in `api-ibkr-submission-and-watchlists.md` (link to `portfolio.action_draft_state_machine`).
- [ ] No source modification.

## Out of scope

- Worker IBKR gateway + reconciliation (covered by T-007).
- Frontend IBKR pages and components (covered by T-008).
- No verdicts / gaps / findings.

## Verification

- All three files exist.
- `grep -lE 'placeOrder|cancelOrder' apps/api/src/portfolio_outlook_api/ibkr_*.py` → every result is referenced in the reality doc that covers it.

## Notes

Module groupings:
- `api-ibkr-connection-and-status.md`: `ibkr_connection_*`, `ibkr_status`, `ibkr_session_*`, `ibkr_tws_*`, `ibkr_ibapi_client_facade`, `ibkr_contracts`.
- `api-ibkr-sync-and-snapshot.md`: `ibkr_sync*`, `ibkr_account_snapshot*`, `ibkr_market_data`, `ibkr_ibapi_sync_client`, `ibkr_ibapi_account_snapshot_client`.
- `api-ibkr-submission-and-watchlists.md`: `ibkr_submission`, `ibkr_order_submission_factory`, `ibkr_ibapi_order_submission_client`, `ibkr_ibapi_manual_status_client`, `ibkr_watchlists`.
