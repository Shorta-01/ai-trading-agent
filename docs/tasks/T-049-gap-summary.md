```yaml
id: T-049
title: Write gap analysis summary doc — 00 summary
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/494
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/gap-analysis/00-summary.md` does not exist (verified). All 5 prior Track 1c docs merged: T-044 (15 missing-features), T-045 (15 incomplete-impl), T-046 (13 quant), T-047 (12 AI), T-048 (15 operational). Total 70 gap entries.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the Track 1c gap-analysis synthesis.
  - `00-summary.md` — synthesises 70 gap entries across T-044-T-048: (1) aggregate MoSCoW + effort distributions, (2) 19 Must items + sequencing recommendation, (3) cross-doc most-cited findings (ADR-0003 6× / wiring gaps 8× / Case-B / fx_rate_at_fill), (4) Track 1b → Track 1c convergence patterns, (5) Phase 2 sprint-shaped backlog recommendation, (6) "category transition" thesis: 5 sprints converting localhost POC → production-ready service.
- **Step 3 (one-line change):** write one Track 1c gap-analysis synthesis closing the track.
- **Step 4 (measurable):** yes — eight acceptance criteria: file exists; aggregate gap matrix across 70 entries; all 5 prior docs cited; 19 Must items enumerated with sprint-shape grouping; cross-doc most-cited findings surfaced; Track 1b → Track 1c convergence mapped; Phase 2 sprint sequencing proposed; "category transition" thesis articulated; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — no Track 1c sibling left (T-049 closes); functional-review additions (T-011b/T-011c/T-012b/T-016b/T-021b) are separate. T-049 is the synthesis, NOT a fix-implementation document.

## Goal

Produce one summary doc synthesising Track 1c's 5 gap-analysis docs (T-044-T-048). Surface the aggregate MoSCoW + effort distributions, the 19 Must items with proposed sprint-sequencing, the most-cited cross-doc findings, the Track 1b → Track 1c convergence patterns, and the "category transition" thesis. T-049 is the input to Phase 2 backlog planning — it identifies what to fix; Phase 2 decides what to build.

## Context

`depends_on:` T-044 + T-045 + T-046 + T-047 + T-048 (all 5 prior Track 1c docs merged). Per queue.md spec for T-049: "The `00-summary.md` task is written LAST and depends on T-044 … T-048." T-049 is that task.

## Touch scope

Create:
- `docs/gap-analysis/00-summary.md`

Read: T-044 … T-048 reality docs + T-043 (Track 1b summary for convergence mapping).

## Acceptance criteria

- [ ] Output file exists at `docs/gap-analysis/00-summary.md`.
- [ ] Aggregate gap matrix across 70 entries.
- [ ] All 5 prior docs cited.
- [ ] 19 Must items enumerated.
- [ ] Phase 2 sprint sequencing proposed.
- [ ] Cross-doc most-cited findings (ADR-0003, wiring gaps, Case-B, fx_rate_at_fill) surfaced.
- [ ] Track 1b → Track 1c convergence pattern documented.
- [ ] "Category transition" thesis articulated.
- [ ] No source modification.

## Out of scope

- Phase 2 implementation (Track 1c surfaces fixes; Phase 2 builds).
- Functional-review additions (T-011b through T-021b — separate carry-forward tasks).

## Verification

- File exists.
- 70-entry aggregate.
- All 5 docs cited.
- 19 Musts enumerated with sprint shape.

## Notes

T-049 closes Track 1c Gap Analysis. With Track 1c complete, the audit produces:
- Track 1a (24 reality docs): what IS.
- Track 1b (8 architecture-review docs): is what IS good?
- Track 1c (6 gap-analysis docs, this being the 6th): how to close the gaps.

Phase 1 audit is then complete except for 5 functional-review-addition tasks (T-011b/T-011c/T-012b/T-016b/T-021b) that carry forward from the 2026-05-26 functional review. Phase 2 backlog inherits the 19 Musts as its initial scope.
