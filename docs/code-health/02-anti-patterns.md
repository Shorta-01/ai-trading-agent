# Anti-Patterns — populated in Phase 1d

## FIND-009 (was FIND-BANDIT-001) — `assert` used for type-narrowing in production paths (20 occurrences across 8 files)

- **Tool:** `bandit 1.9.4`, test `B101 assert_used`, severity LOW (bandit's rating). Raw output `/tmp/bandit-low-and-up.json` (T-053).
- **Pattern:** every B101 site is a post-validation type-narrowing `assert x is not None` that follows an explicit `if x is None: _raise_*(...)` or framework-raise. The assert exists to satisfy mypy's narrowing in strict mode, not as an invariant guard.

### Inventory (file:line)

| File | Lines | Note |
|---|---|---|
| `apps/api/src/portfolio_outlook_api/action_draft.py` | `:260, :498, :499, :500, :501, :502, :503, :504, :505` | 9 asserts; eight (`:498-505`) narrow user-supplied draft fields after a missing-field guard at `:489-495` |
| `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py` | `:278, :279, :295, :296` | 4 asserts inside `_sum_positions` / `_sum_cash`; already documented in `docs/reality/components/portfolio-money-and-accounting.md` ("uses bare `assert` for `None` checks inside the summation helpers") |
| `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py` | 2 lines | sweep-tick null guards |
| `apps/api/src/portfolio_outlook_api/ibkr_submission.py` | 1 line | |
| `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py` | 1 line | |
| `apps/api/src/portfolio_outlook_api/reconciliation.py` | 1 line | |
| `apps/worker/src/portfolio_outlook_worker/forecasting/asset_universe_resolver.py` | 1 line | |
| `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` | 1 line | |

### Evidence

```python
# apps/api/src/portfolio_outlook_api/action_draft.py:256-262
def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    assert storage.database_url is not None  # _raise_storage_unavailable raises above
    return StorageConnectionProvider(...)
```

```python
# packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py:275-285
for position in positions:
    assert position.native_market_value is not None
    assert position.source_currency is not None
    if position.source_currency == base_currency:
        total += position.native_market_value
        continue
    ...
```

### Why it matters (plain English)

`assert` is removed by `python -O`. In every B101 site here, removal is **safe today** because the prior validation (`_raise_*`, `HTTPException`, or an explicit `if missing: raise`) raises first; the assert only narrows the type for mypy. The risk is **documentation drift**: a future refactor that removes the prior raise without noticing would silently turn the assert into the sole guard, then have that guard vanish under `python -O`. AGENTS.md ("Every decision must be logged") favors an explicit raise even where mypy can be satisfied with `assert`.

### Fix approach

Replace each site with one of:
- `if x is None: raise RuntimeError("invariant violated: ...")` — explicit invariant check; survives `-O`.
- `typing.cast(T, x)` — pure type-narrowing without runtime cost or `-O` sensitivity.

The choice per-site depends on whether the assertion is documenting an internal invariant (use `cast`) or a true post-validation guarantee (use explicit `raise`).

### Complexity / severity

- Complexity: **small**. Each site is a one-line swap; no behaviour change.
- Severity: **low**. No runtime vulnerability today; the surrounding validation already raises. Risk is purely future-refactor-fragility.

### Related findings

None directly; the B110/B112 `try/except/pass(continue)` patterns inventoried in `_dismissed.md` under T-053 are documented boundary catches, not the same family.

## FIND-010 (was FIND-RADON-001) — High-severity cyclomatic complexity (rank E/F, 10 functions across 9 files)

- **Tool:** `radon 6.0.1`, command `radon cc -s -a apps packages`. Raw output `/tmp/radon-cc-baseline.txt` (T-055).
- **Pattern:** ten functions exceed Radon's "moderate" complexity threshold (CC ≥ 21 → rank D, ≥ 31 → rank E, ≥ 41 → rank F). Six are E (`CC 31–40`) and four are F (`CC ≥ 41`); the worst two tie at CC 58. All ten are in production source — none in tests.
- **Severity mapping rationale:** the locked T-055 threshold maps CC ≥ 21 (`E`/`F`) to **high** because these functions are large enough that a unit-test refactor alone cannot easily catch regressions on every branch.

### Inventory (file:line, rank, CC)

| Site | Function | Rank | CC |
|---|---|---|---|
| `apps/api/src/portfolio_outlook_api/ibkr_sync_validation.py:49` | `validate_ibkr_sync_payloads` | F | 58 |
| `apps/api/src/portfolio_outlook_api/portfolio_valuation_readiness.py:471` | `build_portfolio_valuation_readiness` | F | 58 |
| `apps/worker/src/portfolio_outlook_worker/orchestrator.py:183` | `run_orchestrator` | F | 42 |
| `apps/worker/src/portfolio_outlook_worker/ibkr_submission/safety_recheck.py:240` | `evaluate_submission_gates` | F | 42 |
| `packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py:272` | `_apply_clip_with_water_filling` | E | 40 |
| `apps/api/src/portfolio_outlook_api/ibkr_sync.py:106` | `run_sync` | E | 37 |
| `apps/api/src/portfolio_outlook_api/decision_package_sync.py:220` | `build_decision_package_record` | E | 36 |
| `apps/api/src/portfolio_outlook_api/market_data_sync.py:269` | `sync_market_data_and_fx` | E | 35 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:1405` | `run_decision_packages_sync` | E | 34 |
| `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py:612` | `_append_per_order_type_failures` | E | 33 |

### Why it matters (plain English)

Five of the ten sites are the morning-chain sync orchestrators (`run_sync`, `sync_market_data_and_fx`, `run_decision_packages_sync`, `build_decision_package_record`, `run_orchestrator`). They mutate persisted state, drive the daily briefing, and carry the most business-critical branching. High CC here means: every new branch added under time pressure compounds an already-hard-to-cover decision tree, and the reality docs (`docs/reality/components/api-forecasting-and-market-data.md`, `…-actions-suggestions-and-watchlists.md`, `worker` cluster T-007) already note these as the trickiest modules to trace.

Two of the ten sites are the **safety/readiness builders** that the project's tri-defence pattern leans on: `evaluate_submission_gates` (worker-side, the final guard before `placeOrder`) and `build_portfolio_valuation_readiness` (the readiness scorecard that the order-safety floor depends on). High CC in safety code raises audit risk — a future refactor that subtly drops a branch could weaken a guard without a test catching it.

The remaining three (`_apply_clip_with_water_filling`, `_append_per_order_type_failures`, `validate_ibkr_sync_payloads`) are pure-function helpers — easier to refactor, but currently the densest decision trees in their files.

### Fix approach

- **Per-function approach.** Extract the inner branching of each E/F function into named helpers, one branch per helper, with a flat top-level driver. Target CC ≤ 10 (rank A/B) per refactored helper.
- **Safety-critical functions first.** Order of refactor: `evaluate_submission_gates`, `build_portfolio_valuation_readiness`, `validate_ibkr_sync_payloads`, then the four sync orchestrators (`run_sync`, `sync_market_data_and_fx`, `run_decision_packages_sync`, `build_decision_package_record`), then the helpers.
- **No behaviour change.** Refactors must preserve the exact branch behaviour — every refactor PR should have a unit test asserting the input/output table is unchanged.
- **Out of scope for T-055.** This task is the baseline only; refactors are Phase 4 territory.

### Complexity / severity

- Complexity to fix: **medium per function** — pure extraction is mechanical, but the safety-critical ones need careful test coverage first.
- Severity: **high** (per the locked T-055 severity mapping for CC ≥ 21).

### Related findings

- The medium-severity CC cluster `FIND-RADON-002` covers the same anti-pattern at a lower threshold (CC 11–20).
- Five of the ten functions are in modules also flagged by `FIND-RADON-003` for low maintainability index (`status_routes.py`, `portfolio_valuation_readiness.py`, `sql_repositories.py`).

## FIND-011 (was FIND-RADON-002) — Medium-severity cyclomatic complexity (rank C/D, 202 functions)

- **Tool:** `radon 6.0.1`, raw output `/tmp/radon-cc-baseline.txt` (T-055).
- **Pattern:** 202 functions/methods at CC 11–30 (182 rank C, 20 rank D). Split: 113 in production source (98 C + 15 D), 89 in test files (84 C + 5 D).
- **Severity mapping rationale:** the locked T-055 threshold maps CC 11–20 (`C`/`D`) to **medium**. Tests at rank C/D are documented here too because the task scope (`radon cc apps packages`) is project-wide; their fix approach differs from production (see below).

### Inventory (file:line, rank, CC) — sorted by file:line

| Site | Function | Rank | CC |
|---|---|---|---|
| `apps/api/src/portfolio_outlook_api/action_draft.py:396` | `create_action_draft` | D | 23 |
| `apps/api/src/portfolio_outlook_api/action_draft.py:585` | `patch_action_draft` | C | 14 |
| `apps/api/src/portfolio_outlook_api/action_draft_submission.py:313` | `submit_action_draft_to_paper` | C | 20 |
| `apps/api/src/portfolio_outlook_api/action_draft_sync.py:101` | `generate_action_drafts` | C | 15 |
| `apps/api/src/portfolio_outlook_api/ai_explanation_sync.py:83` | `_build_canonical_input` | C | 11 |
| `apps/api/src/portfolio_outlook_api/ai_ts_provider.py:85` | `StubTsModelProvider.forecast` | C | 12 |
| `apps/api/src/portfolio_outlook_api/ai_ts_provider.py:168` | `build_ts_model_provider` | C | 12 |
| `apps/api/src/portfolio_outlook_api/decision_package_sync.py:355` | `sync_decision_packages` | D | 24 |
| `apps/api/src/portfolio_outlook_api/eodhd_client.py:418` | `_parse_fundamentals` | C | 20 |
| `apps/api/src/portfolio_outlook_api/forecast_routes.py:397` | `read_forecast_day_summary` | C | 12 |
| `apps/api/src/portfolio_outlook_api/forecast_sync.py:179` | `sync_forecasts` | D | 28 |
| `apps/api/src/portfolio_outlook_api/ibkr_connection_read_model.py:89` | `synthesise_connection_status` | D | 22 |
| `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py:281` | `_build_orders_for_type` | D | 24 |
| `apps/api/src/portfolio_outlook_api/ibkr_status.py:147` | `build_ibkr_status_placeholder` | D | 24 |
| `apps/api/src/portfolio_outlook_api/ibkr_sync.py:402` | `read_status` | C | 17 |
| `apps/api/src/portfolio_outlook_api/ibkr_sync_readiness.py:6` | `build_ibkr_sync_readiness` | C | 16 |
| `apps/api/src/portfolio_outlook_api/ibkr_tws_readonly_runtime.py:102` | `check_tws_readonly_runtime_preflight` | C | 13 |
| `apps/api/src/portfolio_outlook_api/ibkr_watchlists.py:127` | `import_ibkr_watchlist` | C | 17 |
| `apps/api/src/portfolio_outlook_api/market_data_readiness.py:217` | `build_readiness_row` | C | 11 |
| `apps/api/src/portfolio_outlook_api/market_data_runtime_routes.py:249` | `read_snapshots_by_account` | C | 13 |
| `apps/api/src/portfolio_outlook_api/market_data_sync.py:146` | `derive_required_fx_pairs` | C | 13 |
| `apps/api/src/portfolio_outlook_api/online_storage_status.py:39` | `build_online_storage_status` | C | 11 |
| `apps/api/src/portfolio_outlook_api/portfolio_valuation_readiness.py:212` | `build_position_row` | D | 29 |
| `apps/api/src/portfolio_outlook_api/portfolio_valuation_readiness.py:802` | `build_portfolio_reconciliation_readiness` | D | 24 |
| `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py:199` | `run_backtest_for_symbol` | C | 11 |
| `apps/api/src/portfolio_outlook_api/reconciliation_sync.py:93` | `_classify` | C | 16 |
| `apps/api/src/portfolio_outlook_api/reconciliation_sync.py:150` | `_persist_state_transition` | C | 12 |
| `apps/api/src/portfolio_outlook_api/reconciliation_sync.py:226` | `reconcile_submissions` | C | 20 |
| `apps/api/src/portfolio_outlook_api/research_sources.py:333` | `_archive_uploaded_file` | C | 16 |
| `apps/api/src/portfolio_outlook_api/research_sources.py:376` | `_extract_plain_research_text` | C | 12 |
| `apps/api/src/portfolio_outlook_api/scheduler_routes.py:109` | `read_scheduler_v127_status` | C | 12 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:463` | `read_ibkr_sync_run_detail` | C | 12 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:576` | `read_portfolio_valuation_readiness` | C | 15 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:992` | `run_forecast_sync` | C | 13 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:1206` | `run_suggestions_sync` | C | 12 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:1691` | `run_explanation_for_decision_package` | C | 13 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:1884` | `run_action_drafts_sync` | C | 17 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:2351` | `run_action_drafts_reconciliation` | C | 14 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:2477` | `run_prediction_diary_evaluation` | C | 13 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:2627` | `run_daily_briefing` | C | 19 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:2860` | `read_market_data_snapshot_latest` | D | 21 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:3068` | `run_morning_chain_manually` | C | 15 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:3593` | `read_decision_package_diff` | C | 14 |
| `apps/api/src/portfolio_outlook_api/status_routes.py:3705` | `read_predictor_leaderboard` | C | 13 |
| `apps/api/src/portfolio_outlook_api/suggestion_sync.py:132` | `sync_suggestions` | C | 14 |
| `apps/api/src/portfolio_outlook_api/universe_scan_sync.py:174` | `scan_universe` | D | 21 |
| `apps/api/src/portfolio_outlook_api/watchlist_confirmation_routes.py:201` | `confirm_watchlist` | C | 11 |
| `apps/api/tests/test_action_draft_endpoints.py:195` | `test_compute_full_cycle_with_fake_repos` | C | 12 |
| `apps/api/tests/test_action_draft_submission.py:327` | `test_submit_happy_path_calls_real_client_and_persists_submitted_state` | C | 16 |
| `apps/api/tests/test_action_draft_sync.py:111` | `test_kopen_package_produces_one_draft_persisted_with_dry_run_passed` | C | 14 |
| `apps/api/tests/test_ai_explanation_endpoints.py:231` | `test_run_explanation_happy_path_with_stub_provider` | C | 12 |
| `apps/api/tests/test_ai_explanation_sync.py:150` | `test_stub_provider_happy_path_persists_generated_explanation` | C | 16 |
| `apps/api/tests/test_anthropic_ts_provider.py:153` | `test_forecast_returns_typed_result_and_persists_audit_row` | C | 11 |
| `apps/api/tests/test_decision_package_routes.py:156` | `test_get_by_id_returns_full_payload` | C | 15 |
| `apps/api/tests/test_decision_package_sync.py:201` | `test_happy_path_persists_one_package_with_full_evidence_chain` | C | 18 |
| `apps/api/tests/test_eodhd_client.py:47` | `test_fetch_quote_returns_parsed_decimal_fields_and_timestamp` | C | 11 |
| `apps/api/tests/test_eodhd_client.py:227` | `test_fetch_fundamentals_parses_subset_of_payload` | C | 13 |
| `apps/api/tests/test_forecast_endpoints.py:99` | `test_compute_runs_full_cycle_with_fake_repos_and_provider` | C | 12 |
| `apps/api/tests/test_forecast_routes.py:143` | `test_latest_returns_full_payload_with_eur_native_levels` | C | 13 |
| `apps/api/tests/test_forecast_sync.py:167` | `test_happy_path_persists_bars_and_forecasts_with_safety_booleans_false` | C | 15 |
| `apps/api/tests/test_ibkr_ibapi_order_submission_client.py:299` | `test_build_bracket_returns_three_orders_with_correct_transmit_flags` | C | 14 |
| `apps/api/tests/test_ibkr_ibapi_sync_client.py:250` | `test_sync_account_summary_returns_typed_cash_with_decimal_values` | C | 11 |
| `apps/api/tests/test_ibkr_ibapi_sync_client.py:277` | `test_sync_positions_returns_typed_positions_with_decimal_quantity` | C | 11 |
| `apps/api/tests/test_ibkr_ibapi_sync_client.py:313` | `test_sync_open_orders_returns_typed_orders_with_remaining` | C | 14 |
| `apps/api/tests/test_ibkr_ibapi_sync_client.py:360` | `test_sync_executions_merges_commission_reports` | C | 13 |
| `apps/api/tests/test_ibkr_status_endpoint.py:26` | `test_ibkr_status_endpoint_disabled_default_response` | C | 14 |
| `apps/api/tests/test_ibkr_status_endpoint.py:111` | `test_ibkr_status_wrong_account_mode_via_fake_adapter` | C | 13 |
| `apps/api/tests/test_ibkr_status_endpoint.py:142` | `test_ibkr_status_explicit_mismatch_without_account_mode_stays_mismatch` | C | 13 |
| `apps/api/tests/test_ibkr_status_endpoint.py:199` | `test_ibkr_status_infers_wrong_account_mode_from_adapter_account_mode` | C | 13 |
| `apps/api/tests/test_ibkr_status_endpoint.py:231` | `test_ibkr_status_unknown_without_account_mode_and_without_mismatch` | C | 12 |
| `apps/api/tests/test_ibkr_sync_endpoints.py:117` | `test_sync_runs_history_and_detail_after_valid_sync` | C | 12 |
| `apps/api/tests/test_ibkr_sync_endpoints.py:196` | `test_status_and_read_endpoints_use_memory_when_storage_disabled` | C | 11 |
| `apps/api/tests/test_ibkr_sync_endpoints.py:461` | `test_durable_status_contract_includes_payload_validation_and_safety` | C | 14 |
| `apps/api/tests/test_ibkr_sync_latest_routes.py:109` | `test_positions_route_returns_locked_v126b_shape` | C | 14 |
| `apps/api/tests/test_ibkr_sync_latest_routes.py:188` | `test_cash_route_returns_locked_v126b_shape` | C | 11 |
| `apps/api/tests/test_ibkr_tws_readonly_runtime.py:75` | `_assert_safety_flags_false` | C | 11 |
| `apps/api/tests/test_ibkr_tws_readonly_status_endpoint.py:65` | `_assert_safety_flags_false` | C | 11 |
| `apps/api/tests/test_market_data_readiness_endpoint.py:68` | `test_market_data_readiness_blocks_unvalidated_identity` | C | 20 |
| `apps/api/tests/test_market_data_readiness_endpoint.py:105` | `test_market_data_readiness_ready_for_validated_identity_only` | C | 13 |
| `apps/api/tests/test_market_data_readiness_endpoint.py:143` | `test_market_data_readiness_list_response_contract` | C | 11 |
| `apps/api/tests/test_market_data_readiness_endpoint.py:301` | `test_market_data_snapshot_latest_returns_not_configured_when_storage_disabled` | C | 16 |
| `apps/api/tests/test_market_data_readiness_endpoint.py:459` | `test_market_data_readiness_stored_snapshot_metadata_is_read_only` | C | 16 |
| `apps/api/tests/test_market_data_readiness_endpoint.py:511` | `test_market_data_snapshot_latest_returns_snapshot_available_variant` | D | 26 |
| `apps/api/tests/test_market_data_sync.py:223` | `test_sync_happy_path_persists_quotes_and_fx_with_safe_flags_false` | D | 22 |
| `apps/api/tests/test_market_data_sync_endpoint.py:70` | `test_sync_runs_full_cycle_with_fake_provider_and_repos` | C | 18 |
| `apps/api/tests/test_prediction_diary_sync.py:148` | `test_happy_path_persists_entry_with_outcomes` | C | 14 |
| `apps/api/tests/test_reconciliation_sync.py:149` | `test_full_fill_transitions_to_filled_then_reconciled` | C | 16 |
| `apps/api/tests/test_research_source_archive_endpoints.py:559` | `test_upload_txt_success_and_metadata` | C | 13 |
| `apps/api/tests/test_research_source_archive_endpoints.py:706` | `test_source_credibility_defaults_and_remains_blocked` | C | 12 |
| `apps/api/tests/test_research_source_archive_endpoints.py:744` | `test_evidence_item_register_and_list` | C | 11 |
| `apps/api/tests/test_scheduler_endpoints.py:224` | `test_morning_chain_route_runs_and_persists_audit_row` | C | 13 |
| `apps/api/tests/test_status_endpoints.py:33` | `test_system_status_summary` | C | 15 |
| `apps/api/tests/test_status_endpoints.py:58` | `test_settings_summary` | C | 11 |
| `apps/api/tests/test_storage_status_endpoint.py:7` | `test_storage_status_endpoint` | D | 29 |
| `apps/api/tests/test_storage_status_online_endpoint.py:61` | `test_online_storage_status_success_connection_lifecycle` | C | 11 |
| `apps/api/tests/test_suggestion_endpoints.py:170` | `test_compute_runs_full_cycle_with_fake_repos` | C | 12 |
| `apps/api/tests/test_system_events_active_endpoint.py:82` | `test_active_events_loaded_read_only_connection` | C | 13 |
| `apps/api/tests/test_universe_scan_sync.py:127` | `test_scan_persists_one_snapshot_per_ticker_and_updates_run` | C | 12 |
| `apps/worker/src/portfolio_outlook_worker/action_draft/composer.py:91` | `compose_action_draft_from_decision_package` | C | 15 |
| `apps/worker/src/portfolio_outlook_worker/action_draft/composer.py:269` | `compose_action_draft_user_supplied` | C | 12 |
| `apps/worker/src/portfolio_outlook_worker/forecasting/asset_universe_resolver.py:77` | `resolve_forecast_universe` | C | 17 |
| `apps/worker/src/portfolio_outlook_worker/forecasting/forecasting_step.py:195` | `_forecast_single_asset` | C | 11 |
| `apps/worker/src/portfolio_outlook_worker/forecasting/historical_bootstrap.py:52` | `compute_historical_bootstrap_forecast` | C | 13 |
| `apps/worker/src/portfolio_outlook_worker/forecasting/label_translator.py:54` | `translate_to_label` | C | 14 |
| `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py:187` | `IbkrGateway.connect` | C | 13 |
| `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:233` | `SubmissionSweep._run_locked` | C | 11 |
| `apps/worker/src/portfolio_outlook_worker/market_data_step.py:92` | `fetch_market_data_for_account` | C | 14 |
| `apps/worker/src/portfolio_outlook_worker/providers/eodhd.py:194` | `EodhdClient._request` | C | 13 |
| `apps/worker/src/portfolio_outlook_worker/storage_readiness.py:34` | `build_worker_storage_readiness` | C | 11 |
| `apps/worker/tests/test_decision_package_composer.py:162` | `test_compose_eur_native_asset_produces_full_package` | D | 21 |
| `apps/worker/tests/test_decision_package_composer.py:411` | `test_dutch_explanation_contains_required_elements` | C | 11 |
| `apps/worker/tests/test_eodhd_client.py:91` | `test_fetch_eod_parses_decimal_preserving_precision` | C | 15 |
| `apps/worker/tests/test_ibkr_gateway.py:139` | `test_connect_paper_success_writes_full_audit_chain` | C | 19 |
| `apps/worker/tests/test_ibkr_gateway.py:211` | `test_connect_refuses_when_prefix_and_behavioural_disagree` | C | 12 |
| `apps/worker/tests/test_ibkr_gateway_decimal.py:139` | `test_fetch_positions_returns_decimal_quantity_and_avg_cost` | C | 13 |
| `apps/worker/tests/test_lifecycle_handler_fill.py:112` | `test_full_fill_transitions_to_filled_and_writes_execution` | C | 13 |
| `apps/worker/tests/test_lifecycle_handler_partial_fill.py:103` | `test_partial_fill_then_full_fill` | C | 13 |
| `apps/worker/tests/test_lifecycle_handler_rejection.py:105` | `test_rejection_transitions_submitted_to_rejected_and_captures_reason` | C | 11 |
| `apps/worker/tests/test_order_builder_decimal_boundary.py:120` | `test_build_ib_order_happy_path_preserves_decimal_then_converts` | C | 13 |
| `apps/worker/tests/test_pass_a_orphaned_executions_happy.py:225` | `test_orphaned_full_fill_heals_submitted_draft_to_filled` | C | 12 |
| `apps/worker/tests/test_pass_a_unmatched_execution.py:128` | `test_unmatched_execution_appends_unmatched_row_and_audit` | C | 11 |
| `apps/worker/tests/test_pass_c_timeout_recovery.py:148` | `test_timeout_older_than_24h_escalates_to_manual_review` | C | 14 |
| `apps/worker/tests/test_reconciler_orchestrator.py:212` | `test_full_tick_with_orphaned_execution_and_timeout_escalation` | C | 13 |
| `apps/worker/tests/test_starter_watchlist.py:138` | `test_seed_writes_12_rows_with_resolver_returning_listings` | C | 16 |
| `apps/worker/tests/test_submitter_connection_lost.py:190` | `test_place_order_connection_lost_records_audit_and_stays_user_approved` | C | 15 |
| `apps/worker/tests/test_submitter_happy_path.py:179` | `test_happy_path_writes_audit_and_transitions_to_submitted` | C | 19 |
| `apps/worker/tests/test_submitter_happy_path.py:221` | `test_account_id_mismatch_at_tier_two_blocks` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/capabilities.py:6` | `AssetCapability` | D | 23 |
| `packages/domain/src/portfolio_outlook_domain/capabilities.py:20` | `AssetCapability.validate_rules` | D | 22 |
| `packages/domain/src/portfolio_outlook_domain/data_quality.py:70` | `DataQualityGate` | C | 16 |
| `packages/domain/src/portfolio_outlook_domain/data_quality.py:83` | `DataQualityGate.validate_gate` | C | 15 |
| `packages/domain/src/portfolio_outlook_domain/data_sources.py:27` | `DataSourcePolicy` | C | 12 |
| `packages/domain/src/portfolio_outlook_domain/data_sources.py:38` | `DataSourcePolicy.validate_policy` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/eligibility.py:41` | `SuggestionEligibilityCheck` | C | 15 |
| `packages/domain/src/portfolio_outlook_domain/eligibility.py:55` | `SuggestionEligibilityCheck.validate_check` | C | 14 |
| `packages/domain/src/portfolio_outlook_domain/eligibility.py:97` | `evaluate_suggestion_eligibility` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/execution.py:47` | `ExecutionTarget.validate_rules` | C | 14 |
| `packages/domain/src/portfolio_outlook_domain/execution.py:108` | `ExecutionModeSettings` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/lots.py:11` | `PaperLot` | C | 15 |
| `packages/domain/src/portfolio_outlook_domain/lots.py:26` | `PaperLot.validate_lot` | C | 14 |
| `packages/domain/src/portfolio_outlook_domain/market_calendar.py:261` | `evaluate_tradability` | C | 14 |
| `packages/domain/src/portfolio_outlook_domain/market_data_foundation.py:118` | `evaluate_market_data_readiness` | C | 12 |
| `packages/domain/src/portfolio_outlook_domain/orders.py:37` | `PaperOrder.validate_order` | C | 14 |
| `packages/domain/src/portfolio_outlook_domain/research_library.py:298` | `classify_document_deterministically` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/research_suggestions.py:278` | `ResearchSourceReference._validate_reference` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/runtime.py:123` | `RuntimeTopology` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/scheduler.py:52` | `ScheduledJobDefinition` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/scheduler.py:67` | `ScheduledJobDefinition.validate_model` | C | 12 |
| `packages/domain/src/portfolio_outlook_domain/scheduler.py:90` | `JobEligibilityCheck` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/scheduler.py:120` | `JobRunRecord` | C | 12 |
| `packages/domain/src/portfolio_outlook_domain/scheduler.py:132` | `JobRunRecord.validate_model` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/settings.py:191` | `evaluate_asset_permission` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/settings.py:396` | `IBKRConnectionSettings.validate_model` | C | 16 |
| `packages/domain/src/portfolio_outlook_domain/settings.py:578` | `ApiUsageSummary.validate_model` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/settings.py:660` | `SettingsProfile` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/storage.py:167` | `StorageReadinessCheck` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/storage.py:186` | `StorageReadinessCheck.validate_readiness` | C | 12 |
| `packages/domain/src/portfolio_outlook_domain/suggestion_engine.py:59` | `SuggestionGateResult` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/suggestion_engine.py:71` | `SuggestionGateResult.validate_model` | C | 12 |
| `packages/domain/src/portfolio_outlook_domain/suggestion_engine.py:90` | `RiskGateResult` | C | 11 |
| `packages/domain/src/portfolio_outlook_domain/suggestion_engine.py:249` | `decide_suggestion_draft_outcome` | C | 13 |
| `packages/domain/src/portfolio_outlook_domain/term_deposits.py:48` | `TermDepositInput.validate_interest_and_currency_rules` | C | 12 |
| `packages/domain/tests/test_market_calendar.py:133` | `test_evaluate_tradability_and_helptexts` | C | 11 |
| `packages/domain/tests/test_suggestion_engine.py:89` | `test_core_models_and_helpers` | C | 16 |
| `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py:295` | `derive_action_draft_sizing` | C | 13 |
| `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py:461` | `run_dry_run_safety_checks` | D | 24 |
| `packages/portfolio/src/portfolio_outlook_portfolio/action_draft_safety.py:561` | `_append_v1_1_tif_and_conditional_failures` | C | 19 |
| `packages/portfolio/src/portfolio_outlook_portfolio/ai_explanation_guards.py:64` | `_normalise_numeric_token` | C | 11 |
| `packages/portfolio/src/portfolio_outlook_portfolio/ensemble_combiner.py:166` | `compute_ensemble_forecast` | D | 29 |
| `packages/portfolio/src/portfolio_outlook_portfolio/kelly_sizing.py:142` | `apply_risk_parity_caps` | C | 11 |
| `packages/portfolio/src/portfolio_outlook_portfolio/ledger_services.py:166` | `validate_cash_entry_sign` | C | 11 |
| `packages/portfolio/src/portfolio_outlook_portfolio/mean_reversion_predictor.py:172` | `_compute_hurst` | C | 16 |
| `packages/portfolio/src/portfolio_outlook_portfolio/mean_reversion_predictor.py:380` | `MeanReversionPredictor.predict` | C | 13 |
| `packages/portfolio/src/portfolio_outlook_portfolio/momentum_predictor.py:341` | `MomentumPredictor.predict` | C | 12 |
| `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py:113` | `walk_forward_backtest` | C | 12 |
| `packages/portfolio/src/portfolio_outlook_portfolio/predictor_backtester.py:196` | `aggregate_window_score` | C | 11 |
| `packages/portfolio/src/portfolio_outlook_portfolio/predictor_feedback.py:195` | `compute_inverse_brier_weights` | C | 16 |
| `packages/portfolio/src/portfolio_outlook_portfolio/qvm_factor_predictor.py:227` | `_sector_neutral_factor_score_for_symbol` | C | 12 |
| `packages/portfolio/src/portfolio_outlook_portfolio/qvm_factor_predictor.py:394` | `QvmFactorPredictor.predict` | C | 19 |
| `packages/portfolio/src/portfolio_outlook_portfolio/snapshot.py:96` | `calculate_transaction_totals` | C | 13 |
| `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py:120` | `calculate_conversion_totals` | D | 30 |
| `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py:305` | `_blocked` | C | 11 |
| `packages/portfolio/tests/test_baseline_forecast.py:127` | `test_baseline_against_realistic_positive_drift_series` | C | 12 |
| `packages/portfolio/tests/test_capabilities.py:38` | `test_watch_only_and_blocked_categories` | C | 13 |
| `packages/portfolio/tests/test_daily_briefing.py:44` | `test_empty_inputs_yield_zero_counts_and_dutch_summary` | C | 12 |
| `packages/portfolio/tests/test_performance.py:156` | `test_calculate_net_result_and_return_cases` | C | 11 |
| `packages/portfolio/tests/test_performance.py:218` | `test_build_portfolio_performance_summary_cases` | C | 11 |
| `packages/portfolio/tests/test_term_deposits.py:90` | `test_net_interest_expected_value_days_status_and_projection_totals` | C | 19 |
| `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:1306` | `SqlAlchemyResearchSourceArchiveRepository.search_asset_listings` | C | 11 |
| `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:2495` | `_action_draft_from_row` | C | 12 |
| `packages/storage/tests/test_alembic_skeleton.py:95` | `test_0002_revision_content_and_safety_guards` | C | 15 |
| `packages/storage/tests/test_alembic_skeleton.py:159` | `test_0003_revision_content_and_safety_guards` | C | 15 |
| `packages/storage/tests/test_alembic_skeleton.py:195` | `test_0004_revision_content_and_safety_guards` | C | 13 |
| `packages/storage/tests/test_alembic_skeleton.py:228` | `test_0005_revision_content_and_safety_guards` | C | 13 |
| `packages/storage/tests/test_alembic_skeleton.py:256` | `test_0006_revision_content_and_safety_guards` | C | 15 |
| `packages/storage/tests/test_decision_package_repository.py:128` | `test_append_and_get_by_id_roundtrips_record` | C | 11 |
| `packages/storage/tests/test_public_exports.py:6` | `test_research_source_records_used_by_api_are_exported` | C | 16 |
| `packages/storage/tests/test_research_source_archive_repository.py:71` | `test_archive_repository_roundtrips_and_filters` | D | 30 |
| `packages/storage/tests/test_sql_repositories.py:317` | `test_system_event_resolve_and_archive_hide_from_open_list` | C | 12 |
| `packages/storage/tests/test_sql_repositories.py:366` | `test_ibkr_sync_repository_roundtrip_and_lists` | C | 17 |
| `packages/storage/tests/test_sql_repositories.py:519` | `test_fx_rate_snapshot_roundtrip_and_latest_lookup` | C | 11 |
| `packages/storage/tests/test_sql_repositories.py:806` | `test_asset_decision_package_repository_persists_and_returns_latest` | C | 12 |

### Pattern observations

- **Hottest production module: `apps/api/src/portfolio_outlook_api/status_routes.py`** — 14 functions at rank C/D (plus one E in `FIND-RADON-001`). The mixed-cluster nature of this 4014-line router (T-006 reality doc §5) is the root cause; splitting the file into per-cluster routers would naturally reduce per-function CC.
- **Pydantic `validate_*` methods recur 23 times in `packages/domain/`** — most are `@model_validator(mode="after")` methods whose CC is inflated by the chain of `raise` clauses. Refactor potential is limited (each `raise` corresponds to one locked invariant), so dismiss-as-acceptable might apply during a future review.
- **Test-side C/D entries are mostly happy-path integration tests** (`test_happy_path_writes_audit_and_transitions_to_submitted`, `test_compose_eur_native_asset_produces_full_package`, etc.). Refactor approach for tests is splitting into smaller assertion-grouped tests rather than helper-extraction — the test's branchiness mirrors the assertion chain.

### Fix approach

- **Per-function:** extract helpers as for `FIND-RADON-001`, but lower priority. Target CC ≤ 10 (rank A/B).
- **Test side (89 of 202 entries):** split assertion blocks into smaller `test_*` functions or use `pytest.mark.parametrize` to flatten branches.
- **Pydantic validators (23 entries):** typically acceptable; can be dismissed individually after review.
- **Out of scope for T-055.** Refactors are Phase 4 territory.

### Complexity / severity

- Complexity to fix: **small per function** (most are 1–2 extractions) — but the total is 202 sites.
- Severity: **medium** (per the locked T-055 severity mapping for CC 11–20).

### Related findings

- High-severity CC sites (10) at `FIND-RADON-001`.
- 541 rank-B "watch" sites dismissed under T-055 in `_dismissed.md` — recorded as documentation only, not in the FIND list.
- `status_routes.py` and `portfolio_valuation_readiness.py` also appear in `FIND-RADON-003` (high-severity maintainability).

## FIND-012 (was FIND-RADON-003) — High-severity maintainability hotspots (MI rank C, 9 modules)

- **Tool:** `radon 6.0.1`, command `radon mi -s apps packages`. Raw output `/tmp/radon-mi-baseline.txt` (T-055).
- **Pattern:** nine modules with maintainability index (MI) < 10 — Radon's rank C threshold. Six modules score MI = 0.00 (Radon's floor — typically reached by `wc -l > 1500` files with heavy comment density).
- **Severity mapping rationale:** the locked T-055 threshold maps MI rank `C` to **high**. MI is a composite of Halstead volume, cyclomatic complexity, and lines-of-code; rank C means a single-touch change is statistically very likely to introduce a defect.

