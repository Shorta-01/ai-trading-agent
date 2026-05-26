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

## T-051 — mypy --strict baseline (2026-05-26)

**Tool:** `mypy 2.1.0` (CI uses `mypy>=1.11.0` per dev-extras pins; results agree — both report zero errors on the configured codebase).
**Command (per package):** `mypy --strict src`
**Per-package results:**

| Package | Files checked | Errors |
|---------|---------------|--------|
| `packages/domain` | 36 | **0** |
| `packages/portfolio` | 39 | **0** |
| `packages/storage` | 8 | **0** |
| `apps/worker` | 37 | **0** |
| `apps/api` | 78 | **0** |
| **Total** | **198** | **0** |

Raw output at `/tmp/mypy-domain.log`, `/tmp/mypy-portfolio.log`, `/tmp/mypy-storage.log`, `/tmp/mypy-worker.log`, `/tmp/mypy-api.log`.

Per-package `[tool.mypy]` config: `python_version = "3.12"`, `strict = true`, `mypy_path = "src"` (worker also adds `../../packages/storage/src`). `packages/storage/sql_repositories.py:1` carries `# mypy: disable-error-code="union-attr"` (file-level pragma — pre-existing, not a per-line override).

Since `mypy --strict` produced zero errors, no `FIND-MYPY-NNN` entries are written. The dismissals below cover (a) the seven `[[tool.mypy.overrides]]` `ignore_missing_imports = true` blocks across the five `pyproject.toml` files, and (b) the 191 `# type: ignore` suppressions in source. They are recorded so future widenings or stub-availability changes start from a complete map.

### `ignore_missing_imports` overrides in pyproject.toml

Each row is the module pattern the override targets plus the reason.

