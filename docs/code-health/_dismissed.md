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

## T-054 — pip-audit baseline (2026-05-26)

**Tool:** `pip-audit 2.10.0`
**Command:** `pip-audit --format=json -o /tmp/pip-audit-baseline.json` (after `pip install -e ./packages/{domain,storage,portfolio} -e ./apps/{worker,api}` into a Python 3.12 venv)
**Findings:** 5 known vulnerabilities in 2 packages (1 fastapi MAL + 4 pip CVEs).
**Triage:** 1 → `FIND-PIPAUDIT-001` in `docs/code-health/04-bugs.md` (`fastapi==0.136.3` malicious release MAL-2026-4750). 4 → dismissed below (all in the build-time `pip` tool, not in the deployed application).
**Raw outputs:** `/tmp/pip-audit-baseline.json` (JSON), `/tmp/pip-audit-baseline.txt` (text).

Five `Skip Reason` entries on the project's own packages (`ai-trading-agent-storage`, `portfolio-outlook-api`, `portfolio-outlook-domain`, `portfolio-outlook-portfolio`, `portfolio-outlook-worker`) are not vulnerabilities — they are pip-audit's "Dependency not found on PyPI and could not be audited" messages for local editable installs. Skipped as not-applicable.

### Dismissed: `pip` CVEs (×4) — build-time tool, not deployed

Pattern: the four `pip` CVEs in `pip==24.0` are all vulnerabilities in the **package installer tool itself**, not in any application dependency. `pip` is not declared in any of the project's `pyproject.toml` files (it is whatever the venv / OS provides). CI uses GitHub's `actions/setup-python@v5` which provides its own pip; production deployments don't bundle pip. The application code never imports or invokes pip programmatically.

- `pip==24.0` `CVE-2025-8869` (alias `GHSA-4xh5-x5gv-qwph`) — *"When extracting a tar archive pip may not check symbolic links point into the extraction directory if the tarfile module doesn't implement PEP 706."* Fixed in pip 25.3.
- `pip==24.0` `CVE-2026-1703` (alias `GHSA-6vgw-5pg2-w6jp`) — *"When pip is installing and extracting a maliciously crafted wheel archive, files may be extracted outside the installation directory."* Fixed in pip 26.0.
- `pip==24.0` `CVE-2026-3219` (alias `GHSA-58qw-9mgm-455v`) — *"pip handles concatenated tar and ZIP files as ZIP files regardless of filename."* Fixed in pip 26.1.
- `pip==24.0` `CVE-2026-6357` (alias `GHSA-jp4c-xjxw-mgf9`) — *"pip prior to version 26.1 would run self-update check functionality after installing wheel files which required importing well-known Python modules names."* Fixed in pip 26.1.

Reason for dismissal: **build-time tool, not deployed.** The project does not declare `pip` as a dependency. Mitigation is a developer-/CI-side `pip install --upgrade pip` outside the scope of any source change. None of the four vulnerabilities can be exploited against the running application — they only apply when pip itself is processing a malicious archive at install time.

Phase 4 / Phase 5 consideration: the CI workflow could pin a known-good pip via `actions/setup-python` cache or `pip install --upgrade pip` step. Out of scope for T-054 (`pyproject.toml` modification is explicitly out of scope per the task spec).

### Not applicable: local editable installs (×5)

pip-audit emits "Dependency not found on PyPI and could not be audited" for each of the five project packages (`ai-trading-agent-storage 0.1.0`, `portfolio-outlook-api 0.1.0`, `portfolio-outlook-domain 0.1.0`, `portfolio-outlook-portfolio 0.1.0`, `portfolio-outlook-worker 0.1.0`). These are local-only packages installed via `pip install -e .` — they have no PyPI release and no advisory database coverage. Not vulnerabilities; recorded here so the baseline accounting is complete.

## T-055 — radon baseline (2026-05-26)

**Tool:** `radon 6.0.1`
**Commands:** `radon cc -s -a apps packages` and `radon mi -s apps packages`
**Findings (CC):** 5729 blocks analysed → 4976 rank A (default-acceptable), 541 rank B (watch — dismissed below), 182 rank C, 20 rank D, 6 rank E, 4 rank F.
**Findings (MI):** 490 modules analysed → 473 rank A, 8 rank B, 9 rank C.
**Triage:** 4 → `FIND-RADON-001..004` in `docs/code-health/02-anti-patterns.md` (10 high CC + 202 medium CC + 9 high MI + 8 medium MI). 541 CC rank-B → dismissed below as "watch".
**Raw outputs:** `/tmp/radon-cc-baseline.txt` (6217 lines), `/tmp/radon-mi-baseline.txt` (498 lines). Average CC across the analysed 5729 blocks: **A (3.07)**.

### Dismissed: CC rank B (×541, watch list)