### Inventory (file:line, MI score)

| Module | MI score |
|---|---|
| `apps/api/src/portfolio_outlook_api/status_routes.py:1` | 0.00 |
| `apps/api/src/portfolio_outlook_api/portfolio_valuation_readiness.py:1` | 0.75 |
| `apps/api/src/portfolio_outlook_api/research_sources.py:1` | 6.07 |
| `apps/api/tests/test_market_data_readiness_endpoint.py:1` | 0.00 |
| `apps/api/tests/test_ibkr_status_endpoint.py:1` | 7.03 |
| `apps/api/tests/test_research_source_archive_endpoints.py:1` | 5.20 |
| `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:1` | 0.00 |
| `packages/storage/tests/test_sql_repositories.py:1` | 0.00 |
| `packages/domain/src/portfolio_outlook_domain/settings.py:1` | 0.00 |

Note: Radon does not emit line-precise findings for MI; the `:1` anchor is the locked stable reference per the task spec.

### Why it matters (plain English)

- Five of nine are confirmed elsewhere as project-wide hotspots:
  - `status_routes.py` (4014 lines, 15 CC C+ sites in `FIND-RADON-002`, 1 CC E site in `FIND-RADON-001`) — the mixed-cluster API router (T-006 §5).
  - `portfolio_valuation_readiness.py` (916 lines, 1 CC F + 2 CC D + 1 CC C in production code; surfaced in T-006 §10 as the largest in-scope module).
  - `sql_repositories.py` (the central storage repository file; T-003 reality doc notes "53-migration linear chain"; mypy carries a file-level `disable-error-code="union-attr"` pragma per T-051).
  - `settings.py` (domain — the central settings/profile model file).
  - `research_sources.py` (already carries ruff `E501, I001` per-file-ignores per T-050 dismissal entry).
