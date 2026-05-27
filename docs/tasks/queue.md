# Audit Workflow Task Queue

The canonical list of audit-workflow tasks. New rows are append-only;
existing rows are updated only to change `status` and append `pr_url`.
The full schema for each row lives in `docs/tasks/_task-template.md`,
and the rules for picking the next task live in
`docs/tasks/_standing-prompt.md`.

Each row identifies a task by `T-NNN`. Larger tasks have a working
file at `docs/tasks/T-NNN-<slug>.md`; smaller ones are tracked here
alone.

Field shorthand inside each row: `P` = phase; `src` = source; `sev` =
severity; `dep` = depends_on. Phase 1 brainstorm tasks all share
`intent_ref: docs/intent/_phase-1-charter.md` and
`decision_ref: docs/decisions/0001-phase-1-charter.md` — those are
written here once, not repeated per row.

## In Progress

- **T-027** — `user-cancel-submitted-order.md` user-action workflow doc (Annuleer ritual on /ibkr-acties Actief tab: window.confirm → POST /cancel-submitted → pending_cancellation status + lifecycle audit row → worker never picks it up; T-019 §4.8 cancel-worker gap re-surfaced from user-action angle). *Branch:* `task/T-027-reality-user-cancel-submitted-order`.

## Locked

All sixty Phase 1 tasks below share these defaults unless overridden:

- `phase: P1`
- `source: brainstorm`
- `owner: claude`
- `created: 2026-05-26`
- `intent_ref: docs/intent/_phase-1-charter.md`
- `decision_ref: docs/decisions/0001-phase-1-charter.md`
- `pr_url: —`

### Track 1a — Reality components (T-001 … T-010)

Each task inspects a coherent module group and writes one or more
files under `docs/reality/components/`. The standing prompt enforces
that these complete before Track 1a functionality / workflows or
Tracks 1b / 1c may pick up.

- **T-001** — Write reality docs for the `packages/domain` package.  
  *dep:* —. *Working file:* `docs/tasks/T-001-reality-domain-package.md`. Produces 4 files.
- **T-002** — Write reality docs for the `packages/portfolio` package.  
  *dep:* —. *Working file:* `docs/tasks/T-002-reality-portfolio-package.md`. Produces 4 files.
- **T-003** — Write reality doc for the `packages/storage` package and its Alembic migration chain.  
  *dep:* —. *Working file:* `docs/tasks/T-003-reality-storage-package.md`. Produces 1 file.
- **T-004** — Write reality docs for the API IBKR cluster (connection / sync / submission).  
  *dep:* —. *Working file:* `docs/tasks/T-004-reality-api-ibkr-cluster.md`. Produces 3 files.
- **T-005** — Write reality docs for the API forecasting, actions, and suggestions clusters.  
  *dep:* —. *Working file:* `docs/tasks/T-005-reality-api-forecasting-and-actions.md`. Produces 2 files.
- **T-006** — Write reality doc for the API infrastructure + AI explanation cluster.  
  *dep:* —. *Working file:* `docs/tasks/T-006-reality-api-infrastructure-and-ai.md`. Produces 1 file.
- **T-007** — Write reality docs for the worker (orchestration, forecasting/decision-package, actions/reconciliation).  
  *dep:* —. *Working file:* `docs/tasks/T-007-reality-worker.md`. Produces 3 files.
- **T-008** — Write reality docs for the frontend (pages, shared components, feature grids).  
  *dep:* —. *Working file:* `docs/tasks/T-008-reality-frontend-pages-and-components.md`. Produces 3 files.
- **T-009** — Write reality docs for the frontend client/text layer and the infra/build layer.  
  *dep:* —. *Working file:* `docs/tasks/T-009-reality-frontend-client-and-infra-build.md`. Produces 3 files.
- **T-010** — Write reality doc for the six README-only stub packages.  
  *dep:* —. *Working file:* `docs/tasks/T-010-reality-stub-packages.md`. Produces 1 file.

### Track 1a — Reality functionality (T-011 … T-024)

One task per major end-to-end functionality. Each produces one file
in `docs/reality/functionality/`. All depend on the relevant
component reality docs (Track 1a components must be `pr-merged`
first).

