```yaml
id: T-005
title: Write reality docs for the API forecasting + actions clusters
phase: P1
status: locked
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

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
