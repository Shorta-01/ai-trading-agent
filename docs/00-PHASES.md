# Audit & Execution Workflow — Phase Plan

One-page map of the multi-phase audit and execution workflow. Each
phase populates specific directories; this file is the index from
phase → output location → status.

## Phase 0 — Scaffolding _(done)_

Set up directories, templates, configs, and CI tooling so later phases
have a consistent place to write into. No source-code analysis beyond
inventorying CI tools.

Outputs:
- All `docs/` audit directories created with READMEs and `.gitkeep`.
- `docs/tasks/queue.md`, `docs/tasks/_task-template.md`,
  `docs/tasks/_standing-prompt.md`, `docs/tasks/_audit-discipline.md`,
  `docs/tasks/_branch-protection-checklist.md`.
- `docs/decisions/decision-log.md`.
- `docs/code-health/` skeleton (`00`–`05`, `_dismissed.md`, `_tooling.md`).
- `docs/00-PHASES.md` (this file).
- `.github/workflows/code-health.yml` in report-only mode.
- Repo-root `pyproject.toml` for cross-cutting Python tool config.

## Phase 1 — Four-track analysis _(planned, awaiting execution)_

Four parallel tracks producing as-is documentation and a code-health
baseline. Each track writes into its own directory. The full charter
is in `docs/intent/_phase-1-charter.md`; the decision detail is in
`docs/decisions/0001-phase-1-charter.md`.

| Track | Description | Output directory |
|-------|-------------|------------------|
| 1a — Reality docs | What the system actually does today, derived from the code. | `docs/reality/functionality/`, `docs/reality/workflows/`, `docs/reality/components/` |
| 1b — Architecture review | Structural assessment of layering, boundaries, dependencies. | `docs/architecture-review/` |
| 1c — Gap analysis | Deltas between intended behaviour (`docs/intent/`, existing product docs, AGENTS guardrails) and reality. | `docs/gap-analysis/` |
| 1d — Code health | Baseline of code-health tool findings. | `docs/code-health/` |

Phase 1 also drafts `docs/intent/` files where needed so Phase 1c has
both sides of the comparison.

### Phase 1a — locked file plan

The locked plan for the three reality sub-directories. The plan is
the contract Phase 1a tasks deliver against; later phases reference
files by these exact names.

#### `docs/reality/components/` (25 files)

Grouped by package / app. Each file describes the public surface,
internal collaborators, persistent state, and noteworthy
implementation choices for the module group.

**Domain (4 files)**
1. `domain-primitives-and-money.md` — `primitives`, `costs`, `lots`, `identifiers`, `enums`, `instruments`, `term_deposits`. Low-level value types and quantity primitives.
2. `domain-portfolio-and-policy.md` — `portfolio`, `paper_setup`, `investment_policy`, `eligibility`, `approvals`, `capabilities`, `settings`, `market_calendar`, `market_data_foundation`, `audit`. The "what the system is for" types.
3. `domain-research-and-suggestions.md` — `suggestion_engine`, `suggestions`, `research`, `research_library`, `research_suggestions`, `quantitative_research`, `data_quality`, `data_sources`, `sources`. The research and decision-input vocabulary.
4. `domain-runtime-and-integration.md` — `runtime`, `scheduler`, `storage`, `broker_adapter`, `broker_reconciliation`, `ibkr`, `orders`, `execution`, `ledger`. The "how it runs and integrates" types.

**Portfolio (4 files)**
5. `portfolio-money-and-accounting.md` — `money`, `accounting`, `lots`, `snapshot`, `performance`, `valuation_conversion_totals`, `valuation_cost_basis_pl`, `term_deposits`, `ledger_services`. EUR conversion, cost basis, P&L.
6. `portfolio-predictors.md` — `baseline_forecast`, `baseline_label_translator`, `_predictor_math`, `predictor_protocol`, `predictor_backtester`, `predictor_feedback`, `gbm_predictor`, `momentum_predictor`, `mean_reversion_predictor`, `qvm_factor_predictor`, `ai_ts_predictor`, `ensemble_combiner`, `kelly_sizing`, `prediction_diary_eval`. All forecasting maths.
7. `portfolio-guards-and-state-machines.md` — `approval_guards`, `suggestion_guards`, `suggestion_engine_guards`, `execution_guards`, `storage_guards`, `paper_setup_guards`, `ai_explanation_guards`, `broker_reconciliation_guards`, `action_draft_safety`, `action_draft_state_machine`, `errors`. Safety-recheck and state-machine logic.
8. `portfolio-daily-briefing-and-tax.md` — `daily_briefing`, `research_evidence_summary`, `belgian_tax`, `capabilities`. Briefing and tax computation.