- **T-011** — Write `morning-chain-orchestration.md`. *dep:* T-007.
- **T-012** — Write `cold-start-seeding-and-watchlist-confirmation.md`. *dep:* T-005, T-007.
- **T-013** — Write `ibkr-readonly-sync-positions-cash.md`. *dep:* T-004, T-007.
- **T-014** — Write `market-data-pipeline.md`. *dep:* T-003, T-005, T-007. Covers both research data (EODHD EOD + intraday + fundamentals + earnings calendar) and execution data (IBKR live quotes for order ticket construction), how the two interact, freshness detection.
- **T-015** — Write `forecast-generation-and-labelling.md`. *dep:* T-002, T-007.
- **T-016** — Write `forecast-calibration-and-prediction-diary.md`. *dep:* T-002, T-005, T-007.
- **T-017** — Write `decision-package-composition.md`. *dep:* T-002, T-007.
- **T-018** — Write `action-draft-composition-and-approval.md`. *dep:* T-002, T-005, T-007, T-008.
- **T-019** — Write `ibkr-order-submission-lifecycle.md`. *dep:* T-004, T-007.
- **T-020** — Write `ibkr-reconciliation-passes-a-b-c.md`. *dep:* T-004, T-007.
- **T-021** — Write `portfolio-valuation-and-cost-basis.md`. *dep:* T-002, T-005.
- **T-022** — Write `belgian-tax-computation.md`. *dep:* T-002, T-005.
- **T-023** — Write `ai-explanation-and-budget.md`. *dep:* T-002, T-006.
- **T-024** — Write `predictor-backtest-and-leaderboard.md`. *dep:* T-002, T-005.

### Track 1a — Reality workflows (T-025 … T-035)

One task per workflow. Each produces one file in
`docs/reality/workflows/`. All depend on the relevant functionality
files (Track 1a functionality must be `pr-merged` first).

- **T-025** — Write `user-confirm-starter-watchlist.md`. *dep:* T-012.
- **T-026** — Write `user-approve-action-draft.md`. *dep:* T-018.
- **T-027** — Write `user-cancel-submitted-order.md`. *dep:* T-019.
- **T-028** — Write `user-acknowledge-manual-review.md`. *dep:* T-020.
- **T-029** — Write `user-edit-trading-settings.md`. *dep:* T-006.
- **T-030** — Write `user-review-decision-package-detail.md`. *dep:* T-017.
- **T-031** — Write `system-morning-pre-briefing-06-00.md`. *dep:* T-011, T-016.
- **T-032** — Write `system-morning-briefing-07-00.md`. *dep:* T-011, T-015, T-017.
- **T-033** — Write `system-hourly-delta-runs.md`. *dep:* T-011.
- **T-034** — Write `system-ibkr-submission-sweep.md`. *dep:* T-019.
- **T-035** — Write `system-ibkr-reconciliation-tick.md`. *dep:* T-020.

### Track 1b — Architecture review (T-036 … T-043)

Verdict-driven assessment. Each task produces one file in
`docs/architecture-review/`. Every architectural choice gets:
current implementation (with file refs), state-of-the-art
alternative with named patterns, verdict
(`state-of-the-art` / `acceptable` / `outdated` / `risky`),
performance implication, concrete improvement (when not
state-of-the-art). All depend on Track 1a components being merged.
The `00-summary.md` task is written LAST and depends on the other
seven.

- **T-036** — Write `01-monorepo-structure.md`. *dep:* T-001 … T-010.
- **T-037** — Write `02-python-stack.md`. *dep:* T-001 … T-010.
- **T-038** — Write `03-frontend-stack.md`. *dep:* T-001 … T-010.
- **T-039** — Write `04-data-and-storage.md`. *dep:* T-001 … T-010.
- **T-040** — Write `05-testing-and-ci.md`. *dep:* T-001 … T-010.
- **T-041** — Write `06-performance-and-scale.md`. *dep:* T-001 … T-010.
- **T-042** — Write `07-security-observability-ops.md`. *dep:* T-001 … T-010.
- **T-043** — Write `00-summary.md`. *dep:* T-036 … T-042.

### Track 1c — Gap analysis (T-044 … T-049)

Each gap recorded with: name, why it matters in plain English, where
it would live in current architecture, effort estimate
(small/medium/large), dependency, MoSCoW priority. All depend on
Track 1a components being merged. The `00-summary.md` task is
written LAST.

