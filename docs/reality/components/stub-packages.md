# Reality — stub packages (`packages/{ai, analytics, audit, data_providers, risk, tax}`)

**Scope.** Six README-only directories under `packages/` that contain zero source code and zero `pyproject.toml`. Each holds a single 3-line `README.md` with identical Dutch placeholder text. They were created as **named namespace slots** for future work; the concept each slot represents is in fact implemented elsewhere in the tree, scattered across `apps/api`, `apps/worker`, `packages/domain`, `packages/portfolio`, and `packages/storage`.

This doc records each slot's reality:

1. README content (verbatim).
2. Where the concept IS implemented today (with cross-references to the per-cluster reality docs from T-001 … T-009).
3. The closing summary table mapping each stub to its equivalent code locations.

Cross-doc anchors:

- `docs/reality/components/domain-*.md` (T-001).
- `docs/reality/components/portfolio-*.md` (T-002).
- `docs/reality/components/storage-package-and-migrations.md` (T-003).
- `docs/reality/components/api-*.md` (T-004, T-005, T-006).
- `docs/reality/components/worker-*.md` (T-007).
- `docs/reality/components/web-*.md` (T-008, T-009).

## In-scope directories

| Directory | Contents |
|---|---|
| `packages/ai/` | `README.md` only |
| `packages/analytics/` | `README.md` only |
| `packages/audit/` | `README.md` only |
| `packages/data_providers/` | `README.md` only |
| `packages/risk/` | `README.md` only |
| `packages/tax/` | `README.md` only |

All six READMEs carry **identical** content (verified via `cat`):

```
# <name>

Placeholderpakket voor toekomstige module-uitwerking. In deze fase is alleen de technische skeleton aanwezig.
```

No `pyproject.toml`, no `src/`, no tests, no `__init__.py`. None of these directories is installed by any CI workflow (`.github/workflows/ci.yml` only references `packages/domain`, `packages/storage`, `packages/portfolio` — see T-009 `build-ci-and-scripts.md` §4).

## 1. `packages/ai/`

- **README path:** `packages/ai/README.md`
- **README content (verbatim):** `"# ai\n\nPlaceholderpakket voor toekomstige module-uitwerking. In deze fase is alleen de technische skeleton aanwezig."`
- **Concept:** AI-as-research/explanation layer (Case C in the doctrine framework — see `docs/ai-policy.md` and T-006 `api-infrastructure-and-ai.md` §11).

### Where the AI concept IS implemented today

Across **`apps/api`** (per T-006 `api-infrastructure-and-ai.md` §11):

- `apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py` (280 lines) — the Anthropic Claude SDK provider with locked Dutch system prompt + ephemeral cache + monthly EUR budget cap.
- `apps/api/src/portfolio_outlook_api/ai_explanation_provider.py` (210 lines) — `ExplanationProviderProtocol` + `StubExplanationProvider` + factory dispatcher with five gates (`ai_explanation_disabled` / `stub` / `real_client_not_enabled` / `claude_ai_api_key_missing` / `claude_ai_budget_repo_missing`).
- `apps/api/src/portfolio_outlook_api/ai_explanation_sync.py` (354 lines) — orchestration: SHA-256 hash chain over canonical Decision Package input, evidence-ledger writer, hallucinated-number guard via `validate_explanation_output`.
- `apps/api/src/portfolio_outlook_api/claude_ai_budget.py` (186 lines) — monthly EUR cap, UTC-anchored calendar reset, `assert_budget_available` pre-call + `persist_call_cost` post-call. Default cap `Decimal("50")` per `apps/api/.../config.py:182`.
- `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py` (~280 lines) — **Case B** LLM-as-forecaster (doctrine-locked to "remove from ensemble" per T-005 `api-forecasting-and-market-data.md`).
- `apps/api/src/portfolio_outlook_api/ai_ts_provider.py` (~210 lines) — **Case A** stub: classical-stats labelled "AI" (doctrine-locked to "rename" per T-005).

In **`packages/portfolio/`** (per T-002):

