# Task 151 — Isolated `ibapi` façade (dependency-only)

## 1. Purpose
Introduce a first production-side, dependency-isolated `ibapi` façade module with safe import preflight only.

## 2. Current state after Task 150-R
Task 150-R confirmed `ibapi` dependency/install/import preflight and restricted production-runtime checks.

## 3. What the façade adds
- New isolated module: `apps/api/src/portfolio_outlook_api/ibkr_ibapi_client_facade.py`.
- Typed availability and import-preflight result objects.
- Explicit dependency detection and explicit safe preflight imports.

## 4. What the façade does not add
- No TWS/Gateway connection behavior.
- No sockets opened by default.
- No endpoint wiring.
- No runtime factory wiring.
- No real low-level IBKR client implementation.

## 5. Dependency isolation rule
`ibapi` production references are allowed only inside the isolated façade module.

## 6. Import/preflight behavior
- `check_ibapi_dependency_available()` checks availability via `importlib.util.find_spec`.
- `load_ibapi_preflight_modules()` imports only `ibapi` and `ibapi.wrapper` via `importlib.import_module`.

## 7. No-socket/no-connection guarantee
Tests monkeypatch socket connect and verify no connection attempt during façade preflight calls.

## 8. Production runtime wiring status
The façade is intentionally not wired to runtime modules, status routes, or session adapter factory.

## 9. Test coverage
- New façade tests for safe import behavior and no runtime wiring.
- Updated dependency preflight test with narrow allowlist for façade-only production `ibapi` usage.

## 10. Safety boundaries preserved
- Runtime remains disabled by default.
- No account/portfolio sync runtime.
- No market-data runtime.
- No FX runtime.
- No suggestions, action drafts, orders, or broker execution.
- `ib_insync` not added.

## 11. Recommended next task
Task 152 — Add disabled-by-default `ibapi` manual status client skeleton behind the isolated façade without connecting to TWS/Gateway.
