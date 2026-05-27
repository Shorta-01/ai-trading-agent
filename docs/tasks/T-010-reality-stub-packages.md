```yaml
id: T-010
title: Write reality doc for the six README-only stub packages
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/452
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file under `docs/reality/components/` does not exist (verified). All 6 stub READMEs read inline (~3 lines each, identical Dutch placeholder text). Cross-references discovered via grep + directory listing across `apps/api`, `apps/worker`, `packages/{domain,portfolio,storage}`: AI cluster (10+ files, T-006), analytics/calibration (6+ files across T-002/T-005/T-007/T-008/T-009), audit (13 storage repos + 1 API router + system-event triad), data_providers (EODHD ×2 + 4 IBKR ibapi clients + Anthropic ×2), risk (10 guard files + safety_recheck + release_readiness), tax (`belgian_tax.py` in portfolio package).
- **Step 2 (one-line per touched file):** the one target file does not exist; it will hold the consolidated reality doc for all six stub packages:
  - `stub-packages.md` — six per-package sections + closing summary table mapping each stub to its actual implementation location(s) elsewhere in the tree.
- **Step 3 (one-line change):** write one cited reality doc that catalogues the six README-only stubs and records where each concept is implemented today, no source / README modified.
- **Step 4 (criteria measurable):** yes — three acceptance criteria: file exists; one section per stub package (6 sections); closing summary table with equivalent-code locations (or "no equivalent — fully unimplemented"); no source / README modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — no proposals for where the stubs should be filled (Phase 1c gap analysis); no code movement into the stubs.

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
