# Task 145 — Add dependency-free manual TWS/Gateway read-only status-check runtime client boundary with injected fake client tests only

## Why
- Task 144 preflight-checklist is vastgesteld en definieert harde gates vóór runtime wiring.
- Volgende kleinste veilige stap is een dependency-free runtime-client boundary met fake-client tests, zonder real connectivity enablement by default.

## Scope
- Implement a manual/status-check-only runtime client boundary behind explicit runtime opt-in.
- Injected fake low-level client tests verplicht voor lifecycle, timeout, account-mode en failure mappings.
- Keep runtime disabled by default; no auto-connect, no reconnect loop, no persistent session manager.
- No third-party IBKR dependency (`ibapi`, `ib_insync`) in this slice.

## Non-goals
- No real low-level IBKR client implementation.
- No orderflow, broker execution, market-data runtime, FX runtime, suggestions, action drafts or sync runtime expansion.
