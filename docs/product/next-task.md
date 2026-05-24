# Task 153 — Add real IBKR paper-only read-only account snapshot preflight for cash and positions without persistence or valuation

Task 152-R3 is completed as a repair-only merged-red fix after Task 152-R2 (`api` job `mypy src`, mypy `[valid-type]`), replacing the static nested class with runtime `ibapi` base variables by a mypy-compatible isolated factory approach while preserving typed protocol/factory boundary and real manual status-check capability.

Continue with Task 153 only, while preserving current safety boundaries, disabled-by-default runtime behavior, and readiness semantics.
