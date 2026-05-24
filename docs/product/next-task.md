# Task 155 — Add real IBKR account-mode-aware read-only account snapshot preflight for cash and positions without persistence or valuation

Task 154-L is completed as a documentation/product-identity correction and source-of-truth lock task.

Proceed with **Task 155** as the next implementation task.

## Scope (copy-paste lock)
- Use the verified manual IBKR status path.
- Request read-only cash/positions preflight data only.
- No persistence yet (unless explicitly re-scoped in a future task).
- No valuation logic.
- No market-data fetch.
- No FX fetch.
- No suggestions runtime.
- No action-draft runtime.
- No order submit/modify/cancel.
- No broker execution.

## Safety boundaries
- AI Trading Agent is account-mode-aware; current implementation slices may be paper-gated where safety requires it.
- Paper mode is a safety/testing context, not product identity.
- No real-money automatic execution.
- No broker action without explicit user approval and final confirmation.
