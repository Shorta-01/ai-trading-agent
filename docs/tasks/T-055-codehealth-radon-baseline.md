```yaml
id: T-055
title: Run `radon` baseline (complexity + maintainability) and emit FIND entries
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/445
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/02-anti-patterns.md` (post-T-053 — contains `FIND-BANDIT-001` only) and `docs/code-health/_dismissed.md` (T-050/T-051/T-052/T-053/T-054 sections) read pre-edit. `radon 6.0.1` installed via `pip install radon`. Raw outputs captured to `/tmp/radon-cc-baseline.txt` (6217 lines) and `/tmp/radon-mi-baseline.txt` (498 lines). Findings parsed into a structured intermediate at `/tmp/radon-cc-findings.txt` (212 rows).
- **Step 2 (one-line per touched file):**
  - `docs/code-health/02-anti-patterns.md` — pre-edit: `FIND-BANDIT-001` only; post-edit: four `FIND-RADON-001..004` umbrella entries appended (10 high-CC + 202 medium-CC + 9 high-MI + 8 medium-MI sites in per-FIND inventory tables).
  - `docs/code-health/_dismissed.md` — pre-edit: T-050+T-051+T-052+T-053+T-054 sections; post-edit: T-055 section appended (541 CC rank-B "watch" entries by file count; rationale = task spec dismisses rank B by default).
- **Step 3 (one-line change):** run radon CC + MI, file 4 FINDs grouping the 229 reportable findings by severity (10 high-CC + 202 medium-CC + 9 high-MI + 8 medium-MI), dismiss 541 CC rank-B watch entries.
- **Step 4 (criteria measurable):** yes — raw outputs at `/tmp/radon-cc-baseline.txt` + `/tmp/radon-mi-baseline.txt`; **CC totals match by rank**: A 4976 + B 541 + C 182 + D 20 + E 6 + F 4 = 5729 blocks (matches the radon-reported total at the tail of `cc-baseline.txt`); **MI totals match by rank**: A 473 + B 8 + C 9 = 490 modules (no E/F MI ranks exist in the radon scale; rank B = MI 10–19, rank C = MI < 10). FIND severity mapping applied: CC E/F → high, CC C/D → medium, MI C → high, MI B → medium. Every FIND inventory row carries the actual radon score in the evidence column.
- **Step 5 (out-of-scope does not block goal):** confirmed — no source modification; no complexity-threshold tuning. All four FINDs are categorisation + documentation only.

## Goal

Run radon cyclomatic-complexity (`cc`) and maintainability-index (`mi`) checks and triage findings.

## Context

`depends_on:` —. Radon thresholds (locked for this baseline):
- CC: only emit FIND for functions/methods at rank `C` or worse (CC ≥ 11). Rank `B` (CC 6–10) is dismissed by default but listed as "watch" in `_dismissed.md`.
- MI: only emit FIND for modules at rank `B` (MI < 20) or worse.

## Touch scope

Create / append to:
- `docs/code-health/02-anti-patterns.md` (complexity hotspots)
- `docs/code-health/_dismissed.md`

Run:
- `radon cc -s -a apps packages | tee /tmp/radon-cc-baseline.txt`
- `radon mi -s apps packages | tee /tmp/radon-mi-baseline.txt`

## Acceptance criteria

- [ ] Raw outputs captured.
- [ ] FIND entries created for: CC rank `C+` functions, MI rank `B+` modules.
- [ ] Each FIND records actual CC / MI score in evidence.
- [ ] FIND severity mapping: CC ≥ 21 (`E`/`F`) → high; CC 11–20 (`C`/`D`) → medium. MI rank `C` → high; rank `B` → medium.
- [ ] FIND ID convention: `FIND-RADON-NNN`.
- [ ] No source modification.

## Out of scope

- Refactoring any complex function.
- Adjusting complexity thresholds in this baseline (the locked thresholds above apply).

## Verification

- Raw outputs present.
- FIND count = (CC rank ≥ C count) + (MI rank ≥ B count).

## Notes

Radon does not produce line-precise findings for MI — record the module path with `:1` as a stable anchor.