- `portfolio_outlook_domain` — `ignore_missing_imports = true` — sibling package without installed stubs at the moment `packages/portfolio` is mypy'd in isolation. Override in `packages/portfolio/pyproject.toml:49-51`.
- `portfolio_outlook_domain.*` — same rationale, wildcard. Override in `packages/portfolio/pyproject.toml:52-54`.
- `statsmodels`, `statsmodels.*`, `scipy`, `scipy.*` — third-party libs without `py.typed` markers (pandas + numpy carry their own stubs and are not in the override). Override in `packages/portfolio/pyproject.toml:55-59` (comment confirms intent).
- `sqlalchemy`, `sqlalchemy.*`, `alembic`, `alembic.*` — third-party libs without `py.typed`. Override in `packages/storage/pyproject.toml:52-54`.
- `ib_insync`, `ib_insync.*` — IBKR Python client without `py.typed`. Override in `apps/worker/pyproject.toml:58-60`.
- `apscheduler`, `apscheduler.*` — APScheduler without `py.typed`. Override in `apps/worker/pyproject.toml:62-64` (and a narrower duplicate `apscheduler.*` at `apps/api/pyproject.toml:63-65` for the API's APScheduler usage).
- `numpy`, `numpy.*` — override exists in `apps/worker/pyproject.toml:66-68`. Note: `numpy` ships its own stubs, so this is broader-than-needed; documenting here, not assessing.

Reason for dismissal across all seven: third-party / inter-package boundary without installed stubs at the moment the package is mypy'd; the override prevents `import-untyped` errors without weakening the strict checks against the package's own code.

### `# type: ignore` suppressions in source

191 occurrences across 9 error codes. Reason for dismissal across all categories: each suppression is at a clearly-bounded interface point (third-party callback shapes, repository polymorphism via duck-typing, deliberate test-only stubs) and corresponds to no current mypy error. They are recorded here so future strict-mode widenings or stub additions can re-review them.

#### `no-untyped-def` (×133, across 33 files)

Pattern: predominantly IBKR `ibapi` callback methods (CamelCase signatures imposed by IBKR's API) and test-local stubs paired with `# noqa: ANN001` (already inventoried under T-050). Files include `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py`, `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py`, `apps/api/src/portfolio_outlook_api/ibkr_ibapi_manual_status_client.py`, `apps/api/src/portfolio_outlook_api/ibkr_ibapi_account_snapshot_client.py`, plus 29 test files. Full file:line list reproducible deterministically via `grep -rn "# type: ignore\[no-untyped-def\]" apps packages --include="*.py"`.

#### `arg-type` (×48)

Pattern: `**kwargs` splats into pydantic constructors and `BudgetRepository` polymorphism. Representative file:line:

- `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py:140` — `GbmPredictor(**gbm_kwargs)` — kwargs dict typing
- `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py:150` — `MomentumPredictor(**momentum_kwargs)` — kwargs dict typing
- `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py:157` — `MeanReversionPredictor(**mean_rev_kwargs)` — kwargs dict typing
- `apps/api/src/portfolio_outlook_api/ai_ts_provider.py:252` — `budget_repo=budget_repo` — repo-polymorphism
- `apps/api/src/portfolio_outlook_api/ai_explanation_provider.py:185` — `budget_repo=budget_repo` — repo-polymorphism

43 further occurrences across `apps/api` and `apps/worker`; reproducible via grep.

#### Other codes (×10)

- `attr-defined` (×3) — accessing pydantic computed-property-like attributes that mypy can't resolve through validators.
- `misc` (×2):
  - `apps/api/tests/test_universe_registry.py:57` — `entry.symbol = "Y"` on a frozen model in test context.
  - `packages/portfolio/tests/test_predictor_protocol.py:369` — `score.brier_score = 0.5` on a frozen `BacktestWindowScore` in test context.
- `union-attr` (×1) — `apps/api/tests/test_release_readiness.py:257` — list comprehension over a payload subset.
- `no-untyped-def, override` (×1) — `apps/worker/tests/test_orchestrator_with_decision_packages.py:358` — test-local stub method.
- `no-untyped-call` (×1) — `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py:542` — `IB()` constructor from `ib_insync` (no `py.typed`); paired with the override above.
- `index` (×1) — `apps/api/tests/test_morning_chain.py:260` — dict-subscript on a serialised payload.
- `assignment` (×1) — `apps/api/src/portfolio_outlook_api/ibkr_connection_read_model.py:155` — `mode = latest_success.account_mode_detected` (narrow-after-isinstance pattern that mypy can't follow through the audit row).

#### File-level pragma (×1)

- `packages/storage/sql_repositories.py:1` — `# mypy: disable-error-code="union-attr"` (module-level). Pre-existing; documentary record only.

## T-052 — vulture baseline (2026-05-26)

**Tool:** `vulture 2.16`
**Command:** `vulture --min-confidence 80 apps/api/src apps/worker/src packages/domain/src packages/portfolio/src packages/storage/src`
**Findings:** 16 total at ≥80% confidence.
**Triage:** 1 → `FIND-VULTURE-001` in `docs/code-health/01-dead-code.md`. 15 → dismissed below.
**Raw output:** `/tmp/vulture-baseline.log`. Config: repo-root `pyproject.toml:[tool.vulture]` `min_confidence = 80`, `paths` scoped to the five `*/src` directories, tests + migrations excluded.

### Dismissed: IBKR `ibapi` callback signatures (×10)

Pattern: every occurrence is an `ibapi`-imposed callback signature. The argument is required by the IBKR client interface; the callback either ignores it or stores it in a fixture. Already inventoried under T-050 noqa codes `N802` / `ARG002` (callback name conventions) and T-051 mypy code `no-untyped-def`.

- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_manual_status_client.py:68` — `reqId` (IBKR `error()` callback)
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_manual_status_client.py:70` — `errorString` (IBKR `error()` callback)
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_manual_status_client.py:71` — `args` (IBKR `error()` callback)
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py:98` — `num_ids` (IBKR `reqIds` callback)
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py:53` — `reqId` (IBKR `reqAccountSummary` callback)
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py:53` — `tags` (IBKR `reqAccountSummary` callback)
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py:56` — `reqId` (IBKR `cancelAccountSummary` callback)
- `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py:64` — `reqId` (IBKR `reqExecutions` callback)
- `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py:63` — `args` (worker-side IBKR adapter signature)
- `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py:63` — `kwargs` (same)

Reason for dismissal: **framework-callback**. The IBKR API contract requires these signatures; removing the arguments would break the API.

### Dismissed: provider Protocol signatures (×3)

Pattern: `**kwargs` retained in concrete-provider methods to keep the call site duck-typed against future Protocol additions. Two are AI explanation / time-series providers; one is the EODHD HTTP-client Protocol.

- `apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py:85` — `kwargs` (Anthropic explanation-provider stub)
- `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py:101` — `kwargs` (Anthropic time-series provider stub)
- `apps/worker/src/portfolio_outlook_worker/providers/eodhd.py:59` — `timeout` (HTTP-client Protocol method, httpx-compatible signature; the doc-comment confirms intent: "the protocol the EODHD client expects from a typed HTTP client without importing `httpx` at module load time")

Reason for dismissal: **framework-callback / interface-conformance**. The signatures exist to satisfy a Protocol contract (`docs/reality/components/domain-runtime-and-integration.md` notes the broader `Protocol` pattern in `market_data_foundation.py`); removing them would break the interface.

### Dismissed: backward-compat parameter retained for signature stability (×2)

Pattern: `mean_value` parameter retained on `_stdev(values, mean_value)` after a V1.1 §22.1 numpy-backed refactor. The comment on the momentum version explicitly states the intent.

- `packages/portfolio/src/portfolio_outlook_portfolio/mean_reversion_predictor.py:113` — `mean_value` (paired with `_mean()` above at `:108-112`)
- `packages/portfolio/src/portfolio_outlook_portfolio/momentum_predictor.py:126` — `mean_value` — module comment at `:127-128` reads: `"V1.1 §22.1 refactor: numpy-backed sample SD (mean_value kept for backward signature compatibility; recomputed internally)."`

Reason for dismissal: **deliberate backward-compatible signature**. The parameter is documented at the source; removing it would break callers that pass it.

## T-053 — bandit baseline (2026-05-26)

**Tool:** `bandit 1.9.4`
**Command:** `bandit -r apps packages -x "*/tests/*,*/test_*.py,*/alembic/*" -f json -o /tmp/bandit-low-and-up.json`
**Findings:** 40 total (39 LOW + 1 MEDIUM).
**Triage:** 1 → `FIND-BANDIT-001` in `docs/code-health/02-anti-patterns.md` (covers the 20 B101 occurrences as a single umbrella pattern). 20 → dismissed below.
**Raw output:** `/tmp/bandit-low-and-up.json` (JSON), `/tmp/bandit-baseline.txt` (text). Run metrics: 20 B101 / 5 B105 / 10 B106 / 3 B110 / 1 B112 / 1 B310.

### Dismissed: B105 hardcoded_password_string — enum value false positives (×5)

Pattern: bandit's heuristic matches the substrings `"secret"` / `"password"` in module-level string constants. Every site is an `enum.StrEnum` member declaration — the **enum value is the persisted string** for an audit row, not a credential.

- `packages/domain/src/portfolio_outlook_domain/enums.py:956` — `EXTERNAL_SECRET_MANAGER_FUTURE = "external_secret_manager_future"` (`SecretStorageKind` enum)
- `packages/domain/src/portfolio_outlook_domain/enums.py:1109` — `SECRET_STORAGE_UNSAFE = "secret_storage_unsafe"` (`StorageBlockReason` enum)
- `packages/domain/src/portfolio_outlook_domain/enums.py:1150` — `SECRET_REFERENCE_ONLY = "secret_reference_only"` (`StorageSensitivity` enum)
- `packages/domain/src/portfolio_outlook_domain/enums.py:1151` — `PROHIBITED_SECRET_VALUE = "prohibited_secret_value"` (`StorageSensitivity` enum)
- `packages/domain/src/portfolio_outlook_domain/enums.py:1162` — `SECRET_REFERENCE_METADATA = "secret_reference_metadata"` (`PersistedEntityKind` enum)

Reason for dismissal: **false positive**. AGENTS.md "no hardcoded secrets" forbids actual credentials in source; these are typed enum vocabularies that classify *the absence* of a secret value (e.g. `PROHIBITED_SECRET_VALUE` flags rows that must never carry a secret).

### Dismissed: B106 hardcoded_password_funcarg — kwarg name false positives (×10)

Pattern: bandit's heuristic matches kwargs whose name pattern resembles `*password*` / `*pass*` / `*secret*`. Every site here is either a `pass_name=` (reconciliation pass label) or a `secret_reference_id=` (typed reference to a `SecretReference` row, not the secret itself).

- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_a_orphaned_executions.py:255` — `pass_name="orphaned_execution"`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_a_orphaned_executions.py:310` — `pass_name="orphaned_execution"`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_a_orphaned_executions.py:347` — `pass_name="orphaned_execution"`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_b_stale_in_flight.py:260` — `pass_name="stale_in_flight"`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_b_stale_in_flight.py:334` — `pass_name="stale_in_flight"`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_b_stale_in_flight.py:368` — `pass_name="stale_in_flight"`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_b_stale_in_flight.py:403` — `pass_name="stale_in_flight"`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_c_timeout_recovery.py:145` — `pass_name="timeout_recovery"`
- `packages/domain/src/portfolio_outlook_domain/settings.py:705` — `api_key_secret_reference_id="secret_openai_api_key"` (typed FK to a `SecretReference` row, not a key)
- `packages/domain/src/portfolio_outlook_domain/settings.py:710` — `secret_reference_id="secret_openai_api_key"` (same row's PK declaration)

Reason for dismissal: **false positive**. `pass_name` is the reconciliation pass label (locked enum: `"orphaned_execution"`, `"stale_in_flight"`, `"timeout_recovery"` — see `_LOCKED_RECONCILIATION_PASS_NAMES` in `repository_contracts.py`). `secret_reference_id` is a typed `SafeIdentifier` pointing at a `SecretReference` row whose body still has `status=NOT_CONFIGURED` and `configured=False` — there is no actual secret stored in either location.

### Dismissed: B110 try_except_pass — documented boundary catches (×3)

Pattern: deliberate boundary swallow already inventoried under T-050 noqa `BLE001`.

- `apps/api/src/portfolio_outlook_api/ibkr_tws_readonly_adapter.py:118` — disconnect-error swallow in the `finally` clause; `docs/reality/components/api-ibkr-connection-and-status.md` notes: "Keep status checks resilient; never escalate disconnect errors."
- `apps/api/src/portfolio_outlook_api/status_routes.py:3149` — boundary catch (already in T-050 `BLE001` list).
- `apps/api/src/portfolio_outlook_api/status_routes.py:3179` — boundary catch (already in T-050 `BLE001` list).

Reason for dismissal: documented intent at the source; the catch boundary keeps a status surface resilient. Not a security defect.

### Dismissed: B112 try_except_continue — documented per-fold catch (×1)

- `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py:162` — `except Exception:` paired with `continue` inside the walk-forward fold loop. Already inventoried in T-050 `BLE001` list and in `docs/reality/components/portfolio-predictors.md`: "Per-fold exceptions caught silently with `except Exception` boundary; blocked predictions skipped, not failed."

Reason for dismissal: documented per-fold boundary; the loop continues to the next fold rather than crashing the whole backtest.

### Dismissed: B310 audit-url-open — config-derived URL (×1)

- `apps/api/src/portfolio_outlook_api/eodhd_client.py:148` — `urllib.request.urlopen(request, timeout=timeout_seconds)`. Bandit warns "Audit url open for permitted schemes."

Reason for dismissal: the URL is constructed inside the EODHD client from configuration values (`base_url`, `endpoint`, query params from typed inputs), not from user-controllable input. No `file://` / custom-scheme attack surface — bandit cannot statically prove this, hence the audit-warning.