Pattern: every site is a function or method at radon's rank B (`CC 6–10`). The locked T-055 threshold dismisses rank B by default but records the per-file count below so a future Phase 4 brainstorm can decide whether to tighten the threshold to B+.

#### Files with the highest rank-B counts

| File | Rank-B count |
|---|---:|
| `apps/api/src/portfolio_outlook_api/status_routes.py` | 20 |
| `packages/storage/tests/test_sql_repositories.py` | 14 |
| `packages/domain/src/portfolio_outlook_domain/settings.py` | 13 |
| `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` | 12 |
| `apps/api/tests/test_ibkr_status_endpoint.py` | 10 |
| `packages/domain/src/portfolio_outlook_domain/storage.py` | 9 |
| `apps/api/tests/test_ibkr_sync_endpoints.py` | 9 |
| `packages/domain/src/portfolio_outlook_domain/suggestion_engine.py` | 8 |
| `packages/domain/src/portfolio_outlook_domain/runtime.py` | 8 |
| `packages/domain/src/portfolio_outlook_domain/broker_reconciliation.py` | 8 |
| `apps/api/tests/test_portfolio_valuation_readiness_endpoint.py` | 8 |
| `apps/api/tests/test_research_source_archive_endpoints.py` | 7 |
| `apps/api/tests/test_market_data_readiness_endpoint.py` | 6 |
| `apps/api/src/portfolio_outlook_api/eodhd_client.py` | 6 |
| `packages/domain/src/portfolio_outlook_domain/data_sources.py` | 5 |
| `apps/api/tests/test_watchlist_endpoints.py` | 5 |
| `apps/api/tests/test_decision_package_sync.py` | 5 |
| `apps/api/src/portfolio_outlook_api/ibkr_ibapi_sync_client.py` | 5 |
| _(other files, ≤4 rank-B sites each)_ | 393 (total) |

Sum: 152 in the top 18 files + 393 in the long tail = 541.

Reason for dismissal: **threshold-locked**. The T-055 task spec explicitly dismisses rank B by default ("Rank `B` (CC 6–10) is dismissed by default but listed as 'watch' in `_dismissed.md`"). The per-file counts above are recorded so the same five "hottest" files (`status_routes.py`, `sql_repositories.py`, `settings.py`, both `test_sql_repositories.py` and `test_ibkr_status_endpoint.py`) line up exactly with the high-severity MI list in `FIND-RADON-003` — a future threshold tightening would compound those findings rather than discover new ones.

### Not applicable: MI rank A (×473)

473 modules score MI ≥ 20 (rank A). No further triage needed; recorded here so the baseline accounting is complete.

### Not applicable: CC rank A (×4976)

4976 functions/methods at radon's rank A (`CC 1–5`). No further triage needed; recorded here so the baseline accounting is complete.

## T-056 — tsc --noEmit baseline (2026-05-26)

**Tool:** `tsc` from `typescript` (versioned in `apps/web/package.json`).
**Commands:** `cd apps/web && npm install --legacy-peer-deps` (clean install), then `npx tsc --noEmit > /tmp/tsc-baseline.log 2>&1` (exit code 1).
**Findings:** 1 distinct error line.
**Triage:** 1 → `FIND-TSC-001` in `docs/code-health/02-anti-patterns.md` (test-fixture drift in `ActionDraftGrid.test.tsx`). 0 dismissals.
**Raw output:** `/tmp/tsc-baseline.log` (1 line).

No false positives, no boundary-pattern catches, no framework-imposed signatures to dismiss. The baseline accounting is `1 FIND + 0 dismissed = 1 distinct error line`.

The current `apps/web` CI step runs `next build` rather than an explicit `tsc --noEmit`, which is why the test-file drift could land. A Phase 4 CI brainstorm could decide to add `npm run typecheck` (or wire `tsc --noEmit` into the existing `npm run build` chain) to surface the same class of drift at PR time.

## T-057 — knip + ts-prune baseline (2026-05-26)

**Tools:** `knip 5.x` + `ts-prune 0.10.x` (both installed via `npm install --no-save --legacy-peer-deps knip ts-prune`).
**Commands:** `npx knip --reporter json > /tmp/knip-baseline.json` (exit 1), `npx knip > /tmp/knip-baseline.txt` (exit 1), `npx ts-prune > /tmp/ts-prune-baseline.txt` (exit 0).
**Findings:** knip 41 reportables (3 files + 2 devDeps + 10 exports + 25 types + 1 duplicate); ts-prune 93 entries.
**Triage:** 7 FINDs in `docs/code-health/01-dead-code.md` covering all 41 knip reportables (the 12 ts-prune real findings overlap with the dual-source FINDs); 3 dismissal categories below covering the remaining 81 ts-prune entries.
**Raw outputs:** `/tmp/knip-baseline.json`, `/tmp/knip-baseline.txt`, `/tmp/ts-prune-baseline.txt`.

