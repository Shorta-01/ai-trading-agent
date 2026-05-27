```yaml
id: T-022
title: Write reality doc for Belgian tax computation
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/belgian-tax.md
decision_ref: docs/decisions/0012-belgian-tax-architecture.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/467
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/belgian-tax-computation.md` does not exist (verified). Pure synthesis — every code site is cited in T-002 + T-005 reality docs or inspected here:
  - T-002 `portfolio-money-and-accounting.md` — `belgian_tax.py` (148 lines): `compute_tob`, `compute_dividend_withholding`, `TobSecurityClass` (6 classes), locked rates + caps.
  - T-005 `api-actions-suggestions-and-watchlists.md` — `action_draft.py` + `action_draft_sync.py` routes (TOB surfaces on action drafts).
  - T-007 `worker-actions-and-reconciliation.md` — `action_draft/composer.py` (where TOB lands on a draft).
  - `packages/storage/alembic/versions/0035_action_draft_belgian_tob.py` — migration that added TOB columns to action drafts.
  - `docs/reality/workflows/portfolio-valuation-and-cost-basis.md` (T-021 §10.8) — flagged the missing `fx_rate_at_fill` on `ibkr_executions` which directly impacts T-022's disposal-realised-gain computation.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the Belgian tax compute + record surface workflow doc.
  - `belgian-tax-computation.md` — TOB per-transaction compute (6-class rate table + Decimal-HALF_UP cents + per-class caps) → action-draft `belgian_tob_*` persisted columns → dividend withholding compute (30% roerende voorheffing) → tax-aware suggestions (intent §4 TOB-net expected return) → 8-section annual report (intent §3) → 5-row record-not-compute list (intent §1) — and the intent-vs-reality drift where the compute primitives exist but the consumer surfaces (annual report, speculative classification, Reynders recording, year-end snapshot, foreign-source income, exec-time FX on disposal) are absent.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing Belgian tax compute + record surfaces end-to-end.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; `compute_tob` cited (6-class rate table + caps + Decimal-HALF_UP-cents rounding); `compute_dividend_withholding` cited (30% locked rate); TOB persistence on action drafts cited (migration `0035` + column list); TOB call sites enumerated (composer + draft preview); annual report compute/record split documented per intent §1; Phase 1c gaps surfaced (annual report absent; speculative classification absent; Reynders absent; `fx_rate_at_fill` absent on `ibkr_executions`; tax rate versioning absent; year-end snapshot absent; foreign-source income absent); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — portfolio valuation (T-021 already merged sibling), AI explanation (T-023), predictor backtest (T-024).

## Goal

Produce one workflow reality doc tracing the Belgian tax compute + record surface end-to-end — from the locked `belgian_tax.py` math primitives (TOB + withholding) through their call sites (action-draft composer, decision package orderimpact, dividend-event ingest) to the persistence layer (action draft `belgian_tob_*` columns from migration `0035`) and what is NOT shipped (8-section annual report, speculative-classification tracking, Reynders bond-component recording, year-end position snapshot, foreign-source income summary, exec-time FX on disposal). The compute primitives are present and locked; the consumer surfaces are largely absent — the doc surfaces this drift cleanly.

## Context

`depends_on:` T-002 (which covered `belgian_tax.py` at module level), T-005 (which covered the API action-draft routes). T-022 stitches them with the worker composer + storage migration into the end-to-end "from `transaction_value` Decimal to a Dutch-rendered action-draft preview row" story, and bridges to the 8-section annual report intent that has zero code today.

## Touch scope

Create:
- `docs/reality/workflows/belgian-tax-computation.md`

Read: T-002 + T-005 + T-007 reality docs + the intent doc + the `belgian_tax.py` module + the `0035` migration + call sites discovered via grep.

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] `compute_tob` documented — 6 `TobSecurityClass` values + 3 distinct rate-cap pairs (`0.12% / €1300` bond, `0.35% / €1600` standard+distributing-ETF+other, `1.32% / €4000` accumulating-ETF+SICAV-redemption); `Decimal("0.01")` HALF_UP rounding; zero / negative input handling.
- [ ] `compute_dividend_withholding` documented — locked `BELGIAN_DIVIDEND_WITHHOLDING_RATE = Decimal("0.30")`.
- [ ] TOB persistence on action drafts documented — migration `0035_action_draft_belgian_tob.py` + the `belgian_tob_*` columns; `TobSecurityClass` string stored for audit-chain proof per the module docstring.
- [ ] TOB call sites enumerated (composer + draft preview); intent §4 "TOB-net expected return" implementation status documented.
- [ ] Compute-vs-record split documented per intent §1 (5 compute items + 4 record items) with current reality mapping.
- [ ] At least 10 intent-vs-reality gaps surfaced (annual report; speculative classification; Reynders; year-end snapshot; foreign-source income; `fx_rate_at_fill` on `ibkr_executions`; tax rate versioning; €1M securities account threshold; treaty-rate reclaim; lot-method per intent §3 vs current aggregate cost basis from T-021).
- [ ] No source modification.

## Out of scope

- Portfolio valuation + cost basis (T-021 already merged; provides `quantity × average_cost` aggregate, NOT the per-lot disposal price needed for realised-gain computation).
- AI explanation (T-023 future).
- Predictor backtest (T-024 future).

## Verification

- File exists.
- 6-class TOB rate/cap table cited (`belgian_tax.py:63-74`).
- `compute_tob` signature + cap-min rule cited (`belgian_tax.py:91-116`).
- `compute_dividend_withholding` signature + 30% rate cited (`belgian_tax.py:119-132`).
- Migration `0035_action_draft_belgian_tob.py` cited.
- At least 10 Phase 1c findings.

## Notes

T-022 is unusual: the compute primitives in `belgian_tax.py` are **rigorously locked** (148 LOC, Decimal-only, ROUND_HALF_UP, hard caps) but the surrounding consumer surfaces (annual report PDF, speculative classification tracking, Reynders recording, year-end snapshot, foreign-source income summary) are largely **absent**. The biggest cross-task finding is the `fx_rate_at_fill` absence on `ibkr_executions` (T-021 §10.8) which makes the intent-§1 "per-disposal realised gain in EUR at execution-time FX" computation impossible today — disposal P&L in EUR cannot be computed correctly when only the latest FX snapshot is available, not the FX at fill time. Phase 1c will likely propose adding `fx_rate_at_fill` + `eur_value_at_fill` to `ibkr_executions` as a precondition for T-022 consumer surfaces.