- Four are tests covering the above hotspots — their low MI is a reflection of the production-code surface they exercise.

### Fix approach

- **Module splitting** is the only reliable lever (helpers extraction alone does not lift MI rank for modules at MI = 0.00). Split `status_routes.py` into per-cluster routers (status_infra.py + status_ibkr.py + status_forecast.py + status_actions.py); split `portfolio_valuation_readiness.py` into builder + sub-readiness modules; split `sql_repositories.py` into per-aggregate repository files. T-006 (the reality doc) already documents the natural cluster boundaries for `status_routes.py`.
- **Out of scope for T-055.**

### Complexity / severity

- Complexity to fix: **large** — module splits touch import sites across many callers.
- Severity: **high** (per the locked T-055 severity mapping for MI rank C).

### Related findings

- `FIND-RADON-001` (high CC) names functions inside three of the nine modules.
- `FIND-RADON-002` (medium CC) lists 49 functions across these nine modules (the bulk of the count).

## FIND-013 (was FIND-RADON-004) — Medium-severity maintainability hotspots (MI rank B, 8 modules)

- **Tool:** `radon 6.0.1`, raw output `/tmp/radon-mi-baseline.txt` (T-055).
- **Pattern:** eight modules with MI 10 ≤ score < 20 — Radon's rank B threshold.
- **Severity mapping rationale:** the locked T-055 threshold maps MI rank `B` to **medium**. Rank B modules are large enough that touch-rate matters but the per-touch defect risk is materially lower than rank C.

