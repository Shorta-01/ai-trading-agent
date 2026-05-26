```yaml
id: T-004
title: Write reality docs for the API IBKR cluster
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

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is creation of three new docs under `docs/reality/components/`; none exist. The 26 source modules at `apps/api/src/portfolio_outlook_api/ibkr_*.py` (~5.9k lines) plus ADR 0002 + 0003 + `docs/integrations/ibkr-api-research.md` + the `AGENTS.md` boundary are read by three parallel subagents (one per output file).
- **Step 2 (one-line per touched file):** the three target files do not exist; each holds the reality doc for one sub-cluster:
  - `api-ibkr-connection-and-status.md` — connection / status / session adapters + TWS read-only runtime + ibapi facade + contracts (9 modules)
  - `api-ibkr-sync-and-snapshot.md` — sync orchestrator + sync-readiness/validation/persistence + account-snapshot persistence + preflight + market data + ibapi sync clients (12 modules)
  - `api-ibkr-submission-and-watchlists.md` — submission orchestrator + order-submission factory + ibapi order-submission/manual-status clients + watchlists (5 modules)
- **Step 3 (one-line change):** write three cited reality docs describing what the existing API IBKR cluster modules export, the read-only safety boundary (explicit `placeOrder`/`cancelOrder` call-site citation per doc), and the storage / state-machine ties.
- **Step 4 (criteria measurable):** yes — seven acceptance criteria: three files exist; each lists modules; safety boundary cited per file with `placeOrder`/`cancelOrder` refs (or "none in this sub-cluster"); account-mode detection cited in connection doc; storage write paths in sync doc; submission state machine in submission doc; no source file modified.
- **Step 5 (out-of-scope does not block goal):** confirmed — worker IBKR gateway and reconciliation are T-007 territory; frontend IBKR pages are T-008; no verdicts / gaps / findings.

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
