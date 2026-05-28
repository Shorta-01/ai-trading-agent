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

- **T-012b** — `data-maturation-and-confidence-buildup.md` functional-review carry-forward reality doc (answers "does maturation logic exist?" — YES: sample-size confidence curve 0.40→0.95 + per-predictor min-bars + calibration coverage 3-state; limitations: bound to single predictor, sample-size not time-driven). *Branch:* `task/T-012b-reality-data-maturation`.

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
- **T-027** — `user-cancel-submitted-order.md` Track 1a workflow doc (257 lines; user-action narrative — /ibkr-acties Actief tab → red Annuleer button (cancellable={submitted,accepted,working,partially_filled}) → window.confirm yes/no → POST /cancel-submitted → status flip to pending_cancellation + lifecycle audit row + raw_callback_json.source='user_api_cancel'; 10 Phase 1c findings dominated by worker-execution gap — cancel writes are persistent never-executed records, broker never contacted, aspirational route docstring describing nonexistent worker behavior, no timeout for pending_cancellation, weakest token gate of the 3 user rituals, perm_id=0 sentinel). PR: https://github.com/Shorta-01/ai-trading-agent/pull/472 — merged 2026-05-27.
- **T-028** — `user-acknowledge-manual-review.md` Track 1a workflow doc (311 lines; user-action narrative — dashboard ReconciliationStatusWidget with warn flag → /admin/reconciliation → table with Bevestig dark button → window.prompt for OPTIONAL note (Cancel does NOT abort) → POST /acknowledge → idempotent draft-unaffecting → full 4-endpoint refresh; 10 Phase 1c findings dominated by 'Bevestig means queue housekeeping NOT case resolution' expectation gap — draft stays in requires_manual_review forever with no automatic path out, Pass-C escalations not in dashboard actions area, no separate audit row, window.alert error pattern is 3rd distinct dialog type). PR: https://github.com/Shorta-01/ai-trading-agent/pull/473 — merged 2026-05-27.
- **T-029** — `user-edit-trading-settings.md` Track 1a workflow doc (343 lines; user-action narrative — /instellingen page → single editable field user_buffer_eur out of 17 domain fields → read-modify-write with hard-coded reason_nl → PUT /settings/trading → upsert on settings_id='default' → no history table; 10 Phase 1c findings dominated by 10-of-11 invisible fields gap and the read-only-summary promise that's not rendered; plus 200-with-updated=False silent failure swallow, single global settings row, last-writer-wins concurrent edit, Category 1/3/4/5 all absent or partial). PR: https://github.com/Shorta-01/ai-trading-agent/pull/474 — merged 2026-05-27.
- **T-030** — `user-review-decision-package-detail.md` Track 1a workflow doc (270 lines; user-action narrative — /volglijst forecast panel → /decision-package/[id] → 7 locked Dutch sections + optional Maak actie button (ACTIONABLE_LABELS gate); 10 Phase 1c findings dominated by deterministic vs LLM explanation surface fragmentation (same DP, two different Dutch texts on different pages, no cross-link); plus single entry point with no nav, 404+503 collapse, Geblokkeerd label crash risk, held_quantity snapshotted not live, raw English gate_name/source_type, UTC timestamps). PR: https://github.com/Shorta-01/ai-trading-agent/pull/475 — merged 2026-05-27.
- **T-031** — `system-morning-pre-briefing-06-00.md` Track 1a workflow doc (235 lines; system-tick narrative — APScheduler cron hour=6 minute=0 Europe/Brussels → _on_pre_briefing → run_orchestrator(pre_briefing) → 2 sub-steps RUN (market-data + calibration) + 3 SKIP (forecasting / DP / daily briefing wait for 07:00) → worker_run_audit with market_data + calibration slots only; zero-LLM-cost by design; 10 Phase 1c findings incl. SCHEDULER_DAILY_BRIEFING_CRON config-vs-reality drift, skipped_locked no audit row, both sub-step exceptions silently swallowed, no per-tick deadline, no catch-up fire for missed cron; first of 5 system-tick workflows). PR: https://github.com/Shorta-01/ai-trading-agent/pull/476 — merged 2026-05-27.
- **T-032** — `system-morning-briefing-07-00.md` Track 1a workflow doc (300 lines; system-tick narrative — APScheduler cron hour='7-21' minute=0 → _on_hourly → _relabel_morning_briefing(hour=7→morning_briefing) → ALL 5 sub-steps RUN at 07:00 + calibration SKIPS → worker_run_audit with 3 populated slots; 12 Phase 1c findings DOMINATED by dual-scheduler doctrine drift between worker scheduler.py and parallel API morning_chain.py; plus _relabel depends on wall-clock, no catch-up fire, AI budget exhaustion has no Dutch fallback rendered). PR: https://github.com/Shorta-01/ai-trading-agent/pull/477 — merged 2026-05-27.
- **T-033** — `system-hourly-delta-runs.md` Track 1a workflow doc (286 lines; system-tick narrative — 14 fires per day at 08:00-21:00 share _on_hourly cron with 07:00 but _relabel_morning_briefing only fires for hour=7 so 08:00-21:00 stay as hourly_delta; ALL 4 sub-step gates EXPLICITLY EXCLUDE hourly_delta (market-data:321 / forecasting:337 / DP:358 / calibration:377) — fires only do lock + connectivity + mode detection + cold-start seed_runner + empty-payload audit row; 10 Phase 1c findings DOMINATED by name-vs-behavior mismatch — 'hourly delta' implies intra-day refresh but reality is 14 empty fires; plus cold-start SQL runs 16× daily, ~3528 empty audit rows yearly, intent doesn't pin hourly cadence). PR: https://github.com/Shorta-01/ai-trading-agent/pull/478 — merged 2026-05-27.
- **T-034** — `system-ibkr-submission-sweep.md` Track 1a workflow doc (238 lines; system-tick narrative — SubmissionSweep.tick() with 5-stage body (lock + market-hours + queue poll + 12-gate per-draft + submit-or-break) + locked one-per-tick break + 5-mode SweepMode Literal; but NOT WIRED — grep proof; user-approved drafts pile up indefinitely; 10 Phase 1c findings DOMINATED by no-APScheduler-wiring re-surfaced from T-020 §10.1, plus the 'IBKR-verzending wordt in een toekomstige update toegevoegd' banner from T-026 §6 is accidentally truthful, connection-lost ghost-order recovery also gapped, no defined intended cadence). PR: https://github.com/Shorta-01/ai-trading-agent/pull/479 — merged 2026-05-27.
- **T-035** — `system-ibkr-reconciliation-tick.md` Track 1a workflow doc (218 lines; system-tick narrative — IbkrReconciler.tick() with strict Pass A → B → C ordering + 4-mode ReconcilerMode Literal; same wiring gap as T-034; 0 of 7 intent-§1 trigger paths implemented; closes Track 1a Reality Workflows — 11/11 docs done). PR: https://github.com/Shorta-01/ai-trading-agent/pull/480 — merged 2026-05-27.
- **T-036** — `01-monorepo-structure.md` Track 1b architecture review (389 lines; 8 verdict-driven questions on apps/packages layout + workspace manager + 6 stub packages + Makefile + per-app CI + per-package config + frontend isolation + Docker; verdict matrix: 1 state-of-the-art + 3 acceptable + 3 outdated + 1 risky (the 6 README-only stub packages from T-010); patterns observed: tooling lags structure, stubs as unfulfilled intent, CI as parallelism workaround; opens Track 1b — first of 8 architecture-review docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/481 — merged 2026-05-27.
- **T-037** — `02-python-stack.md` Track 1b architecture review (379 lines; 8 verdict-driven questions on Python 3.12 + FastAPI 0-async/179-sync routes + AsyncIO usage + Pydantic v2 + SQLAlchemy Core + psycopg v3 + ibapi==9.81.1.post1 exact pin + APScheduler; verdict matrix: 2 state-of-the-art + 3 acceptable + 1 outdated + 2 risky; patterns observed: async commitment incoherent (async framework + 0 async routes), modern language conservative libraries, ibapi single-point-of-failure pin; second of 8 architecture-review docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/482 — merged 2026-05-27.
- **T-038** — `03-frontend-stack.md` Track 1b architecture review (448 lines; 8 verdict-driven questions on Next.js 15.2.6 App Router + React 19 + TS 5.7 strict + 60% "use client" + no state-mgmt lib + manual 1879-LOC apiClient.ts + inline styles + 18 polling sites; verdict matrix: 3 state-of-the-art + 3 outdated + 2 risky (no acceptable); patterns observed: bimodal stack — modern framework + 2018-era data layer, hand-rolled where ecosystem has solutions, 60% use client defeats App Router RSC; third of 8 architecture-review docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/483 — merged 2026-05-27.
- **T-039** — `04-data-and-storage.md` Track 1b architecture review (405 lines; 8 verdict-driven questions on Postgres + SQLite tests + 88-tables in 3116-LOC metadata.py + 53-migration linear Alembic chain + 47 JSON columns + Decimal-as-string MONEY_NUMERIC discipline + 53 repos in 6617-LOC sql_repositories.py + connection pool + single-DB; verdict matrix: 2 state-of-the-art (53-migration chain, Decimal discipline — gold standard) + 2 acceptable + 2 outdated (single-file metadata.py + sql_repositories.py) + 2 risky (no pool tuning vs FastAPI threadpool of 40, no caching for poll-heavy frontend); patterns observed: discipline at value layer + structure-debt at code layer, missing tiers between Python and Postgres; fourth of 8 architecture-review docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/484 — merged 2026-05-27.
- **T-040** — `05-testing-and-ci.md` Track 1b architecture review (407 lines; 8 verdict-driven questions on 240-file/56k-LOC Python test suite + real-impl discipline (3 of 240 mock ~1%) + zero conftest.py + no coverage measurement + no test parallelism + only parametrize markers + 10-job CI matrix with 3-attempt checkout retry + frontend Vitest+Playwright split; verdict matrix: 2 state-of-the-art (240-file test suite, 1% mock ratio) + 3 acceptable + 2 outdated (zero conftest, no parallelism) + 1 risky (no coverage measurement); patterns observed: discipline at test layer + infrastructure-debt at support layer, real-impl testing unusually strong as audit's strongest 'we know what we're doing' signal; fifth of 8 architecture-review docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/485 — merged 2026-05-27.
- **T-041** — `06-performance-and-scale.md` Track 1b architecture review (415 lines; 8 verdict-driven questions on single-worker uvicorn + threadpool-40/DB-pool-5 mismatch + zero caching + polling everywhere + no background queue + largest modules + no APM + no CDN; verdict matrix: 0 state-of-the-art (deliberate — perf is weakest layer) + 2 acceptable + 3 outdated + 3 risky; dominant pattern: stacked scale ceilings capping API at ~100 RPS; 5 of 8 high-priority Track 1c items; sixth of 8 architecture-review docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/486 — merged 2026-05-27.
- **T-042** — `07-security-observability-ops.md` Track 1b architecture review (431 lines; 8 verdict-driven questions on zero auth + no CORS/CSRF + no rate limiting + plain-text env + append-only audit tables + unstructured logging + minimal healthchecks + no backup/DR; verdict matrix: 1 state-of-the-art (audit tables — brightest spot) + 0 acceptable + 3 outdated + 4 risky; dominant pattern: audit-trail discipline + network-defense void; AGENTS.md backup mandate violated; 2 Critical + 2 High Track 1c priorities; seventh of 8 architecture-review docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/487 — merged 2026-05-27.
- **T-043** — `00-summary.md` Track 1b architecture review SUMMARY (273 lines; synthesises T-036-T-042 across 56 verdicted questions; aggregate distribution 11 state-of-the-art + 13 acceptable + 17 outdated + 15 risky; dominant meta-pattern: asymmetric discipline — rigor at domain/correctness layer + gaps at infrastructure/supporting layer; 4 state-of-the-art highlights all at domain layer; 4 critical Track 1c priorities all at infrastructure layer; 17 recurring patterns observed; final verdict: codebase exceptionally well-built where it had to be and exceptionally under-built where it could afford to be; CLOSES Track 1b — 8/8 docs complete). PR: https://github.com/Shorta-01/ai-trading-agent/pull/488 — merged 2026-05-27.
- **T-044** — `01-missing-features.md` Track 1c gap analysis OPENING (239 lines; 15 user-facing missing-feature gap entries with 6-part format; MoSCoW distribution 2 Must + 8 Should + 4 Could + 1 Won't-v1; all 4 ratings + all 3 effort sizes exercised; 2 Must items both address direct trading-quality issues (performance review screen, live mid-price for sizing); §16 cross-reference table to siblings; opens Track 1c gap analysis — first of 6 docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/489 — merged 2026-05-27.
- **T-045** — `02-incomplete-implementations.md` Track 1c gap analysis (232 lines; 15 incomplete-implementation gap entries; MoSCoW distribution 5 Must + 8 Should + 2 Could; effort 7 S + 6 M + 1 L; dominant pattern: unwired infrastructure; 5 Must items tightly clustered around safety-critical operational gap (SubmissionSweep + IbkrReconciler wiring, worker cancel_order wiring, fx_rate_at_fill schema, single place_order authority) — combined effort 4S+1M close ~80% of operational risk; §16 cross-reference table; second of 6 docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/490 — merged 2026-05-27.
- **T-046** — `03-quant-and-forecasting-gaps.md` Track 1c gap analysis (212 lines; 13 quant-specific gap entries; MoSCoW distribution 3 Must + 6 Should + 4 Could; dominant gap: ADR-0003 1-of-7 predictors (6th re-confirmation); 3 Must items form quant correctness floor — ADR-0003 ensemble closure (L), weight floor 5%→10% (S — first numeric contradiction in audit), backtest transaction costs (M — intent's 'not a backtest, it's marketing' rebuttal); §14 cross-reference table; third of 6 docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/491 — merged 2026-05-27.
- **T-047** — `04-ai-integration-gaps.md` Track 1c gap analysis (209 lines; 12 AI-specific gap entries; MoSCoW distribution 3 Must + 8 Should + 1 Could; effort 7 S + 5 M + 0 L; dominant gap: Case-B AnthropicTsModelProvider wired in production behind 5 feature flags despite intent §5 forbidding it; 3 Must items: Case-B quarantine (M), system prompt from intent file (S), Dutch 'budget bereikt' fallback rendering (S); §13 cross-reference table; fourth of 6 docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/492 — merged 2026-05-27.
- **T-048** — `05-operational-gaps.md` Track 1c gap analysis (237 lines; 15 operational gap entries; MoSCoW 6 Must + 8 Should + 1 Could — MOST MUSTS of any Track 1c doc; effort 6 S + 6 M + 3 L; dominant gap-pair: define deployment topology + auth layer + add backup tooling — both Critical pre-deploy blockers; AGENTS.md backup mandate explicitly violated; 6 Must items: auth topology (L), backup tooling (M), multi-worker uvicorn (S), pool tuning (S), TrustedHostMiddleware (S), ghost-order recovery via Pass A wiring (M); §16 cross-reference table; fifth of 6 docs). PR: https://github.com/Shorta-01/ai-trading-agent/pull/493 — merged 2026-05-27.
- **T-049** — `00-summary.md` Track 1c gap analysis SUMMARY (276 lines; synthesises T-044-T-048 across 70 gap entries; aggregate distribution 19 Must (27%) + 38 Should (54%) + 12 Could (17%) + 1 Won't-v1; 19 Musts grouped into 5 Phase 2 sprints totalling ~3-4 months focused engineering OR 6-8 weeks parallel; 5 most-cited cross-doc findings; Track 1b → Track 1c 73% risky→Must convergence; 'category transition' thesis — bounded one-quarter scope converting POC → production-ready; CLOSES Track 1c — 6/6 docs complete; Phase 1 audit core 49 docs done). PR: https://github.com/Shorta-01/ai-trading-agent/pull/494 — merged 2026-05-27.
- **T-011b** — `hourly-decision-refresh.md` functional-review carry-forward reality doc (100 lines; intent vs reality of "lighter hourly run" — intent: keep action list current between 07:00 evals; reality: 14 empty fires/day per T-033 §3; closes carry-forward ledger; Phase 2 paths: T-044 §5 live mid-price + T-046 §11 monthly rebacktest; first of 5 functional-review additions). PR: https://github.com/Shorta-01/ai-trading-agent/pull/495 — merged 2026-05-27.
- **T-011c** — `dashboard-composition.md` functional-review carry-forward reality doc (173 lines; dashboard contract vs intent §1; 1 of 5 elements honored (PAPER/REAL badge); 4 violations: charts forbidden-but-present, no actions area, no watchlist area, no single system-health line; out-of-date 'runtime bestaat nog niet' placeholder cards; build-order artefact root cause; 5 Phase 1c findings; second of 5 functional-review additions). PR: https://github.com/Shorta-01/ai-trading-agent/pull/496 — merged 2026-05-27.