### Inventory (file:line, MI score)

| Module | MI score |
|---|---|
| `apps/api/tests/test_ibkr_sync_endpoints.py:1` | 13.82 |
| `apps/api/tests/test_portfolio_valuation_readiness_endpoint.py:1` | 10.48 |
| `packages/storage/tests/test_alembic_skeleton.py:1` | 17.63 |
| `packages/domain/src/portfolio_outlook_domain/broker_reconciliation.py:1` | 18.08 |
| `packages/domain/src/portfolio_outlook_domain/suggestion_engine.py:1` | 18.62 |
| `packages/domain/src/portfolio_outlook_domain/storage.py:1` | 17.78 |
| `packages/domain/src/portfolio_outlook_domain/research_library.py:1` | 13.43 |
| `packages/domain/src/portfolio_outlook_domain/research_suggestions.py:1` | 13.54 |

### Fix approach

Same as `FIND-RADON-003`, but lower urgency. The five `packages/domain/` modules at MI 13–19 are pure dataclass + validator files — natural fix is splitting per-aggregate (`broker_reconciliation.py` → reconciliation + execution sub-files; `suggestion_engine.py` → engine + gate evaluation; `storage.py` → readiness + persistence-mode sub-files).

### Complexity / severity

- Complexity to fix: **medium** — domain splits are mostly mechanical.
- Severity: **medium** (per the locked T-055 severity mapping for MI rank B).

