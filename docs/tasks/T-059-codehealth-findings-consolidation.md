```yaml
id: T-059
title: Consolidate all FIND entries into `00-findings.md`
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** all four per-category files inventoried via `grep -E "^## FIND-"`:
  - `01-dead-code.md` (180 lines): 8 FINDs (`FIND-VULTURE-001`, `FIND-UNUSED-001..003`, `FIND-KNIP-001..004`).
  - `02-anti-patterns.md` (466 lines): 6 FINDs (`FIND-BANDIT-001`, `FIND-RADON-001..004`, `FIND-TSC-001`).
  - `03-outdated-patterns.md` (1 line): 0 FINDs (empty Phase 1d stub).
  - `04-bugs.md` (207 lines): 5 FINDs (`FIND-PIPAUDIT-001`, `FIND-NPMAUDIT-001..004`).
  - `_dismissed.md` (445 lines): T-050…T-058 dismissal sections (no FINDs — already dismissed).
  - `00-findings.md` (1 line): currently empty header stub — target file for rewrite.
- **Step 2 (one-line per touched file):**
  - `00-findings.md` — pre-edit: 1-line stub; post-edit: master list table with 19 rows + totals + severity reconciliation rule.
  - `01-dead-code.md` — pre-edit: 8 FINDs with per-tool IDs as H2 headers; post-edit: same content + `**Master ID:** FIND-NNN` cross-reference at the top of each FIND.
  - `02-anti-patterns.md` — pre-edit: 6 FINDs; post-edit: same + master ID cross-references on each.
  - `04-bugs.md` — pre-edit: 5 FINDs; post-edit: same + master ID cross-references on each.
  - `_dismissed.md` — pre-edit: T-050…T-058 sections; post-edit: T-059 consolidation note appended at the bottom recording which tools dismissed which categories wholesale.
  - `03-outdated-patterns.md` not touched (no FINDs to consolidate).
- **Step 3 (one-line change):** roll up 19 FINDs from 4 per-category files into `00-findings.md` master with unified `FIND-NNN` IDs (no source modification; per-tool IDs preserved as cross-references).
- **Step 4 (criteria measurable):** yes — six acceptance criteria: master table with the 8 required columns; every per-category FIND has a `master_id` mapping; collision check (no file:line overlap between FINDs after dedup analysis); severity reconciliation rule documented (MAX when tools disagree); 3-block totals (category / severity / tool) at top; no findings dropped (19 in → 19 out). Verification: `grep -c "^| FIND-" docs/code-health/00-findings.md` must equal 19.
- **Step 5 (out-of-scope does not block goal):** confirmed — no fixing of any finding; no batching proposal (T-060); no source code modification.

## Goal

Roll up every FIND-* entry across the per-category files (`01-dead-code.md`, `02-anti-patterns.md`, `03-outdated-patterns.md`, `04-bugs.md`) into a single sortable master list in `docs/code-health/00-findings.md`. Re-key every per-tool ID (`FIND-RUFF-NNN`, `FIND-MYPY-NNN`, …) to a unified `FIND-NNN` master ID, and rewrite the per-category files to use the master ID.

## Context

Phase 1d's per-tool baseline tasks (T-050 … T-058) each emit findings into per-category files using per-tool ID prefixes. This task is the deduplication + unification pass: same file:line picked up by two tools collapses into one master FIND; the master list is sortable by file, category, severity, and complexity. `depends_on:` T-050 … T-058 (all must be `pr-merged`).

## Touch scope

Modify:
- `docs/code-health/00-findings.md` — the master list (currently a one-line header).
- `docs/code-health/01-dead-code.md` … `04-bugs.md` — per-category files, re-keyed to master IDs.
- `docs/code-health/_dismissed.md` — no rekey, but include a "consolidation note" at the bottom recording which tools dismissed which categories wholesale.

Read: every entry in the per-category files, plus `_dismissed.md`.

## Acceptance criteria

- [ ] `00-findings.md` is a sortable table with columns: `master_id`, `file`, `line`, `category` (dead-code / anti-pattern / outdated-pattern / bug), `severity`, `complexity`, `tools` (comma-separated, one or more), `evidence_excerpt_short`, `link` (anchor to detail in per-category file).
- [ ] Every per-category FIND in `01`–`04` has a `master_id` mapping; per-tool IDs preserved as a "discovered by" cross-reference.
- [ ] Collisions resolved: same file:line picked up by N tools → one master FIND with `tools: ruff,mypy` in the row.
- [ ] Severity reconciliation rule used and documented at top of `00-findings.md`: when N tools disagree, use the MAX severity reported.
- [ ] `00-findings.md` opens with: (a) totals per category, (b) totals per severity, (c) totals per tool.
- [ ] No findings are silently dropped during consolidation.

## Out of scope

- Fixing any finding.
- Producing the batching proposal (T-060).
- Modifying source code.

## Verification

- `grep -c '^| FIND-' docs/code-health/00-findings.md` = sum of distinct findings across per-category files after dedup.
- Every `FIND-NNN` in the master list resolves to at least one anchor in a per-category file.

## Notes

Master-ID assignment order: walk per-category files in numerical order (`01` → `04`), within each file walk by file path then line; assign master IDs sequentially. This is reproducible.