- **T-044** — Write `01-missing-features.md`. *dep:* T-001 … T-010.
- **T-045** — Write `02-incomplete-implementations.md`. *dep:* T-001 … T-010.
- **T-046** — Write `03-quant-and-forecasting-gaps.md`. *dep:* T-001 … T-010.
- **T-047** — Write `04-ai-integration-gaps.md`. *dep:* T-001 … T-010.
- **T-048** — Write `05-operational-gaps.md`. *dep:* T-001 … T-010.
- **T-049** — Write `00-summary.md`. *dep:* T-044 … T-048.

### Track 1d — Code-health baseline (T-050 … T-060)

Per-tool baselines (T-050 … T-058) have no dependencies and can run
in any order. Each runs its tool against the full repo with current
config, captures raw output, and either writes FIND-XXX entries into
the appropriate per-category file (`01`–`04`) under
`docs/code-health/`, or records the result in `_dismissed.md` with a
one-line reason.

Consolidation (T-059) depends on all per-tool baselines. Batching
(T-060) depends on consolidation.

- **T-050** — Run `ruff` baseline and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-050-codehealth-ruff-baseline.md`.
- **T-051** — Run `mypy --strict` baseline and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-051-codehealth-mypy-baseline.md`.
- **T-052** — Run `vulture` baseline (dead Python code) and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-052-codehealth-vulture-baseline.md`.
- **T-053** — Run `bandit` baseline (Python security smells) and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-053-codehealth-bandit-baseline.md`.
- **T-054** — Run `pip-audit` baseline (Python dep CVEs) and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-054-codehealth-pip-audit-baseline.md`.
- **T-055** — Run `radon` baseline (complexity + maintainability) and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-055-codehealth-radon-baseline.md`.
- **T-056** — Run `tsc --noEmit` baseline and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-056-codehealth-tsc-baseline.md`.
- **T-057** — Run `knip` + `ts-prune` baseline (unused TS exports) and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-057-codehealth-knip-tsprune-baseline.md`.
- **T-058** — Run `npm audit` baseline (JS dep CVEs) and emit FIND entries.  
  *dep:* —. *Working file:* `docs/tasks/T-058-codehealth-npm-audit-baseline.md`.
- **T-059** — Consolidate all FIND entries into `docs/code-health/00-findings.md`.  
  *dep:* T-050 … T-058. *Working file:* `docs/tasks/T-059-codehealth-findings-consolidation.md`.
- **T-060** — Produce batching proposal in `docs/code-health/05-fix-batches.md`.  
  *dep:* T-059. *Working file:* `docs/tasks/T-060-codehealth-batching-proposal.md`.

### Functional-review additions (carry-forward of 2026-05-26 T-011…T-024 review)

Six tasks added 2026-05-26 to cover gaps surfaced during the functional review. All share the defaults at the top of this section.

- **T-061** — Write reality doc for settings and credentials management infrastructure. *dep:* —. *Working file:* `docs/tasks/T-061-reality-settings-and-credentials.md`. Scope: document the existing settings/secrets infrastructure across `packages/domain/.../settings.py`, `claude_ai_budget.py`, `paper_setup.py`, and any `.env` handling. Map to intent in `docs/intent/settings-and-credentials.md`. Produces 1 file under `docs/reality/components/` (location chosen during the task).
- **T-011b** — Write reality doc for `hourly-decision-refresh.md`. *dep:* T-007. Documents the lighter hourly run that keeps the action list current between 07:00 evaluations. Produces 1 file in `docs/reality/functionality/`.
- **T-011c** — Write reality doc for `dashboard-composition.md`. *dep:* T-008. Documents what the dashboard assembles (portfolio area, watchlist area, actions area, system-health line, mode badge) — the dashboard contract as a whole, distinct from the frontend component reality (T-008). Produces 1 file in `docs/reality/functionality/`.
- **T-012b** — Write reality doc for `data-maturation-and-confidence-buildup.md`. *dep:* T-005, T-007. Documents (or explicitly notes as gap) how the system's suggestions evolve from day 1 (low data, low confidence) to mature operation. If no explicit maturation logic exists, the file says so and the finding becomes a Phase 1c gap entry. Produces 1 file in `docs/reality/functionality/`.
- **T-016b** — Write reality doc for `prediction-track-record-screen.md`. *dep:* T-008, T-016. Documents the screen specification (filters by predictor / asset / window, aggregate views, drill-downs) and current implementation status. Produces 1 file in `docs/reality/functionality/`.
- **T-021b** — Write reality doc for `performance-review.md`. *dep:* T-008, T-021. Documents the performance review screen spec (time-weighted return vs benchmark, drawdown, volatility / risk-budget usage, exposure breakdown, portfolio chart, weekly/monthly views) and current implementation status. Produces 1 file in `docs/reality/functionality/`.