### Related findings

- `FIND-RADON-002` (medium CC) lists 8 functions inside these eight modules.
- T-052's `FIND-VULTURE-001` (in `research_suggestions.py`) is in one of these eight modules.

## FIND-014 (was FIND-TSC-001) — `ActionDraftGrid.test.tsx` `HAPPY` fixture drifts from the `ActionDraftResponse` type (TS2739; 3 missing Task-134 lifecycle fields)

- **Tool:** `tsc` from `typescript` (versioned in `apps/web/package.json`). Raw output `/tmp/tsc-baseline.log` (T-056).
- **Command:** `cd apps/web && npx tsc --noEmit` (exit code 1, 1 error line).
- **Error line (verbatim):**

  ```
  components/ActionDraftGrid.test.tsx(14,7): error TS2739: Type '{ action_draft_id: string; ...
    21 more ...; safe_for_submission: false; }' is missing the following properties from type
    'ActionDraftResponse': submission_block_reason, submission_started_at, terminal_state_at
  ```

- **Site:** `apps/web/components/ActionDraftGrid.test.tsx:14` — the `HAPPY: ActionDraftResponse = { … }` test fixture declaration.
- **Type source:** `apps/web/lib/apiClient.ts:926-962` — the `ActionDraftResponse` type. The three missing fields were appended at the bottom of the type under the "Task 134 lifecycle fields" comment (`apiClient.ts:958-961`):

  ```ts
  // Task 134 lifecycle fields.
  submission_block_reason: string | null;
  submission_started_at: string | null;
  terminal_state_at: string | null;
  ```

