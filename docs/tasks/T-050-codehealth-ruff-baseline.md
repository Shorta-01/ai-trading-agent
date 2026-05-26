```yaml
id: T-050
title: Run `ruff` baseline and emit FIND entries
phase: P1
status: pr-merged
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/435
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the touch scope is the three append-able docs under `docs/code-health/` plus a read-only ruff run. All three target files were read and confirmed at their Phase 0 stub state (`02-anti-patterns.md` and `03-outdated-patterns.md` are single-header placeholders; `_dismissed.md` is a single-header file). Per-package ruff config in each `pyproject.toml` was read to confirm `select = ["E", "F", "I", "UP", "B"]`, `line-length = 100`, `target-version = "py312"`.
- **Step 2 (one-line per touched file):**
  - `docs/code-health/_dismissed.md` — pre-edit: single-header stub; post-edit: holds the T-050 baseline summary + per-file-ignore rows + grouped `# noqa` inventory.
  - `docs/code-health/02-anti-patterns.md`, `docs/code-health/03-outdated-patterns.md` — pre-edit: stub headers; post-edit: unchanged (ruff produced zero findings, nothing to add).
- **Step 3 (one-line change):** run ruff against the full Python codebase, confirm zero findings, record the pre-existing suppressions (per-file-ignores + noqa lines) in `_dismissed.md` so future widenings start from a complete map.
- **Step 4 (criteria measurable):** yes — raw output captured at `/tmp/ruff-baseline.json` (size 2 bytes, `[]`); `grep -c "^- FIND-" docs/code-health/0[1-4]-*.md` returns 0 (no FINDs because zero findings); per-file-ignore rows in `_dismissed.md` are independently verifiable against `pyproject.toml`.
- **Step 5 (out-of-scope does not block goal):** confirmed. The out-of-scope list (no fixes; no select widening; no other tools' triage) is fully observed — only `_dismissed.md` is appended; no source or config file is modified.

## Goal

Run `ruff check` against the full Python codebase with current config, triage every reported finding into a FIND-XXX entry or a one-line `_dismissed.md` row, and emit nothing else.

## Context

`ruff` is already configured per-package (`packages/{domain,portfolio,storage}/pyproject.toml` and `apps/{api,worker}/pyproject.toml`, select `E/F/I/UP/B`, line-length 100, py312). CI passes today, so a clean baseline run is expected to be small. The interesting findings live in per-file `per-file-ignores` and in any `# noqa` suppressions. `depends_on:` —.

## Touch scope

Create / append to:
- `docs/code-health/02-anti-patterns.md` (for E/B/UP violations that the lint config has not yet caught)
- `docs/code-health/03-outdated-patterns.md` (for UP findings)
- `docs/code-health/_dismissed.md` (for findings that are correctly suppressed or out of scope)

Run (read-only side effects beyond the docs):
- `ruff check apps/api apps/worker packages/domain packages/portfolio packages/storage --output-format=json | tee /tmp/ruff-baseline.json`
- Capture exit status; if non-zero, that's expected. Do not fail the task on non-zero exit.

Read: each per-package `pyproject.toml` `[tool.ruff]` block to record current config in the FIND entries' context.

## Acceptance criteria

- [ ] Raw output captured (path noted in Notes section of the relevant FIND entries).
- [ ] Every distinct file:line finding becomes either a FIND-XXX entry OR a one-line row in `_dismissed.md` with reason.
- [ ] FIND schema honoured: `id`, `file:line`, `tool`, `evidence` excerpt, `why it matters` in plain English, `fix approach` sketch, `complexity` (trivial/small/medium/large), `severity` (critical/high/medium/low), `related findings` (links to neighbouring FIND IDs when relevant).
- [ ] Per-file-ignores already in pyproject get cited as `_dismissed.md` rows with reason "ruff per-file-ignore in `<pyproject>:<line>`".
- [ ] No source / config modification.

## Out of scope

- Fixing any finding (Phase 4 territory after batching review).
- Adding new lint rules (`select` widening) — that's a separate brainstorm decision later.
- Triaging mypy, vulture, bandit etc. (separate baseline tasks).

## Verification

- `grep -c "^- FIND-" docs/code-health/0[1-4]-*.md` matches the count of distinct findings minus dismissals.
- Raw ruff output present on disk for the duration of the session and referenced in PR body.

## Notes

FIND ID convention: `FIND-RUFF-NNN` (zero-padded per tool). The consolidation task T-059 unifies all per-tool IDs into a single `FIND-NNN` master list.

Command transcript and exact `ruff` version go into the PR body under "Tests" / "All passing".