ts-prune accounting:

- 93 total entries reported.
- 12 are real findings (file-level deletions + auditFormatting helpers + 2 apiClient exports + ApiUnavailableNotice + uiText.ts + AssetIdentityPicker.tsx) — all covered by the FIND-UNUSED-001..003 entries.
- 81 are over-reports broken down into the three dismissal categories below.

### Dismissed: Next.js framework convention defaults (×18)

Pattern: Next.js App Router uses `page.tsx default export`, `layout.tsx default export + metadata named export` as **framework-driven entry points**. They are not imported by any user code; the Next.js compiler discovers them by file convention. ts-prune cannot model the Next.js file-to-route mapping, so it reports each `default` (and the layout's `metadata`) as "unused".

Specific entries dismissed (all `apps/web/`):

- `app/layout.tsx:27 - default` + `app/layout.tsx:10 - metadata` (the root layout — see T-008 `web-pages.md` §2).
- `app/page.tsx:34 - default` (the root Dashboard page — T-008 §3.1).
- `app/audit/page.tsx:7 - default` (T-008 §3.10).
- `app/historiek/page.tsx:3 - default` (T-008 §3.16).
- `app/ibkr-acties/page.tsx:38 - default` (T-008 §3.5).
- `app/instellingen/page.tsx:23 - default` (T-008 §3.7).
- `app/onderzoek/page.tsx:3 - default` (T-008 §3.15).
- `app/portefeuille/page.tsx:59 - default` (T-008 §3.2).
- `app/research-sources/page.tsx:25 - default` (T-008 §3.4).
- `app/suggesties/page.tsx:10 - default` (T-008 §3.11).
- `app/systeemmeldingen/page.tsx:37 - default` (T-008 §3.8).
- `app/volglijst/page.tsx:34 - default` (T-008 §3.6).
- `app/admin/reconciliation/page.tsx:44 - default` (T-008 §3.3).
- `app/decision-package/[id]/page.tsx:29 - default` (T-008 §3.9).
- `app/audit/freshness-audits/[freshnessAuditId]/page.tsx:10 - default` (T-008 §3.13).
- `app/audit/provider-sources/[providerSourceId]/page.tsx:8 - default` (T-008 §3.14).
- `app/audit/request-logs/[requestLogId]/page.tsx:10 - default` (T-008 §3.12).

Reason for dismissal: **framework convention** — Next.js discovers these by `app/**/page.tsx` + `layout.tsx` file naming, not by import graph. knip is configured to understand Next.js conventions (`apps/web/knip.config` is implicit / default Next.js plugin) so it correctly does NOT flag these.

### Dismissed: top-level config-file defaults (×3)

Pattern: tool config files use `export default { ... }` and are loaded by their respective CLI tools (Next.js, Playwright, Vitest) by filename convention. ts-prune cannot model these.

- `next.config.ts:7 - default` — Next.js config.
- `playwright.config.ts:11 - default` — Playwright config.
- `vitest.config.ts:6 - default` — Vitest config.

Reason for dismissal: **framework convention** — tool CLIs load these by filename, not by import.

### Dismissed: ts-prune `(used in module)` over-reporting (×60)

Pattern: ts-prune marks every `export` declaration that has at least one internal reference within the same module file but no external import as `(used in module)`. In `apps/web/lib/apiClient.ts`, ~60 type aliases and constants follow this pattern — they're chained internally (e.g. a `WatchlistConfirmResponse` type referenced by another `*ListResponse` envelope type which is itself exported) but the outer envelope's external use does not propagate through the chain in ts-prune's analysis.

Two of the entries that look similar but are **genuinely unused** (NOT marked `(used in module)`) are surfaced in `FIND-UNUSED-003` (`MarketDataLatestSnapshotResponse:746`, `updateWatchlistItem:1807`). The remaining 60 `(used in module)` entries split roughly:

- **~24 are also flagged by knip as "Unused exported types"** — these are the genuine-but-internal-only types, covered by `FIND-KNIP-004`.
- **~36 are correctly internally-referenced** — they're consumed by other exports in the same file that *do* have external consumers; ts-prune just can't trace the chain through TypeScript's type-system. Examples (line refs are in `apps/web/lib/apiClient.ts`):
  - `FetchState:1`, `ApiResult:5` — base discriminated-union types used everywhere via `Result<T>`.
  - `SettingsSummary:34`, `AiUsageSummary:56`, `StorageStatusSummary:57`, `IntegrationsSummary:59` — composed into nested response shapes.
  - `LatestForecastsResponse:391`, `LatestSuggestionsResponse:428`, `LatestDecisionPackagesResponse:501`, `LatestActionDraftsResponse:1316` — wrappers for "latest" endpoints whose responses are consumed via the `Result<T>` discriminated union.
  - 30+ other inner-chain response types.

Reason for dismissal across all 60: **ts-prune limitation** — the tool over-reports any export whose only references are inside the same file. knip's deeper analysis disambiguates the genuinely-unused (FIND-KNIP-004) from the internally-chained. No action: either accept the chain or let `FIND-KNIP-004` Phase 4 pruning shrink the set.

The current `apps/web` CI step does not run `knip` or `ts-prune`. A Phase 4 CI brainstorm could decide to add `npm run dead-code` (running both with the dismissals above wired into knip's config) so the same class of drift surfaces at PR time. Per the T-057 spec, "Adding either tool to `package.json` permanently — that decision goes through Phase 4 brainstorming" — explicitly out of scope here.

## T-058 — npm audit baseline (2026-05-26)

**Tool:** `npm audit 10.x` (built into npm 10.9.7).
**Commands:** `npm audit --omit=dev --json > /tmp/npm-audit-prod.json` + `npm audit --omit=dev > /tmp/npm-audit-prod.txt` + `npm audit --json > /tmp/npm-audit-full.json` + `npm audit > /tmp/npm-audit-full.txt` (all exit 1).
**Findings:** 9 vulnerable packages, 26 distinct GHSAs total (22 next + 1 postcss + 1 @eslint/plugin-kit + 2 esbuild/vite). Prod-only run: 2 packages (1 high, 1 moderate). Full run: 9 packages (1 high, 6 moderate, 2 low).
**Triage:** 4 FINDs in `docs/code-health/04-bugs.md` cover every reported package and every distinct GHSA. **No dismissals** — every package is in a FIND.
**Raw outputs:** `/tmp/npm-audit-prod.json` (434 lines), `/tmp/npm-audit-prod.txt` (42 lines), `/tmp/npm-audit-full.json` (621 lines), `/tmp/npm-audit-full.txt` (73 lines).

### Accounting (every reported package mapped to a FIND)

| Package | Prod/Dev | npm-audit severity | FIND | FIND severity |
|---|---|---|---|---|
| `next` | prod | high | FIND-NPMAUDIT-001 | HIGH (prod follows npm-audit) |
| `postcss` | prod (transitive via `next`) | moderate | FIND-NPMAUDIT-002 | MEDIUM (prod follows npm-audit) |
| `@eslint/plugin-kit` | dev | low | FIND-NPMAUDIT-003 | LOW (dev: low → low) |
| `eslint` | dev (transitive via `@eslint/plugin-kit`) | low | FIND-NPMAUDIT-003 | LOW (covered by same FIND) |
| `esbuild` | dev | moderate | FIND-NPMAUDIT-004 | LOW (dev: moderate → low, downgraded) |
| `vite` | dev (own advisory + transitive via `esbuild`) | moderate | FIND-NPMAUDIT-004 | LOW (covered) |
| `@vitest/mocker` | dev (transitive via `vite`) | moderate | FIND-NPMAUDIT-004 | LOW (covered) |
| `vite-node` | dev (transitive via `vite`) | moderate | FIND-NPMAUDIT-004 | LOW (covered) |
| `vitest` | dev (transitive via all three above) | moderate | FIND-NPMAUDIT-004 | LOW (covered) |

Sum: **9 packages → 4 FINDs, 0 dismissals.** Per task spec ("Every distinct CVE becomes a FIND-XXX or `_dismissed.md` row") satisfied — every npm-audit-reported advisory is covered by a FIND (umbrella pattern matches T-054's `FIND-PIPAUDIT-001` and T-055's `FIND-RADON-*` precedents).

### Note: dev-only CVE downgrade

Per the locked T-058 severity mapping ("dev-only CVEs downgraded one rank: critical→high, high→medium, medium→low, low→low"), the 5 dev-only `moderate` packages in the vitest + esbuild chain are surfaced as **LOW** in FIND-NPMAUDIT-004. The two dev-only `low` packages stay at LOW per the floor rule. This matches the spirit of "dev tooling never reaches production" — both advisories require an active HTTP dev server (esbuild's, vite's) which only runs during `npm run dev` or `vitest watch`, never during `next build`/`next start` or one-shot `npm test`.

### CI cross-reference

`code-health.yml:197-199` already runs `npm audit --omit=dev || true` report-only on every PR. The `|| true` swallows findings, so this baseline did not previously surface in PR feedback. A Phase 4 CI brainstorm could remove `|| true` for HIGH-severity prod advisories (FIND-NPMAUDIT-001's class). Per the T-058 spec, "No `package.json` / `package-lock.json` modification" — even the obvious `next@15.5.18` bump is explicitly out of scope here.
