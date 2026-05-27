```yaml
id: T-013
title: Write reality doc for IBKR read-only sync (positions + cash) flow
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/458
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/ibkr-readonly-sync-positions-cash.md` does not exist (verified). T-013 is a synthesis task — every code site needed is cited in already-merged reality docs:
  - T-004 `api-ibkr-sync-and-snapshot.md` (9 sync modules — `ibkr_sync.py`, `ibkr_sync_adapter_factory.py`, `ibkr_sync_contracts.py`, `ibkr_sync_persistence.py`, `ibkr_sync_read_model.py`, `ibkr_sync_readiness.py`, `ibkr_sync_validation.py`, `ibkr_account_snapshot_persistence.py`, `ibkr_account_snapshot_preflight.py`).
  - T-004 `api-ibkr-connection-and-status.md` (connection routes + status + read-model + `ibkr_tws_readonly_*` modules).
  - T-007 `worker-orchestration-and-scheduling.md` §7 (`ibkr_gateway.py` — TWS connect lifecycle + tier-two paper-account guard + read-only `IbClientProtocol`).
  - T-008 frontend reality docs: `<PortefeuilleRealtimeSection>` (positions+cash polling) and `<AccountModeBadge>` (mode pill polling).
  - T-009 `web-api-client-and-text.md` §2 (12 IBKR-related `apiClient.*` method catalogue).
  - Storage tables `ibkr_sync_runs`, `ibkr_position_snapshots`, `ibkr_cash_snapshots`, `ibkr_open_orders`, `ibkr_executions` from `packages/storage/.../metadata.py`.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the end-to-end read-only sync workflow doc.
  - `ibkr-readonly-sync-positions-cash.md` — trigger model (manual + scheduled), API ↔ Worker boundary, tier-two paper-account guard, sync_run lifecycle, persisted snapshots, frontend polling cadence, audit chain, out-of-scope for order submission + reconciliation.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing the read-only IBKR sync flow end-to-end from trigger to persisted snapshot rows, citing T-004/T-007/T-008/T-009 reality docs.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; trigger model documented (manual `POST /ibkr/sync/run` + status poll); tier-two paper-account guard documented with the prefix + behavioural check anchors; sync_run lifecycle documented (table + state transitions); 4 persisted snapshot tables enumerated; frontend polling cadence documented (`AccountModeBadge` 30 s + `PortefeuilleRealtimeSection` 30 s); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — order submission (T-019), reconciliation (T-020), TWS read-only runtime (separate read-only adapter, not the sync flow).

## Goal

Produce one workflow reality doc tracing the IBKR read-only sync end-to-end — trigger (manual + scheduled) → API `ibkr_sync.run_sync` → worker `IbkrGateway.connect` with tier-two paper-account guard → read-only IbClientProtocol calls (`managedAccounts`, `accountSummary`, `positions`) → persisted snapshot rows → frontend display.

## Context

`depends_on:` T-004, T-007. The read-only sync is the data-feed loop everything else (forecasting, daily briefing, action-draft sizing) consumes. T-004 documents the API-side sync routes + persistence; T-007 §7 documents the worker-side IBKR gateway connect lifecycle. T-013 documents how they chain together.

## Touch scope

Create:
- `docs/reality/workflows/ibkr-readonly-sync-positions-cash.md`

Read: T-004 + T-007 + T-008 + T-009 reality docs (already on disk).

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Trigger model documented (manual `POST /ibkr/sync/run` + status poll via `GET /ibkr/sync/status`).
- [ ] Tier-two paper-account guard documented (prefix-check + behavioural-check + the disagreement-blocks-connect rule) with `ibkr_gateway.py` anchors.
- [ ] `ibkr_sync_runs` lifecycle documented (table + state transitions through the sync_run row).
- [ ] 4 persisted snapshot tables enumerated: `ibkr_position_snapshots`, `ibkr_cash_snapshots`, `ibkr_open_orders`, `ibkr_executions`.
- [ ] Frontend polling cadence documented (AccountModeBadge 30 s, PortefeuilleRealtimeSection 30 s).
- [ ] No source modification.

## Out of scope

- Order submission flow (T-019).
- Reconciliation passes (T-020).
- The `ibkr_tws_readonly_*` runtime adapter (separate from the sync flow; not part of T-013 scope).

## Verification

- File exists.
- `ibkr_sync_runs` + `ibkr_position_snapshots` + `ibkr_cash_snapshots` + `ibkr_open_orders` + `ibkr_executions` all appear with their `metadata.py` anchors.
- `IbkrGateway` tier-two guard (prefix + behavioural) appears.
- `<AccountModeBadge>` + `<PortefeuilleRealtimeSection>` cited.

## Notes

The read-only sync is the **only currently-implemented IBKR data path** — order submission lives in `apps/api/src/.../ibkr_ibapi_order_submission_client.py:525` (camelCase `placeOrder` in the API, see T-004 + T-007 §5) and `apps/worker/src/.../ibkr_submission/submitter.py:240` (snake_case `place_order` adapter in the worker). Per the doctrine, `place_order` ownership is supposed to be worker-only — T-007 §5 documents the doctrine drift. This doc is read-only and out-of-scope for that gap.
