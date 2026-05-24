# Task 154 — Add real IBKR paper-only read-only account snapshot preflight for cash and positions without persistence or valuation

Task 153-L is completed as a documentation/product-lock recovery task that consolidated Version 1 product experience decisions into GitHub source-of-truth docs.

Proceed with **Task 154** as the next implementation task.

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

## Safety boundaries
- Version 1 remains paper-only.
- No live trading automation.
- No real-money automatic execution.
- No broker execution expansion in this task.