- `packages/portfolio/src/portfolio_outlook_portfolio/ai_ts_predictor.py` — the typed predictor interface.
- `packages/portfolio/src/portfolio_outlook_portfolio/ai_explanation_guards.py` — hallucinated-number validation helpers.

In **`packages/storage/`** (per T-003):

- Migration `0043_claude_ai_budget_usage.py` — the `claude_ai_budget_usage` table holding `ClaudeAiBudgetUsageRecord` rows.
- `SqlAlchemyClaudeAiBudgetUsageRepository` inside `sql_repositories.py`.

In **`apps/web/`** (per T-008 + T-009):

- `apps/web/components/AccountModeBadge.tsx` consumer-side display (none currently surface AI explanations directly; they are returned by `apiClient.runDecisionPackageExplanation` and `apiClient.getDecisionPackageExplanation`, per T-009 `web-api-client-and-text.md` §2).

Locked policy intent: `docs/ai-policy.md` (95 lines).

**Verdict on the `packages/ai/` stub:** the namespace was reserved before the AI surface settled into its current `apps/api` location. The provider + sync + budget triad lives in the API tier because it shares the `Settings` class + the storage connection provider; relocating it to `packages/ai/` would have required either duplicating those dependencies or introducing a circular reference. The stub remains valuable as a **future home** if the AI surface ever needs to be reused by the worker (e.g. a worker-side AI explanation for daily briefings).

## 2. `packages/analytics/`

- **README path:** `packages/analytics/README.md`
- **README content (verbatim):** placeholder Dutch text (same as above).
- **Concept:** measurement + calibration + coverage + performance metrics.

### Where the analytics concept IS implemented today

Across **`packages/portfolio/`** (per T-002 `portfolio-predictors.md`):

- `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py` — `walk_forward_backtest`, `aggregate_window_score`, per-fold boundary catch (T-053 dismissed under B112). Also flagged in T-055 `FIND-RADON-002` (CC C in `walk_forward_backtest:113` + `aggregate_window_score:196`).
- `packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py` — `compute_inverse_brier_weights:195` (CC 16, FIND-RADON-002) + `_apply_clip_with_water_filling:272` (CC 40, T-055 `FIND-RADON-001` high-severity).
- `packages/portfolio/src/portfolio_outlook_portfolio/performance.py` — portfolio performance metrics (T-002 `portfolio-money-and-accounting.md`).
- `packages/portfolio/src/portfolio_outlook_portfolio/prediction_diary_eval.py` — prediction-diary evaluation logic.

In **`apps/worker/`** (per T-007 `worker-forecasting-and-decision-package.md` §3):

- `apps/worker/src/portfolio_outlook_worker/forecasting/calibration_step.py` (179 lines) — per-forecast realized-vs-band `hit_status` (4 cases: `realized_above_p90`, `realized_below_p10`, `realized_within_p10_p90`, `realized_outside_band`). Writes `CalibrationDiaryEntry` rows.

In **`apps/api/`** (per T-005):

- `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py` — backtest orchestration + 4 high-CC sub-functions (T-055 FIND-RADON-002 CC 11–24).

In **`apps/web/`** (per T-008 + T-009):

- `apps/web/components/CalibrationCoverageBadge.tsx` (138 lines, T-008 `web-components-status-and-shared.md` §3) — three locked Dutch labels: `"Kalibratie: goed"` / `"Kalibratie: matig"` / `"Kalibratie: te weinig data"` against hit-rate floors 0.60 / 0.40 with `MIN_SAMPLE_SIZE=10`.
- `apiClient.getCalibrationCoverage(windowDays=90)` (T-009 `web-api-client-and-text.md` §2).

**Verdict on `packages/analytics/`:** calibration + backtesting + performance metrics live in **`packages/portfolio/`** today because they all consume the same predictor protocol (`predictor_protocol.py`) and frozen dataclasses (`_predictor_math.py`). The named-stub split was never operationalised; the analytics namespace is reserved for a future extraction if metrics ever need their own package boundary (e.g. for a `packages/portfolio/`-independent reporting service).

## 3. `packages/audit/`

- **README path:** `packages/audit/README.md`
- **README content (verbatim):** placeholder Dutch text (same as above).
- **Concept:** persisted audit trail — hash-chained event ledgers, system events, request audit.

