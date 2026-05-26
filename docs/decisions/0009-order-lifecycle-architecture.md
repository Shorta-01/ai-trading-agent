# 0009 — Adopt the order-lifecycle architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/order-lifecycle.md`, `docs/intent/dashboard-and-order-flow.md`, doctrine §4.2, §15.

## Context

T-019 (`ibkr-order-submission-lifecycle.md` reality) and the discussion of the IBKR-todo grid surfaced three questions not previously locked:

1. What happens with partial fills? Auto-cancel the remainder, split, or let-them-ride?
2. How are exchange rejections classified vs IBKR rejections? Same model or different?
3. Can the user modify or cancel a transmitted (in-flight) order, and what are the race-condition semantics?

The Open orders grid scope itself was also expanded in the doctrine §4.2 revision — it now covers both parked and transmitted orders, with status badges.

## Decision

Adopt the lifecycle behaviour defined in `docs/intent/order-lifecycle.md`:

- **Partial fills: let them ride.** No auto-cancel of remainder, no split. Each partial fill is one audit event; portfolio updates per event. Status badge `partial-filled N/M` on the row.
- **Exchange rejections handled identically to IBKR rejections.** Same recoverable / unrecoverable classification; same configurable mapping; default-unrecoverable for unknown codes.
- **In-flight modify and cancel allowed on any unresolved order.** Modify re-runs hybrid validation (`whatIfOrder`). Cancel is fire-and-forget; race conditions with just-arrived fills are normal and audit-logged.
- **Open orders grid scope: parked + transmitted + partial-filled.** Resolved orders leave the grid; they appear in the audit trail screen but not the dashboard.

## Alternatives considered

- **Auto-cancel partial-fill remainder.** Rejected: would surprise users who expected the full order to fill eventually. Manual cancel remains the explicit path.
- **Separate classification model for exchange vs IBKR rejections.** Rejected: from the user's perspective the system needs to decide "show me the ticket again so I can fix it" vs "this is dead". The classification axis is the same.
- **Disallow modify on transmitted orders.** Rejected: a fill that's drifted price-wise during transmission is exactly when the user wants to modify the limit. IBKR supports modify; we should too.

## Consequences

- T-019 and T-020 reality describe existing submission and reconciliation code against this intent.
- T-027 (`user-cancel-submitted-order.md`) walks the cancel UX including race-condition wording.
- The Open orders grid UX (`docs/intent/dashboard-and-order-flow.md` §4.2) is the canonical surface for the lifecycle decisions above.
- Initial rejection-code → recoverable/unrecoverable mapping remains open (doctrine §15) — to be populated during T-018 reality.
