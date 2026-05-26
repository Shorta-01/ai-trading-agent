# Action draft — state machine and safety guards

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0008-action-draft-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§4, §5, §15)

## Scope

This document is the **canonical, full-detail** specification of the action draft layer: state machine, safety guards, retries, recoverable-vs-unrecoverable rejection classification, and auto-withdrawal. `docs/intent/dashboard-and-order-flow.md` links here for depth; this file is the source.

## 1. What an action draft is

An action draft is the **user-owned** layer between a decision package's suggested action and a real order in IBKR. It is created when the user clicks "Maak actie" on a decision package detail page or on a watchlist row (per Task 133 lock — see `docs/product/locked-decisions.md` "Task 133 product locks"). Action drafts are not auto-created.

## 2. State machine

States (locked enum):

- `drafted` — Just created from a decision package. Editable. Awaiting user review.
- `user-approved` — User pressed Approve. Locked from further edits. Awaiting worker submission.
- `submitting` — Worker has picked it up and is in the middle of `placeOrder()`. Not yet acknowledged by IBKR.
- `ibkr-acknowledged` — IBKR returned a `permId`. Order is in IBKR's hands.
- `parked` — IBKR confirms the order is parked (visible in Open orders grid). Awaiting the second approve.
- `user-rejected` — User explicitly rejected the draft. Terminal.
- `withdrawn-by-system` — System withdrew the draft (auto-withdrawal of a stale draft, or supersede by a newer decision package). Terminal.
- `failed` — Submission failed in a way that cannot be recovered (unrecoverable rejection per §5). Terminal.

Transitions:

```
drafted --(approve)--> user-approved --(worker picks up)--> submitting --(permId received)--> ibkr-acknowledged --(IBKR confirms parked)--> parked
   |                                                              |                                |
   |                                                              v                                v
   |-- (reject)             ----> user-rejected               failed                       (handed off — open-orders grid takes over)
   |
   |-- (supersede / 24h stale) ----> withdrawn-by-system
```

The boundary between `parked` and the Open orders grid: once `parked`, the order's lifecycle is owned by the Open orders grid (see `docs/intent/order-lifecycle.md`). The action draft retains a pointer to the IBKR `permId` for audit traceability.

## 3. Retry policy

Transient submission failures (network glitch, IBKR timeout, no immediate ack) are retried up to **3 attempts** with exponential backoff:

- Attempt 1: immediate
- Attempt 2: after 1 second
- Attempt 3: after 4 seconds
- Attempt 4: after 16 seconds (final)

After the final attempt, the draft transitions to `failed` with the last rejection captured in the audit log.

## 4. Recoverable vs unrecoverable rejection classification

When IBKR or the exchange rejects, the rejection is classified into one of two categories. The mapping is **configurable** (Category 3 in `docs/intent/settings-and-credentists.md` — note: typo retained intentionally if seen, see settings file). Initial mapping to be populated during T-018 reality (doctrine §15 open).

### Default classifications (placeholders, subject to T-018 reality)

- **Recoverable.** Limit-up / limit-down condition, exchange rule breach that the user can fix by adjusting the ticket, transient connection error.
- **Unrecoverable.** Symbol halt, asset class not permitted on the account, insufficient permissions.
- **Default for unknown codes: unrecoverable.** Fail closed.

A recoverable rejection re-surfaces the ticket in `drafted` (or `user-approved` waiting state) with the rejection reason inline; the user adjusts and re-approves. An unrecoverable rejection transitions to `failed` and surfaces in the audit log.

## 5. Auto-withdrawal of stale drafts

A draft in `drafted` for more than 24 hours is **withdrawn-by-system**. The user is not pinged; the next morning's evaluation will re-propose if still warranted (doctrine §7).

Supersession by a newer decision package is documented in `docs/intent/decision-package.md` §7 and Task 133 product locks ("stale-draft flagging, locked uit brainstorm Q4 'flag, never modify'"). Existing semantics preserved.

## 6. Eleven safety guards

Every approve (whether on a `drafted` ticket or on the Open orders grid second approve) re-runs the full guard set. Guards are classified as **hard-block** (refuses submission) or **soft-warn** (requires user confirmation to proceed). Every block is audit-logged.

| ID | Guard | Class | Description |
|----|-------|-------|-------------|
| A | account-mode-match | hard-block | The connected IBKR account's mode (PAPER/REAL) must match the draft's `account_mode_at_creation`. Mid-flight mode change refuses submission. |
| B | connection-up | hard-block | IBKR session must be connected. No queuing through outages. |
| C | account-id-match | hard-block | The connected IBKR account ID must match the draft's `ibkr_account_id`. |
| D | market-hours | hard-block | The instrument's primary exchange must be open. No after-hours submissions in v1. |
| E | duplicate-in-flight | hard-block | No two drafts for the same (account, conid, side) may be in `user-approved` or `submitting` simultaneously. |
| F | cash-sufficient | hard-block | `usable_cash` (defined in Task 88I lock) must cover the draft's notional + estimated commissions. |
| G | position-sufficient | hard-block | For SELL, the held quantity must be ≥ the draft's quantity. |
| H | cooldown | hard-block | 60-second cooldown between drafts on the same conid (per Task 134 lock). |
| I | daily-limit | hard-block | Maximum approvals per 24h (default 5; per Task 134 lock). |
| J | drawdown | hard-block (hard) / soft-warn (soft) | Soft 5%/5-day drawdown: BUY blocked, SELL allowed (warning). Hard 10%/20-day: all blocked until user acknowledges (per Task 134 lock). |
| K | fomo-drift | hard-block | Price drift > 1.5% from the approved limit since draft creation requires re-approval at the new price (per Task 134 lock). |

### Check timing

- **At creation:** all guards evaluated. Failed guards prevent the draft from being created at all.
- **At submission (worker pickup):** all guards re-evaluated. **The submission-time evaluation is authoritative.** A guard that passed at creation but fails at submission blocks submission and the draft returns to `drafted` with the failed guard surfaced.

### Audit

Every guard block writes one audit-log row with `{draft_id, guard_id, evaluated_at, result, context}`. A guard that passes is not logged individually; the overall approve event references which guards were evaluated.

## 7. Bulk behaviour

Per doctrine §4.4:

- **Approval is individual-only.** No "approve all".
- **Reject and cancel may be bulk.** A single shared one-word reason applies to all selected rows; the audit log records the bulk operation as a coherent batch event.

## 8. Edit-as-override

Per doctrine §4.5:

- When the user edits any field, both the original system value and the user's value are recorded per field.
- Submission proceeds with the edited value.
- Validation (`docs/intent/dashboard-and-order-flow.md` §5.6) runs against the edited value.
- The original system value never disappears from the audit trail.

## 9. Open questions

- Initial population of rejection classification mapping (doctrine §15)
- Exact retry backoff tuning (current 1s/4s/16s is a placeholder)
- Whether to permit any after-hours order types in v1 (currently no)

## 10. Cross-references

- Doctrine §4 (two grids, two approvals + §4.4 bulk + §4.5 edit-as-override)
- Doctrine §5 (order content; guards F/G/J consume sizing context)
- Doctrine §15 (open questions)
- `docs/intent/dashboard-and-order-flow.md` (UX surface — links here for depth)
- `docs/intent/order-lifecycle.md` (what happens once the draft hands off to the Open orders grid)
- `docs/intent/decision-package.md` (action drafts derive from packages)
- `docs/intent/settings-and-credentials.md` (Category 3 hosts the configurable thresholds)
- Existing Task 133 / 134 / 135 locks in `docs/product/locked-decisions.md`
