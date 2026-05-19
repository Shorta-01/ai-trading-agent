# ADR 0003: IBKR integration approach for Version 1

## Context
Ai Trading Agent must integrate with IBKR while keeping Version 1 risk boundaries strict: the connected account must be paper-only and product safety behavior must match a real trading platform discipline.

## Decision
- Product logic depends on internal broker adapter contracts, not IBKR-specific SDK/HTTP objects.
- This task adds contracts, docs, and placeholder status only.
- No real IBKR API calls, credentials, sessions, or order submission are added here.
- Web API versus TWS API stays explicit and open for staged selection:
  - Web API implementation first, or
  - TWS API implementation first, or
  - dedicated spike before final path selection.

## Why not direct IBKR calls from API routes
Direct route-level calls would couple API handlers to transport/auth/session behavior, making safety controls, testing, and provider changes harder. Adapter contracts centralize risk checks, error mapping, and audit expectations.

## Why no credentials in this task
Credential handling requires separate security design, storage policy, and operational controls. Task 47 is intentionally limited to safe contracts and documentation without secret material.

## Why no order submission in this task
Order submission is a high-risk capability. It must come only after session checks, account mode verification, data snapshots, reconciliation controls, and explicit risk gates.

## Version 1 safety boundary
- Connected broker account must be paper-only.
- If account mode cannot be confirmed, order actions must be blocked.

## Consequences
- Enables implementation teams to add IBKR transport incrementally without changing product-domain interfaces.
- Improves testability by keeping adapters mockable and deterministic.
- Preserves strict safety posture while integration matures.

## Future implementation sequence
1. account/session status
2. account mode verification
3. cash snapshots
4. position snapshots
5. open order snapshots
6. execution snapshots
7. reconciliation
8. controlled order submission
