Task 147 — Add explicit operator-facing readiness diagnostics for manual TWS/Gateway status-check endpoint without enabling runtime connectivity.

# Task 146 - Add manual read-only TWS/Gateway status-check endpoint shell

## Why
Task 145 introduced the dependency-free manual runtime boundary with fake-client tests only.
A small follow-up endpoint shell can expose this safely behind disabled runtime gates.

## Scope
- Keep runtime disabled by default.
- Add endpoint shell only, no real IBKR client, no sockets by default.
- Use injected fake clients in tests only.
- Keep order/suggestion/action booleans blocked.
