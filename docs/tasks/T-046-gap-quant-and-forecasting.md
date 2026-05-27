```yaml
id: T-046
title: Write gap analysis doc — 03 quant and forecasting gaps
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/gap-analysis/03-quant-and-forecasting-gaps.md` does not exist (verified). T-044 + T-045 (siblings, merged) established the 6-part format + cross-reference discipline. T-045 §16 explicitly cross-referenced predictor/quant findings as "belongs to T-046". T-046 inherits those.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the gap analysis of predictor / forecasting / backtest gaps.
  - `03-quant-and-forecasting-gaps.md` — gap-entry-per-gap for quant infrastructure: (1) ADR-0003 1-of-7 predictors (6th re-confirmation), (2) Shadow-mode infrastructure absent, (3) 3-month observation period tracking absent, (4) 6-month retirement watch absent, (5) Weight floor 5% vs intent 10% — first numeric contradiction in audit, (6) Backtest methodology drift (weekly step vs intent's monthly), (7) Look-ahead bias prevention absent in backtester, (8) Transaction costs not deducted from fold returns, (9) CI-enforced backtest-on-add gate absent, (10) Monthly scheduled rebacktest absent, (11) On-demand backtest UI button absent, (12) 4-stage predictor entry path 0-of-4 implemented, (13) No prediction-diary shadow flag, (14) User-decision promotion system-decision item generator absent.
- **Step 3 (one-line change):** write one gap-analysis doc enumerating predictor / quant / forecasting / backtest gaps.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; ≥ 12 quant-specific gap entries; each entry uses the 6-part format; MoSCoW distribution spans at least 3 ratings; effort distribution spans at least 2 sizes; each entry cites originating reality doc; cross-reference table to T-044/T-045/T-047/T-048; ADR-0003 1-of-7 re-confirmed as the dominant gap; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — UI gaps in T-044, schema gaps in T-045, AI provider gaps in T-047, operational gaps in T-048.

## Goal

Produce one gap-analysis doc focused on predictor / quant / forecasting / backtest gaps. The dominant gap: **ADR-0003 mandates a 7-predictor ensemble; the worker runs 1**. Six modules exist in `packages/portfolio/`; three are supported by the backtest orchestrator; only one runs in production. Closing the ensemble gap is the highest-leverage quant fix.

## Context

`depends_on:` T-007 (worker forecasting), T-015 (forecast generation), T-016 (calibration + prediction diary), T-024 (backtest + leaderboard). T-024 is the densest source — its 15 Phase 1c findings map almost 1:1 to T-046 gap entries.

## Touch scope

Create:
- `docs/gap-analysis/03-quant-and-forecasting-gaps.md`

Read: T-007 + T-015 + T-016 + T-024 reality docs + T-044 + T-045 for cross-reference.

## Acceptance criteria

- [ ] Output file exists at `docs/gap-analysis/03-quant-and-forecasting-gaps.md`.
- [ ] ≥ 12 quant-specific gap entries.
- [ ] Each entry uses the 6-part format.
- [ ] MoSCoW distribution spans at least 3 ratings.
- [ ] Effort distribution spans at least 2 sizes.
- [ ] Each entry cites originating reality doc.
- [ ] Cross-reference table to T-044/T-045/T-047/T-048 included.
- [ ] ADR-0003 1-of-7 explicitly surfaced as dominant gap.
- [ ] No source modification.

## Out of scope

- Missing user-facing features (T-044 — merged).
- Schema / unwired-impl gaps (T-045 — merged).
- AI provider / voice / budget gaps (T-047 — next).
- Operational / security gaps (T-048 — future).
- Summary (T-049 — last).

## Verification

- File exists.
- 6-part format consistent.
- ADR-0003 prominent.
- Cross-reference table present.

## Notes

T-046 is the 3rd of 6 Track 1c docs. The quant infrastructure is paradoxical: T-024 documented an **impressive backtest harness** (409 LOC walk-forward + storage table + 4 API routes including leaderboard) BUT only 1 of 7 predictors actually runs in production. The infrastructure to evaluate predictors exists; the predictors themselves are mostly absent or deferred. Closing the gap is largely about wiring existing portfolio-package modules into the worker's `forecasting_step.py`, not about writing new predictors.