**Storage (1 file)**
9. `storage-package-and-migrations.md` — `sql_repositories`, `repository_contracts`, `connection_provider`, `migration_readiness`, `settings`, `metadata`, `alembic_helpers`, and the 54-migration Alembic chain (overview, not per-migration deep dive).

**API (6 files)**
10. `api-ibkr-connection-and-status.md` — `ibkr_connection_*`, `ibkr_status`, `ibkr_session_*`, `ibkr_tws_*`, `ibkr_ibapi_client_facade`, `ibkr_contracts`.
11. `api-ibkr-sync-and-snapshot.md` — `ibkr_sync*`, `ibkr_account_snapshot*`, `ibkr_market_data`, `ibkr_ibapi_sync_client`, `ibkr_ibapi_account_snapshot_client`.
12. `api-ibkr-submission-and-watchlists.md` — `ibkr_submission`, `ibkr_order_submission_factory`, `ibkr_ibapi_order_submission_client`, `ibkr_ibapi_manual_status_client`, `ibkr_watchlists`.
13. `api-forecasting-and-market-data.md` — `forecast_*`, `market_data_*`, `eodhd_client`, `asset_master`, `asset_listings`, `universe_*`, `predictor_backtest_orchestrator`, `anthropic_ts_provider`, `ai_ts_provider`, `decision_package_*`, `daily_briefing_sync`, `prediction_diary_sync`, `morning_chain`.
14. `api-actions-suggestions-and-watchlists.md` — `action_draft*`, `action_draft_submission`, `action_draft_sync`, `suggestion_sync`, `watchlist*`, `watchlist_confirmation_routes`, `reconciliation*`, `reconciliation_sync`, `paper_setup*`, `trading_settings`, `research_sources`.
15. `api-infrastructure-and-ai.md` — `main`, `config`, `health`, `status_*`, `scheduler*`, `system_event_*`, `storage_status`, `online_storage_status`, `release_readiness`, `request_audit`, `portfolio_valuation_readiness`, `anthropic_explanation_provider`, `ai_explanation_*`, `claude_ai_budget`.

**Worker (3 files)**
16. `worker-orchestration-and-scheduling.md` — `main`, `config`, `orchestrator`, `scheduler`, `single_flight_lock`, `storage_readiness`, `health`, `ibkr_gateway`, `starter_watchlist`.
17. `worker-forecasting-and-decision-package.md` — `forecasting/*` (5 files), `decision_package/*` (4 files), `market_data_step`, `providers/eodhd`.
18. `worker-actions-and-reconciliation.md` — `action_draft/*` (3 files), `ibkr_submission/*` (6 files), `ibkr_reconciliation/*` (5 files).

**Frontend (4 files)**
19. `web-pages.md` — all 16 Next.js `page.tsx` files plus `layout.tsx`.
20. `web-components-status-and-shared.md` — shared UI / status components (`StatusCard`, `EmptyState`, `HelpText`, `HelpTooltip`, `IconButtonWithTooltip`, `SyncStatusBadge`, `AccountModeBadge`, `SchedulerStatusBadge`, `ReconciliationStatusWidget`, `ColdStartBanner`, etc.).
21. `web-components-feature-grids.md` — domain-specific grids and forms (`ActionDraftGrid`, `IbkrSubmissionGrids`, `PortefeuilleRealtimeSection`, `ValuationTraceDetails`, `ForecastExplanationPanel`, `ForecastDaySummaryWidget`, `DecisionPackageDetail`, `SubmissionLifecycleDrawer`, `VolglijstColdStartFlow`, etc.).
22. `web-api-client-and-text.md` — `lib/apiClient.ts`, `lib/uiText.ts`, `next.config.ts`, `playwright.config.ts`, `vitest.config.ts`, `eslint.config.mjs`.

**Infra (2 files)**
23. `infra-docker-and-compose.md` — `apps/{api,web,worker}/Dockerfile`, `infra/docker/docker-compose.yml`, `.env.example`.
24. `build-ci-and-scripts.md` — `Makefile`, repo-root `pyproject.toml`, `.github/workflows/*`, `scripts/*`.

