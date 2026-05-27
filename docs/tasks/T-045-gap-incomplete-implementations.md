```yaml
id: T-045
title: Write gap analysis doc — 02 incomplete implementations
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/490
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/gap-analysis/02-incomplete-implementations.md` does not exist (verified). T-044 (sibling, merged) established the 6-part format. T-044 §16 explicitly cross-referenced several findings as "belongs to T-045". T-045 inherits those.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the gap analysis of incomplete-but-partially-shipped implementations.
  - `02-incomplete-implementations.md` — gap-entry-per-implementation for features that exist in code but are unwired / stranded / asymmetric / structurally incomplete: (1) `SubmissionSweep.tick()` not APScheduler-wired, (2) `IbkrReconciler.tick()` not APScheduler-wired, (3) Worker `cancel_order` not wired, (4) `compute_dividend_withholding` stranded with no consumers, (5) `PaperLot` + `FifoLotAllocation` domain models unpersisted, (6) Worker composer omits TOB while API path populates it, (7) `fx_rate_at_fill` absent on `ibkr_executions`, (8) AI Depth-B prompt is 2-3 sentence paraphrase not 6-element structure, (9) AI explanation eager-generated not lazy, (10) No `prompt_version` on `decision_package_explanations` cache, (11) Dual morning-chain orchestrators (worker + API parallel), (12) Two reconciliation orchestrators (worker 3-pass + API legacy), (13) Two `placeOrder` paths (worker submitter + API direct), (14) 4-tier B/C/D/E classification absent from code, (15) `skipped_locked` produces no audit row, (16) Out-of-date banner text contradicting shipped infrastructure.
- **Step 3 (one-line change):** write one gap-analysis doc enumerating incomplete-implementation gaps.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; ≥ 12 incomplete-implementation gap entries; each entry uses the 6-part format; MoSCoW distribution spans at least 3 ratings; effort spans at least 2 sizes; each entry cites originating reality doc; cross-reference table to T-044 + T-046-T-049 documented; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — entirely-missing features in T-044 (merged), predictor/quant gaps in T-046 (next), AI provider gaps in T-047, operational/security gaps in T-048.

## Goal

Produce one gap-analysis doc enumerating features whose code exists but is incomplete, unwired, stranded, asymmetric, or duplicated. T-044 covered features-that-don't-exist; T-045 covers features-that-half-exist. The two are operationally different — fixing an unwired class is cheaper than building a missing feature.

## Context

`depends_on:` T-001 … T-010 reality docs + T-036 … T-043 architecture docs. T-044 covered missing user-facing features. T-045 narrows to the partial-implementation class. Many entries here are direct re-surfacings of Track 1a "the class exists but isn't called" or "two parallel implementations" findings.

## Touch scope

Create:
- `docs/gap-analysis/02-incomplete-implementations.md`

Read: All reality docs + Track 1b verdicts + T-044 for cross-reference.

## Acceptance criteria

- [ ] Output file exists at `docs/gap-analysis/02-incomplete-implementations.md`.
- [ ] ≥ 12 incomplete-implementation gap entries.
- [ ] Each entry uses the 6-part format (name + why + where + effort + dependency + MoSCoW).
- [ ] MoSCoW distribution spans at least 3 ratings.
- [ ] Effort distribution spans at least 2 sizes.
- [ ] Each entry cites originating reality doc.
- [ ] Cross-reference table to T-044 + T-046-T-049 included.
- [ ] No source modification.

## Out of scope

- Missing features (T-044 — merged).
- Predictor + quant gaps (T-046 — next).
- AI provider gaps (T-047 — future; though some AI-implementation incompletes land here).
- Operational gaps (T-048 — future).
- Summary (T-049 — last).

## Verification

- File exists.
- 6-part format consistent.
- MoSCoW span verified.
- Cross-reference table present.

## Notes

T-045 is the 2nd of 6 Track 1c docs. The dominant pattern is **unwired infrastructure** — classes that exist, are tested, have docstrings claiming "Wired into APScheduler", but are never instantiated in production. This pattern surfaced most prominently in T-020 §10.1 (`IbkrReconciler.tick()`) and T-034 (`SubmissionSweep.tick()`) but extends across the codebase. T-045 elevates these from "audit findings" to "concrete fix gaps".
