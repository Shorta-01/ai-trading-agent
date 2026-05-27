```yaml
id: T-019
title: Write reality doc for IBKR order submission lifecycle
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/ibkr-order-submission-lifecycle.md` does not exist (verified). Pure synthesis — every code site is cited in T-004 + T-007 reality docs:
  - T-007 `worker-actions-and-reconciliation.md` §§3-7 — order_builder, safety_recheck (12 gates), submitter (the place_order call site), submission_sweep (APScheduler tick), lifecycle_handler (IBKR callbacks).
  - T-007 §12 — `placeOrder` / `cancelOrder` safety boundary audit.
  - T-007 §13 — state-machine transitions written by the worker.
  - T-004 `api-ibkr-submission-and-watchlists.md` — `ibkr_ibapi_order_submission_client.py` (the API-side `placeOrder` at `:525`).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the post-approval IBKR submission lifecycle workflow doc.
  - `ibkr-order-submission-lifecycle.md` — sweep tick → 12-gate Tier-1 re-check → order builder (Decimal-to-float boundary) → tier-two account-ID re-read → `place_order(contract, order)` → IBKR callbacks via lifecycle_handler → state transitions → audit chain (3 tables).
- **Step 3 (one-line change):** write one cited workflow reality doc tracing the submission lifecycle end-to-end from `user_approved` → terminal IBKR states.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; submission sweep documented (one-per-tick locked); 12 Tier-1 gates documented; tier-two account-ID re-read documented; `place_order` single-authority + the API-side `placeOrder` doctrine drift surfaced; IBKR callback families documented + state transition map; 3 audit tables enumerated; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — action-draft composition + approval (T-018), reconciliation passes A/B/C (T-020), AI explanation (T-023).

## Goal

Produce one workflow reality doc tracing the post-approval IBKR order submission lifecycle end-to-end — APScheduler sweep tick → Tier-1 12-gate safety re-check → order builder (Decimal → float boundary) → Tier-2 account-ID re-read → single `place_order(contract, order)` adapter call → IBKR callback fan-out via lifecycle_handler → state transitions through `submitted → accepted → working → filled/partially_filled/cancelled/rejected` → 3 append-only audit tables.

## Context

`depends_on:` T-004, T-007. T-007 §§3-7 + §13 documented the worker-side submission cluster at module level; T-019 stitches them into the end-to-end "from user_approved to a terminal IBKR state" story. The worker-vs-API `placeOrder` doctrine drift (T-007 §12) is re-confirmed here.

## Touch scope

Create:
- `docs/reality/workflows/ibkr-order-submission-lifecycle.md`

Read: T-004 + T-007 reality docs (already on disk).

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Submission sweep documented (APScheduler tick + single-flight lock + one-per-tick `break`).
- [ ] 12 Tier-1 safety re-check gates documented (with the locked enum + Dutch failure messages).
- [ ] Tier-2 account-ID re-read at submit time documented (`fetch_managed_account_id` at submitter.py:173-185).
- [ ] `place_order(contract, order)` single-authority call site cited (`submitter.py:240`) + the API-side `placeOrder` doctrine drift (`ibkr_ibapi_order_submission_client.py:525`).
- [ ] IBKR callback families documented (`statusEvent` / `fillEvent` / `commissionReportEvent` / `cancelledEvent`) + state-transition map.
- [ ] 3 audit tables enumerated: `ibkr_submission_audit`, `ibkr_submission_lifecycle`, `ibkr_executions` (UNIQUE on `ibkr_exec_id`).
- [ ] No source modification.

## Out of scope

- Action-draft composition + approval (T-018 — produces the `user_approved` rows this flow consumes).
- Reconciliation passes A/B/C (T-020 — sibling that detects/heals divergences after the fact).
- AI explanation (T-023).
- The TWS read-only adapter (T-013 — separate IBKR flow).

## Verification

- File exists.
- All 12 Tier-1 gates cited.
- Worker `place_order:submitter.py:240` AND API `placeOrder:ibkr_ibapi_order_submission_client.py:525` both cited (doctrine drift surfaced).
- All 4 IBKR callback families cited.
- All 3 audit tables cited with their idempotency keys.

## Notes

T-019 is the most safety-critical workflow doc. The `place_order` single-authority claim is the foundation of AGENTS.md §3.2 ("no order without explicit user approval"); T-007 §12 already flagged that the API has an independent `placeOrder` call site, contradicting the lock. T-019 re-surfaces this for Phase 1c without proposing a fix.