### Where the audit concept IS implemented today

In **`packages/storage/`** (per T-003 `storage-package-and-migrations.md`):

- 13 `SqlAlchemy*AuditRepository` classes in `packages/storage/src/ai_trading_agent_storage/sql_repositories.py`:
  - `SqlAlchemySystemEventRepository`
  - `SqlAlchemyRequestAuditRepository`
  - `SqlAlchemyAssetActionDraftEventRepository`
  - `SqlAlchemyIbkrConnectionAuditRepository`
  - `SqlAlchemyScheduledRunAuditRepository`
  - `SqlAlchemyColdStartSeedAuditRepository`
  - `SqlAlchemyWatchlistConfirmationAuditRepository`
  - `SqlAlchemyProviderCallAuditRepository`
  - `SqlAlchemyActionDraftAuditRepository`
  - `SqlAlchemyIbkrSubmissionAuditRepository`
  - `SqlAlchemyReconciliationAuditRepository`
  - `SqlAlchemyUnmatchedExecutionAuditRepository`
  - `SqlAlchemyReconciliationRunAuditRepository`
- Plus migration `0051_action_drafts_and_audit.py`, `0052_ibkr_submission_lifecycle_audit_and_executions.py`, `0046_scheduled_run_audit_and_scheduler_state.py`, `0053_reconciliation_audit_and_manual_review.py`, `0001_paper_setup_audit_foundation.py` (per T-003).

In **`packages/domain/`** (per T-001 `domain-runtime-and-integration.md`):

- `packages/domain/src/portfolio_outlook_domain/audit.py` — the domain-level audit dataclasses + protocols.

In **`apps/api/`** (per T-006 `api-infrastructure-and-ai.md` §§6, 9):

- `apps/api/src/portfolio_outlook_api/request_audit.py` (504 lines) — the read-only `/audit/*` router over `request_logs` + `provider_sources` + `freshness_audits`.
- The three `system_event_*` modules (recorder 154 lines + reader 147 lines + mutations 153 lines) — system-event triad (cross-reference T-006 §6).

In **`apps/worker/`** (per T-007 `worker-actions-and-reconciliation.md` §8):

- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py` — writes `ReconciliationRunAuditEntry` rows around each pass.
- Per-pass audit emitters in `pass_a_orphaned_executions.py`, `pass_b_stale_in_flight.py`, `pass_c_timeout_recovery.py` — each writes `ReconciliationAuditEntry` rows with locked `divergence_type` literals.

In **`apps/api/` Decision Package + Action Draft hash chains** (per T-005 + T-007 §9):

- `apps/api/src/portfolio_outlook_api/decision_package_sync.py:build_decision_package_record` (E rank CC 36, T-055 high-severity) — content-addressed SHA-256 hash with `composed_at` + `decision_package_id` deliberately excluded so the hash is reproducible.
- `apps/worker/src/portfolio_outlook_worker/decision_package/composer.py` (572 lines, T-007 `worker-forecasting-and-decision-package.md` §9) — the worker-side hash-chain composer.

In **`apps/web/`** (per T-008 `web-pages.md` §§3.10–3.14):

- `/audit` page + 3 dynamic detail routes (`request-logs/[id]`, `freshness-audits/[id]`, `provider-sources/[id]`).

**Verdict on `packages/audit/`:** audit is the most cross-cutting concern in the codebase — every domain (IBKR sync, action drafts, reconciliation, watchlist confirmation, scheduler runs, provider calls, system events, Claude AI budget usage) has its own append-only ledger. Per T-003, all 13 repositories share the same SQLAlchemy session + connection-provider pattern, which is why they live in `packages/storage/` (the single source of the connection abstraction). A `packages/audit/` package would need to import from `packages/storage/` and would not justify its own boundary.

## 4. `packages/data_providers/`

- **README path:** `packages/data_providers/README.md`
- **README content (verbatim):** placeholder Dutch text (same as above).
- **Concept:** external data integrations (market data, broker, LLM).

### Where the data-providers concept IS implemented today

**EODHD (market data):**

- `apps/worker/src/portfolio_outlook_worker/providers/eodhd.py` (415 lines, T-007 §8) — the worker-side HTTP client (`fetch_eod` + `fetch_fx` only — no fundamentals/splits/dividends despite ADR 0003's "All-In-One" intent at `docs/decisions/0003-forecast-engine-architecture.md:29`).
- `apps/api/src/portfolio_outlook_api/eodhd_client.py` (~600 lines per T-005) — the API-side EODHD client (separate code path from the worker's; T-005 `api-forecasting-and-market-data.md` documents the split).

**IBKR (broker):**

- `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py` (558 lines, T-007 §7) — TWS connect lifecycle, tier-two paper-account guard (prefix + behavioural check), read-only `IbClientProtocol`. **No `placeOrder` / `cancelOrder` in this file.**
- Four IBKR `ibapi` clients in `apps/api/src/portfolio_outlook_api/` (per T-004 `api-ibkr-*.md`): `ibkr_ibapi_order_submission_client.py` (with the API-side `placeOrder` at `:525`), `ibkr_ibapi_manual_status_client.py`, `ibkr_ibapi_sync_client.py`, `ibkr_ibapi_account_snapshot_client.py`.
- `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submitter.py:240` — the worker-side `place_order` adapter call site (snake-case, the doctrine-claimed single owner — but cross-ref T-007 §5 documents the API also has a camelCase `placeOrder` at `ibkr_ibapi_order_submission_client.py:525`, a doctrine drift that Phase 4 should resolve).

**Anthropic Claude (LLM provider):**

- `apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py` (280 lines, T-006 §11c) — Case C explanation provider.
- `apps/api/src/portfolio_outlook_api/anthropic_ts_provider.py` (~280 lines, T-005) — Case B forecasting LLM (doctrine-locked to removal).

**Verdict on `packages/data_providers/`:** data-provider clients live next to their consumers (worker EODHD + IBKR gateway in `apps/worker`, API EODHD + IBKR ibapi + Anthropic in `apps/api`) because each provider's adapter type signature is shaped by its caller's needs. Two EODHD clients exist (api + worker) because the api's HTTP wrapper predates the worker. A `packages/data_providers/` consolidation would require negotiating a single Protocol interface that satisfies both consumers — non-trivial.

## 5. `packages/risk/`

- **README path:** `packages/risk/README.md`
- **README content (verbatim):** placeholder Dutch text (same as above).
- **Concept:** safety guards, risk policy, pre-submit validation.

### Where the risk concept IS implemented today

In **`packages/portfolio/`** (per T-002 `portfolio-guards-and-state-machines.md`):

- 10 guard modules: `approval_guards.py`, `broker_reconciliation_guards.py`, `action_draft_safety.py`, `ai_explanation_guards.py`, `execution_guards.py`, `paper_setup_guards.py`, `storage_guards.py`, `suggestion_engine_guards.py`, `suggestion_guards.py`. (T-053 inventory of B101 noqa sites is scattered across several.)
- `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py` — the cross-engine dry-run safety checks (`run_dry_run_safety_checks:461` CC D 24, `_append_per_order_type_failures:612` CC E 33 — both surfaced in T-055).
- `packages/portfolio/src/portfolio_outlook_portfolio/kelly_sizing.py` — Kelly fraction sizing (default `0.5` in code per T-002, doctrine §5.1 specifies `0.25` — flagged in T-002 as a Phase 1c gap).

In **`apps/worker/`** (per T-007 `worker-actions-and-reconciliation.md` §4):

- `apps/worker/src/portfolio_outlook_worker/ibkr_submission/safety_recheck.py` (392 lines) — the locked **12-gate pre-`place_order` re-check** with `SubmissionBlockReason` enum: `connection_down`, `mode_mismatch`, `account_id_mismatch`, `market_closed`, `duplicate_in_flight`, `hard_drawdown`, `soft_drawdown`, `daily_limit`, `cooldown`, `cash_insufficient` (twice: BUY + SELL), `fomo`. Also flagged in T-055 `FIND-RADON-001` as CC F (CC 42).

In **`apps/api/`** (per T-006 `api-infrastructure-and-ai.md` §8):

- `apps/api/src/portfolio_outlook_api/release_readiness.py` (497 lines) — 20 blocker codes (15 V1 + 5 V1.1) that act as a release-readiness risk scorecard. Hard-coded `safe_for_orders=False`, `blocks_orders=True` in `serialize_release_readiness:464-466`.

In **`packages/domain/`** (per T-001 `domain-portfolio-and-policy.md`):

- `packages/domain/src/portfolio_outlook_domain/data_quality.py` — `DataQualityGate` (FIND-RADON-002 CC C 16).
- `packages/domain/src/portfolio_outlook_domain/eligibility.py` — `SuggestionEligibilityCheck` (CC C 15) + `evaluate_suggestion_eligibility` (CC C 11).
- `packages/domain/src/portfolio_outlook_domain/capabilities.py` — `AssetCapability.validate_rules` (CC D 22) + capability vocabulary.

**Verdict on `packages/risk/`:** risk lives in `packages/portfolio/` (sizing, dry-run, guards) + `apps/worker/ibkr_submission` (tier-1 12-gate re-check) + `apps/api` (release-readiness scorecard) + `packages/domain` (eligibility + capability primitives). The 10-guard-file pattern in `packages/portfolio/` is the strongest signal that "risk" is in fact present and tested — but the responsibility is split between the deterministic-math layer (portfolio) and the runtime-gate layer (worker). A `packages/risk/` consolidation would either duplicate the math or break the worker's tier-1 placement.

## 6. `packages/tax/`

- **README path:** `packages/tax/README.md`
- **README content (verbatim):** placeholder Dutch text (same as above).
- **Concept:** Belgian-specific tax handling.

### Where the tax concept IS implemented today

In **`packages/portfolio/`**:

- `packages/portfolio/src/portfolio_outlook_portfolio/belgian_tax.py` — the actual Belgian tax module. Paired with `packages/portfolio/tests/test_belgian_tax.py`.
- `packages/portfolio/src/portfolio_outlook_portfolio/term_deposits.py` + `tests/test_term_deposits.py` — Belgian term-deposit tax/interest handling (`TermDepositInput.validate_interest_and_currency_rules` flagged at T-055 FIND-RADON-002 CC C 12).
- Cross-reference: T-002 `portfolio-daily-briefing-and-tax.md` is the reality doc that covers this surface end-to-end.

In **`packages/portfolio/src/portfolio_outlook_portfolio/daily_briefing.py`**:

- Tax-aware daily briefing logic that consumes the `belgian_tax` helpers.

**Verdict on `packages/tax/`:** of all six stubs, `tax` is the one where the implementation lives **closest to a single canonical location** (`packages/portfolio/src/portfolio_outlook_portfolio/belgian_tax.py` + sibling files). The slot was reserved before the realisation that Belgian tax math is portfolio-specific arithmetic that depends on `Money` + `Lot` primitives (T-002 `portfolio-money-and-accounting.md`) — and therefore belongs in the portfolio package. The `packages/tax/` namespace remains reserved if multi-jurisdiction tax ever splits the surface.

## Closing summary table

| Stub package | Concept | Equivalent code locations today | Phase 4 disposition (out of scope here) |
|---|---|---|---|
| `packages/ai/` | LLM provider + budget + explanation orchestration | `apps/api/.../anthropic_explanation_provider.py`, `ai_explanation_provider.py`, `ai_explanation_sync.py`, `claude_ai_budget.py`, `anthropic_ts_provider.py`, `ai_ts_provider.py`; `packages/portfolio/.../ai_ts_predictor.py`, `ai_explanation_guards.py`; `packages/storage` claude_ai_budget_usage repo + migration 0043; `docs/ai-policy.md` intent | Cross-tier slot — keep as named reservation; surfaces in T-046 gap analysis (predictor Case A/B/C drift) |
| `packages/analytics/` | calibration + backtesting + performance + coverage | `packages/portfolio/.../predictor_backtester.py`, `predictor_feedback.py`, `performance.py`, `prediction_diary_eval.py`; `apps/worker/.../forecasting/calibration_step.py`; `apps/api/.../predictor_backtest_orchestrator.py`; `apps/web/components/CalibrationCoverageBadge.tsx`; `apiClient.getCalibrationCoverage` | Reserved-name; deferred (ADR 0003 phase-4 includes calibration drift signal expansion) |
| `packages/audit/` | hash-chained audit trail + system-event triad + request audit | 13 `SqlAlchemy*AuditRepository` in `packages/storage/sql_repositories.py`; `packages/domain/audit.py`; `apps/api/request_audit.py` + `system_event_{recorder,reader,mutations}.py`; `apps/api/decision_package_sync.py` hash chain + `apps/worker/decision_package/composer.py` hash chain + `apps/worker/ibkr_reconciliation/reconciler.py` + 3 per-pass emitters; `apps/web/app/audit/*` 4 routes | Cross-cutting — already lives correctly in `packages/storage` (shares connection provider); slot reservation is informational only |
| `packages/data_providers/` | EODHD + IBKR + Anthropic adapter layer | `apps/worker/.../providers/eodhd.py` + `apps/api/.../eodhd_client.py` (two clients); `apps/worker/.../ibkr_gateway.py` + 4 `apps/api/.../ibkr_ibapi_*.py` clients; `apps/api/.../anthropic_explanation_provider.py` + `anthropic_ts_provider.py` | Reserved-name; would require Protocol-unification work to consolidate the two EODHD clients |
| `packages/risk/` | safety guards + pre-submit re-check + release readiness + capability/eligibility | `packages/portfolio/.../action_draft_safety.py`, `kelly_sizing.py`, 9 `*_guards.py` modules; `apps/worker/.../ibkr_submission/safety_recheck.py` (12 locked gates); `apps/api/.../release_readiness.py` (20 blocker codes); `packages/domain/.../{data_quality,eligibility,capabilities}.py` | Most-distributed — risk is intentionally placed at the deterministic-math layer (portfolio) AND the runtime-gate layer (worker); slot reservation would conflict with both placements |
| `packages/tax/` | Belgian tax + term deposits | `packages/portfolio/.../belgian_tax.py` + `term_deposits.py`; `packages/portfolio/.../daily_briefing.py` (consumer) | Single canonical home in portfolio; slot reservation only meaningful if multi-jurisdiction tax is ever added |

**No stub package falls into the "no equivalent — fully unimplemented" bucket.** Every reserved namespace has live implementation elsewhere in the tree.

## Cross-cutting architectural observation

The named-stub-without-source pattern is a **deliberate architectural signal**: someone reserved namespace for these six concerns before deciding where each one would actually live. The eventual placements (mostly in `apps/{api,worker}` or `packages/portfolio`) reflect three convergence pressures the original split could not anticipate:

1. **Co-location with the Settings + storage-connection-provider plumbing** — the AI + audit surfaces ended up in `apps/api` because both consume `apps/api/.../config.py:Settings` and `StorageConnectionProvider`. Splitting them out would require either duplicating the Settings hierarchy or introducing a third-party shared package.
2. **Co-location with the consumer** — the worker has its own EODHD client (`apps/worker/.../providers/eodhd.py`) because the worker is the only place that consumes market data at morning-chain time; a shared `packages/data_providers/` would need to satisfy both api + worker shapes.
3. **The deterministic-math vs runtime-gate split** — risk is fundamentally **two different concerns** (pure-function pre-submit math + tier-1 runtime re-check on the IBKR connection). Putting both in one `packages/risk/` package would force one of the two callers (the worker) to import from a package that also depends on the worker's own runtime state.

**For Track 1b (architecture review)**: the question is not "should the stubs be filled?" — it is "is the current distribution the best long-term split?" The reality doc records *what is*, not *what should be*. Phase 1c gap analysis (T-046 + related) carries the prescriptive call.

**For Track 1c (gap analysis)**: the stub-versus-actual mismatch is most informative for the AI cluster (Case A/B/C drift documented in T-005 + T-006 + T-007 — Case A "AI" stub that is classical stats, Case B forecasting LLM doctrine-locked to removal, Case C explanation LLM live with monthly budget). The named `packages/ai/` slot would, if filled, have a clear policy: only Case C lives there. That decision belongs to Phase 4.
