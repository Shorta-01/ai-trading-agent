```yaml
id: T-044
title: Write gap analysis doc — 01 missing features
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/489
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/gap-analysis/01-missing-features.md` does not exist (verified). Track 1c spec from queue.md: "Each gap recorded with: name, why it matters in plain English, where it would live in current architecture, effort estimate (small/medium/large), dependency, MoSCoW priority." All 24 Track 1a reality docs + 8 Track 1b architecture-review docs merged. T-044 inherits the recorded missing-feature findings.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the gap analysis of missing user-facing features.
  - `01-missing-features.md` — gap-entry-per-feature for user-facing features mandated by intent but absent from code: (1) Performance review screen, (2) Currency exposure dimension, (3) Annual Belgian tax report PDF, (4) Predictor leaderboard UI, (5) Live mid-price for sizing context, (6) AI Depth-C "Explain more" surface, (7) User-initiated reconciliation trigger, (8) Display method setting (FIFO/weighted-avg/specific-lot), (9) Voice-rule deterministic post-generation filter (Layer 2), (10) Multi-provider AI fallback (Anthropic → OpenAI), (11) Reynders bond-component recording, (12) Speculative classification awareness, (13) Foreign-source income summary, (14) €1M securities account tax data, (15) Trading settings full surface (10 of 11 fields invisible).
- **Step 3 (one-line change):** write one gap-analysis doc enumerating user-facing missing features.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; ≥ 12 missing-feature gap entries; each entry uses the locked 6-part format (name + why-it-matters + where-it-would-live + effort + dependency + MoSCoW); MoSCoW distribution spans at least 2 ratings; effort estimates span at least 2 sizes; each entry cites its originating reality doc; no source modification; cross-reference to Track 1c sibling tasks (T-045 incomplete implementations / T-046 quant gaps / T-047 AI gaps / T-048 operational gaps).
- **Step 5 (out-of-scope does not block goal):** confirmed — incomplete-but-shipped features go to T-045, predictor/quant gaps go to T-046, AI provider/budget gaps go to T-047, operational/security gaps go to T-048, summary to T-049.

## Goal

Produce one gap-analysis doc enumerating user-facing features that intent mandates but code lacks. Each gap entry uses the Track 1c 6-part format (name + why + where + effort + dependency + MoSCoW). T-044 focuses narrowly on **user-visible features absent from the system**. T-045 will cover features that exist but are incomplete; T-046-T-048 cover specialized gap categories.

## Context

`depends_on:` T-001 … T-010 reality docs + T-036 … T-043 architecture-review docs. Track 1c opens with T-044 as the first concrete-fix-prescribing doc — Track 1a/1b verdicted choices, Track 1c prescribes fixes.

## Touch scope

Create:
- `docs/gap-analysis/01-missing-features.md`

Read: All 24 Track 1a + 8 Track 1b reality docs + intent docs.

## Acceptance criteria

- [ ] Output file exists at `docs/gap-analysis/01-missing-features.md`.
- [ ] ≥ 12 missing-feature gap entries.
- [ ] Each entry uses the 6-part format (name + why-it-matters + where + effort + dependency + MoSCoW).
- [ ] MoSCoW distribution spans at least 2 ratings (Must / Should / Could / Won't).
- [ ] Effort estimates span at least 2 sizes (Small / Medium / Large).
- [ ] Each entry cites the originating reality doc.
- [ ] Cross-reference table to Track 1c siblings (T-045/T-046/T-047/T-048).
- [ ] No source modification.

## Out of scope

- Incomplete-but-shipped features (T-045 — next).
- Predictor / quant / forecasting gaps (T-046 — future).
- AI provider / budget / explanation gaps (T-047 — future).
- Operational / security / DR gaps (T-048 — future; T-042 already verdicted as critical).
- Summary (T-049 — last).
- Track 1b verdicts (T-036-T-043 — merged).
- Specific implementation plans (Track 1c scope is gap identification + MoSCoW + effort estimate, not implementation design).

## Verification

- File exists.
- 6-part format applied consistently.
- MoSCoW span verified.
- Cross-reference to T-045-T-048 documented.

## Notes

T-044 opens Track 1c Gap Analysis. The track is shorter than Track 1a (6 docs vs 24) and Track 1b (8 docs) — Track 1c is denser per-doc with concrete fix-shaped gap entries. T-044's missing-features list will be the primary input for Phase 2 backlog planning. The MoSCoW prioritisation here drives which features land in Phase 2 vs Phase 4.
