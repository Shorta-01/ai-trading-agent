# Dismissed tool findings — explicit one-line reason per dismissal

## T-050 — ruff baseline (2026-05-26)

**Tool:** `ruff 0.15.8`
**Command:** `ruff check apps/api apps/worker packages/domain packages/portfolio packages/storage --output-format=json`
**Exit code:** 0
**Findings in output:** **0** (raw JSON output: `[]`)
**Per-package config:** `select = ["E", "F", "I", "UP", "B"]`, `line-length = 100`, `target-version = "py312"`.

The baseline is clean against the currently-selected rule families. The dismissal entries below cover the pre-existing suppressions that *would* surface findings if a stricter rule selection were enabled in the future. They are recorded here so future widenings (Phase 4 brainstorm or Phase 5 sweeps) start from a complete map.

### Per-file-ignores already declared in pyproject.toml

These are not ruff findings — they are explicit `per-file-ignores` blocks. Each row is the file the ignore targets plus the suppressed rule(s).

- `apps/api/src/portfolio_outlook_api/research_sources.py` — `E501, I001` — ruff per-file-ignore in `apps/api/pyproject.toml:52`.
- `apps/api/tests/test_research_source_archive_endpoints.py` — `E501, I001` — ruff per-file-ignore in `apps/api/pyproject.toml:53`.
- `packages/storage/alembic/versions/0012_research_source_prompt_injection_scan.py` — `E501, I001` — ruff per-file-ignore in `packages/storage/pyproject.toml:39`.
- `packages/storage/src/ai_trading_agent_storage/__init__.py` — `I001` — ruff per-file-ignore in `packages/storage/pyproject.toml:40`.
- `packages/storage/src/ai_trading_agent_storage/repository_contracts.py` — `E501` — ruff per-file-ignore in `packages/storage/pyproject.toml:41`.
- `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` — `I001` — ruff per-file-ignore in `packages/storage/pyproject.toml:42`.

### `# noqa` suppressions in source

163 occurrences across 8 rule codes. Only **`B018`** is in the current `select`; the other codes belong to rule families not currently enabled and are pre-emptive against future widening.

#### `B018` — useless-expression (in current select; real suppression)

- `apps/api/src/portfolio_outlook_api/action_draft_submission.py:571` — `_ = timedelta  # noqa: B018` — keeps `timedelta` import alive for a helper referenced in the next phase; comment-line above reads "Hint at the helper name so future readers find it" (`:570`).

#### `BLE001` — blind-except (not in current select; 59 occurrences across 26 files)

Pattern: every occurrence is an `except Exception:` (or `except Exception as exc:`) at a process boundary (provider call, async edge, sync runner) where the catch is intentional to surface the error as a structured "failed" outcome rather than crash the run. Representative file:line list:

- `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py:280` — provider boundary
- `apps/api/src/portfolio_outlook_api/morning_chain.py:151` — boundary catch
- `apps/api/src/portfolio_outlook_api/ai_explanation_sync.py:229, 286` — boundary catch, surfaced as failed
- `apps/api/src/portfolio_outlook_api/universe_scan_sync.py:254, 296` — opportunistic cache lookup / boundary catch
- `apps/api/src/portfolio_outlook_api/scheduler.py:135` — boundary catch
- `apps/api/src/portfolio_outlook_api/status_routes.py:3149, 3179` — boundary catch
- `apps/api/src/portfolio_outlook_api/daily_briefing_sync.py:251` — boundary catch
- 51 further `BLE001` lines distributed across `apps/api`, `apps/worker`, `packages/portfolio`, `packages/storage` — `grep -rn "# noqa: BLE001" apps packages` reproduces the full list deterministically.

Reason for dismissal: rule not in current `select`; suppressions are pre-emptive documentation. If a future brainstorm decides to add `BLE` to `select`, each occurrence must be re-reviewed to confirm the boundary-catch intent is still valid.

#### `N802` — function-name-should-be-lowercase (not in current select; 50 occurrences across 8 files)

Pattern: every occurrence is an IBKR `ibapi` callback method that **must** mirror IBKR's camelCase API names (e.g. `isConnected`, `reqIds`, `placeOrder`, `next_valid_id` callback wrappers). Files:

- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py` — multiple methods
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py` — multiple methods
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_manual_status_client.py` — multiple methods
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_account_snapshot_client.py` — multiple methods
- Several test-double facades under `apps/api/tests/` mirror the same callback names.

Reason for dismissal: rule not in current `select`. Even if `N` were added to `select`, IBKR API conformance would justify keeping these suppressions as documentary.

#### `ARG001` / `ARG002` — unused-function-/method-argument (not in current select; 48 occurrences across 17 files)

Pattern: every occurrence is an IBKR ibapi callback signature whose unused arguments are imposed by the IBKR API contract. The implementing wrapper still receives them per the IBKR client interface.

Reason for dismissal: rule not in current `select`; same rationale as `N802` — interface conformance.

#### `ANN001` — missing-type-annotation-for-function-argument (not in current select; 3 occurrences)

- `apps/worker/tests/test_forecasting_step_multi_asset.py:313, 356`
- `apps/worker/tests/test_orchestrator_with_decision_packages.py:358`

Pattern: a test-local stub method `append(self, record)` paired with `# type: ignore[no-untyped-def]` because the surrounding test fixture intentionally omits annotations.

Reason for dismissal: rule not in current `select`; tests-only; the comment pairing documents the intent.

#### `PLC2701` — pylint-convention (not in current select; 1 occurrence)

- `apps/api/tests/test_decision_package_sync.py:24` — `_AssemblyContext,  # noqa: PLC2701  -- testing internal helper deliberately`

Reason for dismissal: rule not in current `select`; the inline comment states the intent.

#### `N803` — function-argument-should-be-lowercase (not in current select; 1 occurrence)

- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_manual_status_client.py:72` — IBKR callback argument `accountsList` (camelCase mirrors IBKR API).

Reason for dismissal: same as `N802`.