**Stubs (1 file)**
25. `stub-packages.md` — the six README-only packages `packages/{ai,analytics,audit,data_providers,risk,tax}` (currently containing no source code).

#### `docs/reality/functionality/` (19 files)

One file per major end-to-end functionality. Each file walks the
behaviour from trigger → modules touched → side effects → outputs,
citing concrete code references.

1. `morning-chain-orchestration.md` — Worker `orchestrator.py` + `morning_chain` API.
2. `cold-start-seeding-and-watchlist-confirmation.md` — `starter_watchlist` + `watchlist_confirmation_routes`.
3. `ibkr-readonly-sync-positions-cash.md` — TWS connection + position/cash/open-orders/executions sync.
4. `market-data-pipeline.md` — research data (EODHD EOD + intraday + fundamentals + earnings calendar) and execution data (IBKR live quotes for order ticket construction), including how the two interact and freshness detection.
5. `forecast-generation-and-labelling.md` — Historical bootstrap + label translator + per-asset universe.
6. `forecast-calibration-and-prediction-diary.md` — 06:00 calibration + per-predictor outcomes + diary.
7. `decision-package-composition.md` — Gate evaluation + Dutch explanation + hash chain.
8. `action-draft-composition-and-approval.md` — Composer + Te keuren tab + approve/edit/dismiss/delete.
9. `ibkr-order-submission-lifecycle.md` — Submission sweep + safety recheck + place_order + lifecycle handler + cancel.
10. `ibkr-reconciliation-passes-a-b-c.md` — Orphaned execution + stale in-flight + 24h timeout escalation.
11. `portfolio-valuation-and-cost-basis.md` — Positions × prices × FX → EUR + cost-basis P&L.
12. `belgian-tax-computation.md` — `portfolio.belgian_tax` + frontend display.
13. `ai-explanation-and-budget.md` — Anthropic Claude explanation provider + monthly budget cap.
14. `predictor-backtest-and-leaderboard.md` — `predictor_backtester` + auto-weight ensemble + `/predictor/leaderboard`.
15. `hourly-decision-refresh.md` (T-011b) — Lighter hourly run that keeps the action list current between 07:00 evaluations.
16. `dashboard-composition.md` (T-011c) — The dashboard contract as a whole: portfolio area, watchlist area, actions area (suggested + Open orders grids), system-health line, mode badge.
17. `data-maturation-and-confidence-buildup.md` (T-012b) — How suggestions evolve from day 1 (low data, low confidence) to mature operation; gap entry if no explicit maturation logic exists.
18. `prediction-track-record-screen.md` (T-016b) — Screen spec for filters by predictor / asset / window, aggregate views, drill-downs; current implementation status.
19. `performance-review.md` (T-021b) — Screen spec for time-weighted return vs benchmark, drawdown, volatility / risk-budget usage, exposure breakdown, portfolio chart, weekly/monthly views; current implementation status.

#### `docs/reality/workflows/` (11 files)

One file per workflow, `user-` prefix for interactive flows,
`system-` prefix for scheduler-driven flows.

**User workflows (6 files)**
1. `user-confirm-starter-watchlist.md` — User types BEVESTIG on cold-start.
2. `user-approve-action-draft.md` — User reviews and approves a draft in Te keuren.
3. `user-cancel-submitted-order.md` — User cancels an in-flight submission.
4. `user-acknowledge-manual-review.md` — Admin acknowledges a reconciliation manual-review row.
5. `user-edit-trading-settings.md` — User changes settings in Instellingen.
6. `user-review-decision-package-detail.md` — User opens a Decision Package detail page.

**System workflows (5 files)**
7. `system-morning-pre-briefing-06-00.md` — APScheduler 06:00 fire → calibration.
8. `system-morning-briefing-07-00.md` — APScheduler 07:00 fire → cold-start / market data / forecast / decision package.
9. `system-hourly-delta-runs.md` — APScheduler 08:00–21:00 hourly fires.
10. `system-ibkr-submission-sweep.md` — APScheduler-driven submission sweep tick.
11. `system-ibkr-reconciliation-tick.md` — APScheduler-driven reconciliation tick.

### Phase 1 task index

Total: **66 tasks** (T-001 … T-060 plus the six 2026-05-26 functional-review additions: T-061 and T-011b / T-011c / T-012b / T-016b / T-021b). All start at `status: locked`; the standing prompt picks them up in numbered order respecting the declared dependencies.

