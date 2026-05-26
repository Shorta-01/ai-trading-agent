```yaml
id: T-059
title: Consolidate all FIND entries into `00-findings.md`
phase: P1
status: locked
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

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
