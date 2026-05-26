```yaml
id: T-005
title: Write reality docs for the API forecasting + actions clusters
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is two new files under `docs/reality/components/`; neither exists. The 31 source modules in `apps/api/src/portfolio_outlook_api/` covered by the two output docs (19 in the forecasting + market-data group, 12 in the actions + suggestions + watchlists group; ~12.7k lines total) are read by two parallel subagents.
- **Step 2 (one-line per touched file):** the two target files do not exist; each will hold the reality doc for one sub-cluster:
  - `api-forecasting-and-market-data.md` — forecast routes/sync + market-data adapter/readiness/runtime routes/sync + `eodhd_client` + `asset_master`/`asset_listings` + `universe_registry`/`universe_scan_sync` + `predictor_backtest_orchestrator` + `anthropic_ts_provider`/`ai_ts_provider` + `decision_package_routes`/`decision_package_sync` + `daily_briefing_sync` + `prediction_diary_sync` + `morning_chain` (19 modules)
  - `api-actions-suggestions-and-watchlists.md` — `action_draft`/`action_draft_submission`/`action_draft_sync` + `suggestion_sync` + `watchlist`/`watchlist_confirmation_routes` + `reconciliation`/`reconciliation_sync` + `paper_setup`/`paper_setup_persistence` + `trading_settings` + `research_sources` (12 modules)
- **Step 3 (one-line change):** write two cited reality docs covering routes, response models, storage write-paths, and state-machine touchpoints for the non-IBKR / non-infra portions of `apps/api`.
- **Step 4 (criteria measurable):** yes — seven acceptance criteria: both files exist; each lists modules; route catalogues with method + path + handler + file:line; response models referenced; action-draft state-machine touchpoints listed in the actions doc; Decimal-as-string boundary policy cited; no source modified.
- **Step 5 (out-of-scope does not block goal):** confirmed — IBKR cluster (T-004), infra+AI cluster (T-006), worker (T-007) are not in scope.

## Goal

Produce two reality docs covering the non-IBKR, non-infrastructure portions of `apps/api/`: forecasting/market-data routes and actions/suggestions/watchlists routes.

## Context

`depends_on:` —.

## Touch scope

Create:
- `docs/reality/components/api-forecasting-and-market-data.md`
- `docs/reality/components/api-actions-suggestions-and-watchlists.md`

Read: all listed source modules below (no modification).

## Acceptance criteria

- [ ] Both output files exist at the locked filenames.
- [ ] Each file lists its in-scope modules.
- [ ] Route catalogues per file: HTTP method + path + handler function + file:line.
- [ ] Pydantic response models documented per route (schema-level only, not field-by-field) with refs.
- [ ] State-machine touchpoints (which routes mutate which `action_drafts.status` transition) documented in the actions file.
- [ ] Decimal-as-string boundary policy documented with refs.
- [ ] No source modification.

## Out of scope

- IBKR cluster (T-004).
- Infrastructure / AI cluster (T-006).
- Worker (T-007).

## Verification

- Both files exist.
- Spot-check three random route entries to confirm refs resolve.

## Notes

Module groupings:
- `api-forecasting-and-market-data.md`: `forecast_routes`, `forecast_sync`, `market_data_*`, `eodhd_client`, `asset_master`, `asset_listings`, `universe_*`, `predictor_backtest_orchestrator`, `anthropic_ts_provider`, `ai_ts_provider`, `decision_package_*`, `daily_briefing_sync`, `prediction_diary_sync`, `morning_chain`.
- `api-actions-suggestions-and-watchlists.md`: `action_draft`, `action_draft_submission`, `action_draft_sync`, `suggestion_sync`, `watchlist`, `watchlist_confirmation_routes`, `reconciliation`, `reconciliation_sync`, `paper_setup`, `paper_setup_persistence`, `trading_settings`, `research_sources`.
