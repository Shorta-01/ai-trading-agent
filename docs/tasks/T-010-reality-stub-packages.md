```yaml
id: T-010
title: Write reality doc for the six README-only stub packages
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

Produce one reality doc covering the six README-only packages under `packages/` that currently have no source code: `ai`, `analytics`, `audit`, `data_providers`, `risk`, `tax`.

## Context

These six directories each contain only a single README file with placeholder Dutch text ("Placeholderpakket voor toekomstige module-uitwerking…"). They were created as named slots for future work but never received source. They are structural signals — names commit the project to having those modules — and need to be documented so later phases don't mistake them for missing work. `depends_on:` —.

## Touch scope

Create:
- `docs/reality/components/stub-packages.md`

Read: `packages/{ai,analytics,audit,data_providers,risk,tax}/README.md`.

## Acceptance criteria

- [ ] Output file exists.
- [ ] One section per stub package: name, README path, README content (one-line summary), what code IS implementing the equivalent concept elsewhere (where applicable — e.g. risk concerns are scattered across `portfolio/*_guards.py`).
- [ ] Closing summary table: stub package → equivalent code locations elsewhere (or "no equivalent — fully unimplemented").
- [ ] No source / README modification.

## Out of scope

- Proposing where the stubs should be filled (Phase 1c gap analysis).
- Moving any code into the stubs.

## Verification

- File exists.
- All six stub packages appear in the file.

## Notes

The pattern (named-stub-without-source) is itself an architectural signal worth recording: someone reserved namespace for these concerns and then implemented them, where implemented at all, inside the existing `domain` / `portfolio` packages. This reality doc gives Track 1b (architecture review) and Track 1c (gap analysis) something concrete to cite.
