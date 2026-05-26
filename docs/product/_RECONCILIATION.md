# Legacy task-tracking reconciliation

## Decision

Legacy `docs/product/task-queue.md` and `docs/product/task-history.md`
are **FROZEN** as of **2026-05-26**. No new entries. New
audit-workflow tasks live in `docs/tasks/queue.md` exclusively.
Historical entries remain readable for reference.

## Why

The Phase 0 scaffolding introduces a new task tracking schema
(`T-NNN` IDs, status set including `pr-open` / `ci-failing` /
`pr-merged`, `source: brainstorm | code-health`, intent / decision /
findings references) that the legacy files do not use. Maintaining
two parallel queues with different schemas would invite drift and
make the standing prompt's task selection rules unreliable. Freezing
the legacy queue is cheaper than back-porting hundreds of rows into
the new schema.

## What this means in practice

- Both legacy files now carry a `FROZEN` banner at the top linking
  back to this document.
- The Phase 1 audit will treat the existing content of both files as
  *historical input* — it informs reality docs and the intent corpus,
  but it does not produce new rows in either legacy file.
- All Phase 1–5 tasks land in `docs/tasks/queue.md`, follow the
  template in `docs/tasks/_task-template.md`, and obey the selection
  rules in `docs/tasks/_standing-prompt.md`.
- The Milestone A–J product structure that lives inside
  `task-queue.md` is not lost: when Phase 1c (gap analysis) runs, the
  milestone goals will be re-expressed as entries in `docs/intent/`,
  and any still-open work will surface as new `T-NNN` rows.

## Out of scope for this reconciliation

- No content in either legacy file is modified or migrated. The
  banner is the only change.
- No automated link rewriting from elsewhere in the repo into the
  legacy files. Existing inbound links continue to work; new docs
  should not link into the frozen files except through this
  reconciliation note.