| Range | Track | Tasks | Outputs |
|-------|-------|-------|---------|
| T-001 … T-010 | 1a — Reality components | 10 | 25 files in `docs/reality/components/` |
| T-061 | 1a — Reality components (functional-review addition) | 1 | 1 file in `docs/reality/components/` (settings + credentials infrastructure) |
| T-011 … T-024 | 1a — Reality functionality | 14 | 14 files in `docs/reality/functionality/` |
| T-011b, T-011c, T-012b, T-016b, T-021b | 1a — Reality functionality (functional-review additions) | 5 | 5 files in `docs/reality/functionality/` (`hourly-decision-refresh.md`, `dashboard-composition.md`, `data-maturation-and-confidence-buildup.md`, `prediction-track-record-screen.md`, `performance-review.md`) |
| T-025 … T-035 | 1a — Reality workflows | 11 | 11 files in `docs/reality/workflows/` |
| T-036 … T-043 | 1b — Architecture review | 8 | 8 files in `docs/architecture-review/` (00-summary written last) |
| T-044 … T-049 | 1c — Gap analysis | 6 | 6 files in `docs/gap-analysis/` (00-summary written last) |
| T-050 … T-058 | 1d — Code-health per-tool baselines | 9 | FIND-XXX entries in `01`–`04` per-category files |
| T-059 | 1d — Findings consolidation | 1 | `docs/code-health/00-findings.md` master list |
| T-060 | 1d — Batching proposal | 1 | `docs/code-health/05-fix-batches.md` proposal |

Full task rows live in `docs/tasks/queue.md` under section "Locked",
grouped by track. Larger tasks (component groups, per-tool baselines,
consolidation, batching) have working files at
`docs/tasks/T-NNN-<slug>.md`.

## Phase 2 — Plain-English functional docs

User-facing, jargon-free descriptions of what the product does and how
to use it. Distinct from reality docs (which describe code).

Output directory: `docs/functional/`.

## Phase 3 — Improvement memo

Synthesise Phases 1 and 2 into a prioritised memo: what is most worth
changing, in what order, with what trade-offs. The memo is the input
to Phase 4 brainstorming.

Output: a single dated memo file (location decided in Phase 3 — likely
`docs/improvement-memo-YYYY-MM-DD.md`).

## Phase 4 — Brainstorm → tasks → PRs → merges

Topic-by-topic working loop. For each topic:

1. Brainstorm (record outcomes in `docs/decisions/NNNN-<slug>.md` plus
   a row in `docs/decisions/decision-log.md`).
2. Break into tasks; add rows to `docs/tasks/queue.md` and create
   working files at `docs/tasks/T-NNN-<slug>.md` for non-trivial tasks.
3. Execute tasks one PR at a time, using
   `docs/tasks/_audit-discipline.md` and the PR template.
4. Merge; update `docs/reality/` and `docs/functional/` as behaviour
   changes.

This is where Claude becomes the executor. Standing prompt lives at
`docs/tasks/_standing-prompt.md`.

## Phase 5 — Recurring code-health runs

After Phase 1d baselines, promote code-health gates one tool at a time
(see `docs/code-health/_tooling.md`) and run periodic full sweeps. Each
sweep writes a dated report into `docs/code-health/` (e.g.
`YYYY-MM-DD-sweep.md`) and produces tasks back into `docs/tasks/queue.md`.

## Directory → phase quick reference

| Directory | Populated by |
|-----------|--------------|
| `docs/reality/{functionality,workflows,components}/` | Phase 1a |
| `docs/architecture-review/` | Phase 1b |
| `docs/intent/` | Phase 1 (drafted) → Phase 3 (refined) |
| `docs/gap-analysis/` | Phase 1c |
| `docs/code-health/` | Phase 1d, then Phase 5 |
| `docs/functional/` | Phase 2 |
| `docs/decisions/` | Phase 4 onward |
| `docs/tasks/` | Phase 4 onward |

## Legacy artifacts

`docs/product/task-queue.md` and `docs/product/task-history.md`
predate this workflow. They are **FROZEN** as of 2026-05-26 — no new
entries are added to either file. All new audit-workflow tasks live
in `docs/tasks/queue.md` exclusively. The legacy files remain
readable for historical reference and feed into Phase 1 as input to
the reality and intent corpora, but they are not part of the
go-forward task pipeline. The full reconciliation note is at
`docs/product/_RECONCILIATION.md`.
