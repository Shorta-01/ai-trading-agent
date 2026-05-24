# Task 153 — Add real IBKR paper-only read-only account snapshot preflight for cash and positions without persistence or valuation

Task 152-R6 is completed as a repair-only merged-red fix after Task 152-R5 (`api` job `pytest`), enabling the remaining fake-client real-client gate prerequisites in test helpers, including dummy `ibkr_sync_host` / `ibkr_sync_port` / `ibkr_sync_client_id` values and correcting stale fake-client execution/error-path tests to use `_fake_client_ready_settings(...)` while preserving disabled-by-default runtime behavior and no-secret safety checks.

Continue with Task 153 only, while preserving current safety boundaries, disabled-by-default runtime behavior, and readiness semantics.
