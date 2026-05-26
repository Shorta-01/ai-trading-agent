```yaml
id: T-001
title: Write reality docs for the `packages/domain` package
phase: P1
status: pr-merged
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/434
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is creation of four new docs under `docs/reality/components/`; none exist yet, so there are no files to read in the *target* path. The *source* files to read (`packages/domain/src/portfolio_outlook_domain/*.py` plus their tests) are inventoried below — 35 source modules organised into four groups per the locked file plan.
- **Step 2 (one-line per touched file):** the four target files do not exist; each will hold a reality doc for one module group:
  - `domain-primitives-and-money.md` — covers primitives, costs, lots, identifiers, enums, instruments, term_deposits.
  - `domain-portfolio-and-policy.md` — covers portfolio, paper_setup, investment_policy, eligibility, approvals, capabilities, settings, market_calendar, market_data_foundation, audit.
  - `domain-research-and-suggestions.md` — covers suggestion_engine, suggestions, research, research_library, research_suggestions, quantitative_research, data_quality, data_sources, sources.
  - `domain-runtime-and-integration.md` — covers runtime, scheduler, storage, broker_adapter, broker_reconciliation, ibkr, orders, execution, ledger.
- **Step 3 (one-line change):** write four cited reality docs describing what the existing `packages/domain` modules actually export, what invariants they encode, and what depends on what.
- **Step 4 (criteria measurable):** yes — the six acceptance criteria are observable (file existence, `wc -l` count, grep for `path:NNN` cites, grep for the required sections, `git diff` scope check).
- **Step 5 (out-of-scope does not block goal):** confirmed. The out-of-scope list (no code fixes, no Phase 1b verdicts, no Phase 1c gaps, no Phase 1d findings, no test edits) is descriptive of what reality docs are *not* — none of those items is a prerequisite for the four docs themselves.

## Goal

Produce four reality docs covering the entire `packages/domain` source tree as files under `docs/reality/components/`.

## Context

`packages/domain` is the pure-types layer: dataclasses, protocols, enums, primitives. 36 source files (`packages/domain/src/portfolio_outlook_domain/*.py`). The four output files are locked in `docs/00-PHASES.md` §"Phase 1a — locked file plan". `depends_on:` —.

## Touch scope

Create:
- `docs/reality/components/domain-primitives-and-money.md`
- `docs/reality/components/domain-portfolio-and-policy.md`
- `docs/reality/components/domain-research-and-suggestions.md`
- `docs/reality/components/domain-runtime-and-integration.md`

Read (no modification): all `packages/domain/src/portfolio_outlook_domain/*.py` plus their docstrings and tests in `packages/domain/tests/` for behavioural confirmation.

## Acceptance criteria

- [ ] All four output files exist with the locked filenames.
- [ ] Every file lists its in-scope source modules in a "Modules covered" section near the top.
- [ ] Every factual claim cites at least one `path/to/file.py:NNN` reference.
- [ ] Non-trivial claims include a 3–10 line code excerpt.
- [ ] Each file ends with an "Open questions / uncertainty" section (empty is fine; absence is not).
- [ ] No source file is modified.

## Out of scope

- No fixes to domain code.
- No Phase 1b verdicts, Phase 1c gaps, or Phase 1d findings.
- No new types or refactors.
- No edits to `packages/domain/tests/` files (read-only inspection only).

## Verification

- `find docs/reality/components -name 'domain-*.md' | wc -l` returns 4.
- Spot-check three random claims per file to confirm `path:NNN` refs resolve.
- Confirm `git diff` shows changes only under `docs/reality/components/` and the queue/working-file status update.

## Notes

Module groupings (from the locked file plan):
- `domain-primitives-and-money.md`: `primitives`, `costs`, `lots`, `identifiers`, `enums`, `instruments`, `term_deposits`.
- `domain-portfolio-and-policy.md`: `portfolio`, `paper_setup`, `investment_policy`, `eligibility`, `approvals`, `capabilities`, `settings`, `market_calendar`, `market_data_foundation`, `audit`.
- `domain-research-and-suggestions.md`: `suggestion_engine`, `suggestions`, `research`, `research_library`, `research_suggestions`, `quantitative_research`, `data_quality`, `data_sources`, `sources`.
- `domain-runtime-and-integration.md`: `runtime`, `scheduler`, `storage`, `broker_adapter`, `broker_reconciliation`, `ibkr`, `orders`, `execution`, `ledger`.
