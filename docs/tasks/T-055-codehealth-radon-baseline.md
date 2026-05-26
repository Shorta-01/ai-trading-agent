```yaml
id: T-055
title: Run `radon` baseline (complexity + maintainability) and emit FIND entries
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