- **Why it matters (plain English):** `apiClient.ts:ActionDraftResponse` was extended with three lifecycle fields (Task 134) but the `HAPPY` test fixture in `ActionDraftGrid.test.tsx` was not updated. `next build` (which CI runs) only type-checks files in the production bundle — test files under `*.test.tsx` are excluded by `tsconfig.json`'s build config, so the drift never blocked merge. An explicit `tsc --noEmit` (this task) catches it.
- **Production impact:** **none**. `next build` continues to pass; the test compiles under `vitest` because vitest uses esbuild and is permissive about extra-property checks. The fixture renders correctly because `ActionDraftGrid` doesn't access the three missing fields. The risk is purely future-test-fragility: if `ActionDraftGrid` is later extended to render `submission_block_reason`, the test would not catch a missing fixture field because the existing assertion has already drifted.
- **Fix approach:** add the three fields to the fixture with `null` placeholders. One-line patch:

  ```ts
  const HAPPY: ActionDraftResponse = {
    // … existing fields …
    safe_for_submission: false,
    submission_block_reason: null,
    submission_started_at: null,
    terminal_state_at: null,
  };
  ```

- **Complexity:** **small** (3-line addition).
- **Severity:** **low** — per the locked T-056 severity mapping for `*.test.tsx` files. The bug is test-fixture drift, not a production defect; `next build` is unaffected.
- **Related findings:** none directly. The drift exists because the `apps/web` CI step runs `next build` rather than `tsc --noEmit`, which the T-056 baseline now makes visible. A Phase 4 CI brainstorm could decide to add an explicit `npm run typecheck` step that runs `tsc --noEmit` on the full tree.
