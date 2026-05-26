# Standing Prompt

> **Placeholder.** The intended content for this file was truncated in the
> Phase 0 task prompt. Replace this stub with the canonical standing
> prompt when the original is available. The structure below summarises
> what each session should read on startup so the rest of the scaffold
> can reference it consistently.

## Read at the start of every session

1. `docs/00-PHASES.md` — current phase plan and where we are in it.
2. `docs/tasks/queue.md` — pick up `in-progress` or top `pending` task.
3. `docs/tasks/_audit-discipline.md` — the audit-before-execute checklist.
4. `docs/tasks/_task-template.md` — the shape of a task working file.
5. `docs/decisions/decision-log.md` — recent decisions that may bind this work.
6. The working file for the active task, if one exists at
   `docs/tasks/T-NNN-<slug>.md`.

## Working preferences in effect

- No approval gates; execute the goal end-to-end.
- Minimal reporting; no narration of routine steps.
- Audit-before-execute: verify state before changes, summarise existing vs new.
- Goal-led, not instruction-led: deliverables are mandatory, implementation
  details are the executor's choice.

## On finishing a task

1. Update the task's row in `docs/tasks/queue.md`.
2. Add any new decisions to `docs/decisions/decision-log.md` plus a detailed
   record at `docs/decisions/NNNN-<slug>.md`.
3. Open a PR using `docs/tasks/PR-TEMPLATE.md` (auto-applied via
   `.github/pull_request_template.md`).
