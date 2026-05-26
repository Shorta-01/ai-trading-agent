# Order lifecycle — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0009-order-lifecycle-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§4.2, §15)

## Scope

This document covers what happens to an order **after** the second approve transmits it to the market: partial fills, exchange rejections, in-flight modify/cancel, and the relationship to the Open orders grid.

The pre-submission flow is in `docs/intent/action-draft-state-machine.md`; the submission boundary (handoff to Open orders grid) is shared between the two documents.

## 1. Partial fills

**Policy: let them ride.** v1 does not auto-cancel the unfilled remainder or split into a new order.

- Each partial fill event is captured immediately. The portfolio updates per event (Task 134 lock: "Fill flow updates the durable position snapshot").
- The Open orders grid shows partial-fill status inline as `partial-filled N/M` (e.g. 60/100).
- The audit log records every partial fill event as a distinct entry, never collapsed into a sum.
- The order remains in the Open orders grid until fully filled, cancelled, or expired (DAY orders expire at market close).

## 2. Exchange rejections

Handled identically to IBKR rejections in the action-draft layer: the classification model is the same (recoverable / unrecoverable), and the mapping is configurable.

### Default classifications

- **Recoverable.**
  - Limit-up / limit-down condition.
  - Exchange rule breach the user can fix (e.g. lot-size, tick-size, away-from-market price).
- **Unrecoverable.**
  - Symbol halt.
  - Asset class not permitted on the account.
- **Default for unknown codes: unrecoverable.** Fail closed.

Recoverable rejections re-surface the order ticket with the rejection reason inline. The user can edit (which re-runs `whatIfOrder`) and resubmit. Unrecoverable rejections transition the order to a terminal state in the audit log and remove it from the Open orders grid.

The mapping table is configurable in Category 3 of `docs/intent/settings-and-credentials.md`. Initial population is doctrine §15 open — to be filled during T-018 reality.

## 3. In-flight modify and cancel

Available on **any unresolved order** in the Open orders grid (states: `parked`, `transmitted`, `partial-filled`).

### Modify

- Triggered by user edit in the Open orders grid.
- Re-runs hybrid validation: client-side instant checks (`docs/intent/dashboard-and-order-flow.md` §5.6) + `whatIfOrder` round-trip before the modify is sent to IBKR.
- If IBKR rejects the modify, the original order remains as-is; the rejection reason is shown.
- Audit log records the modify event with both original and modified field values per the edit-as-override rule (doctrine §4.5).

### Cancel

- **Fire-and-forget** at the IBKR API level. The system sends `cancelOrder()` and waits for the IBKR callback.
- Race condition with a just-arrived fill is **normal and expected**. If a fill arrives concurrent with the cancel:
  - Full fill before cancel reaches IBKR: cancel is no-op; the order completes normally.
  - Partial fill before cancel reaches IBKR: the cancel applies only to the unfilled remainder.
- Both outcomes are audit-logged.

## 4. Open orders grid: scope

Per doctrine §4.2 (revised). The grid covers **both** order states:

- **Parked** — awaiting the second approve. No IBKR exchange transmission yet (IBKR holds it parked).
- **Transmitted** — handed to the exchange, partially or fully unfilled.

Status badges per row: `parked` / `transmitted` / `partial-filled N/M`.

Resolved orders (fully filled, cancelled, rejected) leave the grid and appear in the audit trail screen but not the dashboard.

## 5. Bulk behaviour

Per doctrine §4.4 and `docs/intent/action-draft-state-machine.md` §7:

- **Approve / submit is individual-only.**
- **Cancel may be bulk.** A bulk cancel applies to all selected unresolved rows; the audit log records the bulk as a coherent batch event. Each cancel still passes through the same fire-and-forget mechanism per order.

## 6. Open questions

- Initial population of rejection classification mapping (doctrine §15)
- Behaviour when a DAY order is partially filled at market close — current intent is to let the unfilled remainder expire and not auto-cancel-and-recompose. Subject to revisit.

## 7. Cross-references

- Doctrine §4.2 (Open orders grid scope)
- Doctrine §4.4 (bulk cancel)
- Doctrine §15 (open questions)
- `docs/intent/dashboard-and-order-flow.md` (UX of the Open orders grid)
- `docs/intent/action-draft-state-machine.md` (everything before transmission)
- `docs/intent/reconciliation.md` (reconciliation passes verify what the grid shows against IBKR truth)
- `docs/intent/settings-and-credentials.md` (Category 3 hosts the classification mapping)
- Existing Task 134 product locks (submission state machine and post-fill semantics)