## Blocked

_None._

## CI-Failing

_None._

## Done

- **T-001** — Reality docs for `packages/domain` (4 files, 35 modules cited). PR: https://github.com/Shorta-01/ai-trading-agent/pull/434 — merged 2026-05-26.
- **T-050** — `ruff` baseline (0 findings; per-file-ignores + noqa inventory in `_dismissed.md`). PR: https://github.com/Shorta-01/ai-trading-agent/pull/435 — merged 2026-05-26.
- **T-002** — Reality docs for `packages/portfolio` (4 files, 38 modules cited; Kelly + A-K guard observations in Open Questions). PR: https://github.com/Shorta-01/ai-trading-agent/pull/436 — merged 2026-05-26.
- **T-051** — `mypy --strict` baseline (0 errors across 198 source files; ignore_missing_imports + type:ignore inventory in `_dismissed.md`). PR: https://github.com/Shorta-01/ai-trading-agent/pull/437 — merged 2026-05-26.
- **T-003** — Reality doc for `packages/storage` + Alembic chain (1 file; 8 modules + 53-migration overview cited; tri-defense safety-boolean + per-asset hash-chain patterns surfaced). PR: https://github.com/Shorta-01/ai-trading-agent/pull/438 — merged 2026-05-26.
- **T-052** — `vulture` baseline (1 FIND-VULTURE-001 for the `if False else` ternary already flagged by T-002; 15 framework/Protocol/backward-compat dismissals). PR: https://github.com/Shorta-01/ai-trading-agent/pull/439 — merged 2026-05-26.
- **T-004** — Reality docs for the API IBKR cluster (3 files; 26 modules cited; safety-boundary verified — one `placeOrder` call site at `ibkr_ibapi_order_submission_client.py:525`, zero `cancelOrder` anywhere in the API; two state-vocabulary islands surfaced). PR: https://github.com/Shorta-01/ai-trading-agent/pull/440 — merged 2026-05-26.
- **T-053** — `bandit` baseline (1 FIND-BANDIT-001 for the B101 assert-for-mypy-narrowing cluster across 20 sites; 20 dismissed: enum value / kwarg false positives + documented boundary catches + config-derived URL). PR: https://github.com/Shorta-01/ai-trading-agent/pull/441 — merged 2026-05-26.
- **T-005** — Reality docs for the API forecasting + actions clusters (2 files; 31 modules, 72 routes cited; storage write-path map + state-machine touchpoints; AI scope: anthropic_ts_provider Case B, ai_ts_provider stub Case A). PR: https://github.com/Shorta-01/ai-trading-agent/pull/442 — merged 2026-05-26.
- **T-054** — `pip-audit` baseline (1 HIGH FIND-PIPAUDIT-001 for fastapi==0.136.3 MAL-2026-4750; 4 pip CVEs dismissed as build-time-only; 5 local-package skips for accounting). PR: https://github.com/Shorta-01/ai-trading-agent/pull/443 — merged 2026-05-26.
- **T-006** — Reality doc for the API infrastructure + AI cluster (1 file; 20 modules ~8985 LoC cited; 15 `include_router` registrations + 20 release-readiness blocker codes + Anthropic Claude provider call shape + monthly EUR budget cap + Case C AI classification documented). PR: https://github.com/Shorta-01/ai-trading-agent/pull/444 — merged 2026-05-26.
- **T-055** — `radon` baseline (4 FINDs: 10 high-CC + 202 medium-CC + 9 high-MI + 8 medium-MI; 541 rank-B "watch" entries dismissed per locked threshold; hottest module status_routes.py — 14 CC C+ + 20 CC B + MI 0.00). PR: https://github.com/Shorta-01/ai-trading-agent/pull/445 — merged 2026-05-26.
- **T-007** — Reality docs for the worker (3 files; 30 non-`__init__` source files / ~8871 LoC cited; 3 intent-vs-reality gaps surfaced — 1-of-7 predictors shipped, 6 labels not 8, place_order authority split across API+worker). PR: https://github.com/Shorta-01/ai-trading-agent/pull/446 — merged 2026-05-26.
- **T-056** — `tsc --noEmit` baseline on `apps/web` (1 LOW `FIND-TSC-001` for `ActionDraftGrid.test.tsx:14` test-fixture drift; production build unaffected since `next build` excludes `*.test.tsx`). PR: https://github.com/Shorta-01/ai-trading-agent/pull/447 — merged 2026-05-26.
- **T-008** — Reality docs for the frontend (3 files; 16 pages + 30 non-test components / ~6493 LoC cited; Dutch UI invariant verified, client-first vs server-first noted, 9 Decimal-as-string display-rounding sites flagged). PR: https://github.com/Shorta-01/ai-trading-agent/pull/448 — merged 2026-05-26.
- **T-057** — `knip` + `ts-prune` baseline (7 LOW dead-code FINDs: 3 dual-source unused + 4 knip-only; 24 unused types in apiClient.ts as Phase-4 pruning candidates; 81 ts-prune over-reports dismissed in 3 categories). PR: https://github.com/Shorta-01/ai-trading-agent/pull/449 — merged 2026-05-26.
- **T-009** — Reality docs for web client/text + infra/docker + build/CI/scripts (3 files; ~3 kLoC + 2 intent docs cited; MAJOR Phase 1c gap surfaced — `.env.example` bare keys silently dropped by Pydantic `extra="ignore"`; T-057's `eslint-config-next` false positive corrected). PR: https://github.com/Shorta-01/ai-trading-agent/pull/450 — merged 2026-05-26.
- **T-058** — `npm audit` baseline (4 FINDs: 1 HIGH next umbrella with 22 GHSAs + 1 MEDIUM postcss prod + 2 LOW dev chains; 9 packages / 26 advisories covered; 0 dismissals; T-008 + T-009 cross-ref shows most next exposure paths latent — no middleware, no `next/image`, no Server Actions). PR: https://github.com/Shorta-01/ai-trading-agent/pull/451 — merged 2026-05-26.
- **T-010** — Reality doc for 6 README-only stub packages (`ai`, `analytics`, `audit`, `data_providers`, `risk`, `tax`); each mapped to actual implementation locations; no "fully unimplemented" bucket; named-stub-without-source pattern recorded as architectural signal). PR: https://github.com/Shorta-01/ai-trading-agent/pull/452 — merged 2026-05-26.
- **T-059** — Consolidate 19 FINDs into master `docs/code-health/00-findings.md` (re-keyed to FIND-001..019 with per-tool IDs preserved inline; severity reconciliation rule documented; 3 totals blocks; discovery→master mapping table; wholesale-dismissal pattern map appended to `_dismissed.md`; 4 HIGH-severity FINDs identified as Phase 4 batching candidates). PR: https://github.com/Shorta-01/ai-trading-agent/pull/453 — merged 2026-05-26.
- **T-011** — `morning-chain-orchestration.md` first Track 1a workflow doc (281 lines; synthesis of T-005/T-006/T-007 covering 06:00 pre_briefing + 07:00 morning_briefing end-to-end; 6 mode_detected modes + 5 step gates documented; explicit out-of-scope for action drafts/submission/reconciliation). PR: https://github.com/Shorta-01/ai-trading-agent/pull/454 — merged 2026-05-26.
- **T-060** — Batching proposal `05-fix-batches.md` grouping the 19 master FINDs from T-059 into 15 batches (4 high solo + 3 medium solo + 8 low — 3 bundled by same file+category; FIND→BATCH coverage proof table; 3 false-positive annotations preserved; no queue rows added per spec). PR: https://github.com/Shorta-01/ai-trading-agent/pull/455 — merged 2026-05-26.
- **T-012** — `cold-start-seeding-and-watchlist-confirmation.md` Track 1a workflow doc (383 lines; synthesis of T-005/T-007/T-008/T-009; 12-row v1 starter set + 4-table write pattern + BEVESTIG confirmation + 3-step mode_detected sequence documented). PR: https://github.com/Shorta-01/ai-trading-agent/pull/456 — merged 2026-05-26.
- **T-061** — Settings + credentials infrastructure reality doc (336 lines; 5-category intent mapping; 8 secret-read sites + 153 DB-URL sites inventoried; 11 Phase 1c gaps surfaced — Kelly 0.5-vs-0.25 collision re-confirmed, OpenAI vocab-only, Anthropic SDK auto-reads `ANTHROPIC_API_KEY`, PAPER→REAL architecturally forbidden at 3 layers). PR: https://github.com/Shorta-01/ai-trading-agent/pull/457 — merged 2026-05-26.
- **T-013** — `ibkr-readonly-sync-positions-cash.md` Track 1a workflow doc (295 lines; synthesis of T-004/T-007/T-008/T-009; 9-step connect lifecycle with tier-two paper-account guard; 5 storage tables; 12 apiClient methods; 30s polling; 8 Phase 1c surface items — sync trigger is manual-only). PR: https://github.com/Shorta-01/ai-trading-agent/pull/458 — merged 2026-05-26.
- **T-014** — `market-data-pipeline.md` Track 1a workflow doc (360 lines; two paths — EODHD research + IBKR execution; convergence at `market_data_latest_snapshots`; 15/30min freshness policy + 5-state enum + price-basis fallback; 8 Phase 1c surface items incl. ADR-0003 "All-In-One" gap re-confirmed). PR: https://github.com/Shorta-01/ai-trading-agent/pull/459 — merged 2026-05-26.
- **T-015** — `forecast-generation-and-labelling.md` Track 1a workflow doc (395 lines; per-asset block-bootstrap + 5 block reasons + 6-label decision tree + two-volatility-thresholds clarified; ADR-0003 1-of-7-predictors gap re-confirmed for 4th time). PR: https://github.com/Shorta-01/ai-trading-agent/pull/460 — merged 2026-05-26.
- **T-016** — `forecast-calibration-and-prediction-diary.md` Track 1a workflow doc (318 lines; two evaluation flows — worker 06:00 calibration + API on-demand prediction-diary; 4 hit_status + 5 outcomes + 3 horizons; ADR-0003 calibration-correction-layer gap half-built). PR: https://github.com/Shorta-01/ai-trading-agent/pull/461 — merged 2026-05-26.
- **T-017** — `decision-package-composition.md` Track 1a workflow doc (401 lines; per-asset compose with 5 locked gates + SHA-256 content-addressed hash + previous_package_hash chain + deterministic Dutch template + hard order-safety floor; idempotency intent-vs-reality gap surfaced). PR: https://github.com/Shorta-01/ai-trading-agent/pull/462 — merged 2026-05-26.
- **T-018** — `action-draft-composition-and-approval.md` Track 1a workflow doc (373 lines; two composer paths + 11 A-K dry-run gates + two state-vocabulary islands mapped side-by-side + JA confirmation token + `safe_for_submission=False` hard floor; portfolio↔storage vocabulary unification gap re-confirmed for 5th time). PR: https://github.com/Shorta-01/ai-trading-agent/pull/463 — merged 2026-05-26.
- **T-019** — `ibkr-order-submission-lifecycle.md` Track 1a workflow doc (445 lines; APScheduler sweep + 12 Tier-1 safety gates + Decimal→float boundary + Tier-2 account re-read + single `place_order` call + 4 IBKR callback families + 3 audit tables; doctrine drift re-confirmed — worker submitter.py:240 + API ibkr_ibapi_order_submission_client.py:525; 10 Phase 1c findings). PR: https://github.com/Shorta-01/ai-trading-agent/pull/464 — merged 2026-05-27.
- **T-020** — `ibkr-reconciliation-passes-a-b-c.md` Track 1a workflow doc (471 lines; reconciler tick + shared single-flight lock + connection gate + strict Pass A → B → C + 4 audit tables + 7 API routes; 10 Phase 1c findings incl. no APScheduler wiring for `IbkrReconciler.tick` + 4-tier B/C/D/E classification absent from code + legacy `reconciliation_sync.py` doctrine drift + Pass C 24h cut-off hard-coded + `skipped_locked` ticks produce no audit row). PR: https://github.com/Shorta-01/ai-trading-agent/pull/465 — merged 2026-05-27.
- **T-021** — `portfolio-valuation-and-cost-basis.md` Track 1a workflow doc (362 lines; sync snapshot → cost-basis derivation (`quantity × average_cost`) → market value + freshness gate → unrealized P&L → FX conversion + per-pair invalid/stale/fresh gates → readiness API → 30s frontend polling with Decimal-as-string verbatim; 10 Phase 1c findings incl. per-lot storage missing (intent §1) + `PaperLot`/`FifoLotAllocation` unpersisted + display-method setting absent + dashboard bypasses central calc module + Belgian tax disposal exec-time FX not recorded + asymmetric multi-currency base-currency heuristic). PR: https://github.com/Shorta-01/ai-trading-agent/pull/466 — merged 2026-05-27.
- **T-022** — `belgian-tax-computation.md` Track 1a workflow doc (402 lines; locked compute primitives — 6-class TOB rate table + 0.30 dividend withholding + Decimal HALF_UP cents → single production call site (compute_orderimpact) → action-draft persistence via migration 0035 → Dutch UI render in /portefeuille; 11 Phase 1c findings incl. worker composer omits TOB / no security classifier / TOB-net expected return not implemented / fx_rate_at_fill absent on ibkr_executions (re-confirmed from T-021) / 0 of 4 record items shipped / annual report has zero infrastructure / compute_dividend_withholding is a stranded primitive). PR: https://github.com/Shorta-01/ai-trading-agent/pull/467 — merged 2026-05-27.
- **T-023** — `ai-explanation-and-budget.md` Track 1a workflow doc (341 lines; AnthropicExplanationProvider → assert_budget_available → messages.create → validate_explanation_output → cache via migration 0034 → claude_ai_budget_usage via migration 0043; 15 Phase 1c findings incl. Depth-B 6-element structure absent (hard-coded 2-3 sentence paraphrase), eager generation not lazy, voice-rule Layers 2+3 not implemented, 80/100% threshold warnings absent, multi-provider fallback absent, no prompt_version on cache, Case-B `AnthropicTsModelProvider` wired in behind 5 feature flags despite intent §5 forbidding it). PR: https://github.com/Shorta-01/ai-trading-agent/pull/468 — merged 2026-05-27.
- **T-024** — `predictor-backtest-and-leaderboard.md` Track 1a workflow doc (312 lines; walk-forward backtester predictor_backtester.py:1-409 with 252-day window + 5-day weekly step + Brier/Sharpe/hit-rate metrics → predictor_backtest_runs storage via migration 0041 → 4 API routes status_routes.py:3298/:3405/:3466/:3704 incl. leaderboard with inverse-Brier auto-weights; 15 Phase 1c findings incl. weekly-not-monthly step methodology drift / look-ahead bias prevention absent / transaction costs not deducted from fold returns / CI gate absent / leaderboard UI absent / 4-stage entry path 0-of-4 implemented / shadow-mode absent / weight floor 5% vs intent 10% direct numeric contradiction / ADR-0003 1-of-7 predictors 5th re-confirmation — closes Track 1a reality functionality). PR: https://github.com/Shorta-01/ai-trading-agent/pull/469 — merged 2026-05-27.
- **T-025** — `user-confirm-starter-watchlist.md` Track 1a workflow doc (266 lines; user-action narrative — banner sighting (60s poll, 3 render states) → /volglijst conditional render → starter list with fail-closed Verwijder flow → BEVESTIG monospace input (uppercase case-sensitive) → POST /watchlist/confirm 4-gate validation → state transition + audit; 10 Phase 1c findings on the user-action surface incl. + Asset toevoegen placeholder bootstrap-paradox, no case-sensitivity hint, gate ordering hides downstream blockers, no idempotency key for racy tabs, banner stays hidden when storage down — first of 11 Track 1a workflow docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/470 — merged 2026-05-27.
- **T-026** — `user-approve-action-draft.md` Track 1a workflow doc (275 lines; user-action narrative — /ibkr-acties Te keuren tab → per-row Goedkeuren → window.prompt with formatted text → JA client-side strict-equality compare → POST /approve (no body, no token validation) → update_status(actor='user') → green Goedgekeurd badge + out-of-date "future update" banner; 10 Phase 1c findings incl. JA token client-side-only enforcement re-surfaced, 3 different browser-native dialog types, out-of-date banner contradicting shipped T-019, racy double-click, superseded drafts still approvable, prompt shows gross notional but no TOB-net). PR: https://github.com/Shorta-01/ai-trading-agent/pull/471 — merged 2026-05-27.
