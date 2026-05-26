```yaml
id: T-002
title: Write reality docs for the `packages/portfolio` package
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: (set on push)
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is creation of four new docs under `docs/reality/components/`; none exist yet, so there are no files to read in the *target* path. The *source* modules to read (38 files under `packages/portfolio/src/portfolio_outlook_portfolio/*.py` plus tests) are inventoried below — organised into four groups per the locked file plan.
- **Step 2 (one-line per touched file):** the four target files do not exist; each will hold a reality doc for one module group:
  - `portfolio-money-and-accounting.md` — covers `money`, `accounting`, `lots`, `snapshot`, `performance`, `valuation_conversion_totals`, `valuation_cost_basis_pl`, `term_deposits`, `ledger_services`.
  - `portfolio-predictors.md` — covers the 14 predictor / ensemble / sizing / diary-eval modules.
  - `portfolio-guards-and-state-machines.md` — covers the 11 guards + state-machine + errors modules.
  - `portfolio-daily-briefing-and-tax.md` — covers `daily_briefing`, `research_evidence_summary`, `belgian_tax`, `capabilities`.
- **Step 3 (one-line change):** write four cited reality docs describing what the existing `packages/portfolio` modules actually export, what invariants they encode, and what depends on what — with Decimal-precision / ROUND_HALF_EVEN / money-boundary calls cited where applied.
- **Step 4 (criteria measurable):** yes — the seven acceptance criteria are observable (file existence, locked filenames, `## Modules covered` section, `path/to/file.py:NNN` cites, 3-10 line excerpts on non-trivial claims, `## Open questions / uncertainty` section per file, no source file modified).
- **Step 5 (out-of-scope does not block goal):** confirmed. No fixes, no refactors, no test changes, no Phase 1b/1c/1d artefacts, no API/worker wiring (those are T-005 / T-007).

## Goal

Produce four reality docs covering the entire `packages/portfolio` source tree as files under `docs/reality/components/`.

## Context

`packages/portfolio` is the financial / forecasting / guards core. 39 source files in `packages/portfolio/src/portfolio_outlook_portfolio/*.py`. The four output files are locked in `docs/00-PHASES.md` §"Phase 1a — locked file plan". `depends_on:` —.

## Touch scope

Create:
- `docs/reality/components/portfolio-money-and-accounting.md`
- `docs/reality/components/portfolio-predictors.md`
- `docs/reality/components/portfolio-guards-and-state-machines.md`
- `docs/reality/components/portfolio-daily-briefing-and-tax.md`

Read (no modification): all `packages/portfolio/src/portfolio_outlook_portfolio/*.py` plus their corresponding test files for behavioural confirmation.

## Acceptance criteria

- [ ] All four output files exist with the locked filenames.
- [ ] "Modules covered" section near the top of each file.
- [ ] `path/to/file.py:NNN` citations for every factual claim.
- [ ] Non-trivial claims have 3–10 line excerpts.
- [ ] Decimal-vs-float, money-boundary, and ROUND_HALF_EVEN policies cited where they apply (this package is the locus of money-precision rules).
- [ ] Each file ends with "Open questions / uncertainty".
- [ ] No source file modified.

## Out of scope

- No fixes; no refactors; no test changes.
- No verdicts, gaps, or code-health findings (those are Phase 1b/1c/1d).
- No coverage of `apps/api` or `apps/worker` wiring of these modules (covered by T-005, T-007).

## Verification

- `find docs/reality/components -name 'portfolio-*.md' | wc -l` returns 4.
- Spot-check Decimal-boundary references resolve.
- `git diff` is scoped to `docs/reality/components/` + queue/working-file status update.

## Notes

Module groupings (from the locked file plan):
- `portfolio-money-and-accounting.md`: `money`, `accounting`, `lots`, `snapshot`, `performance`, `valuation_conversion_totals`, `valuation_cost_basis_pl`, `term_deposits`, `ledger_services`.
- `portfolio-predictors.md`: `baseline_forecast`, `baseline_label_translator`, `_predictor_math`, `predictor_protocol`, `predictor_backtester`, `predictor_feedback`, `gbm_predictor`, `momentum_predictor`, `mean_reversion_predictor`, `qvm_factor_predictor`, `ai_ts_predictor`, `ensemble_combiner`, `kelly_sizing`, `prediction_diary_eval`.
- `portfolio-guards-and-state-machines.md`: `approval_guards`, `suggestion_guards`, `suggestion_engine_guards`, `execution_guards`, `storage_guards`, `paper_setup_guards`, `ai_explanation_guards`, `broker_reconciliation_guards`, `action_draft_safety`, `action_draft_state_machine`, `errors`.
- `portfolio-daily-briefing-and-tax.md`: `daily_briefing`, `research_evidence_summary`, `belgian_tax`, `capabilities`.
