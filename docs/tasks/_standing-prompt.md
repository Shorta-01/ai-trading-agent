# Standing Prompt — paste this unchanged at the start of every execution session.

## Read at the start of every session

1. `docs/00-PHASES.md`
2. `docs/tasks/queue.md`
3. `docs/tasks/_audit-discipline.md`
4. `docs/tasks/_task-template.md`
5. `docs/decisions/decision-log.md`
6. The active task working file, if one exists at `docs/tasks/T-NNN-<slug>.md`.

## Working preferences

- No approval gates.
- Minimal reporting.
- Audit-before-execute (see `_audit-discipline.md`).
- Goal-led, not instruction-led.
- Never push to `main`.
- Never merge PRs (the user merges).

## Task selection rules (priority order)

1. If any task has `status: ci-failing`, fix it first. Read the failing
   CI run, fix on the same branch, push, and update the task status
   back to `pr-open`.
2. Otherwise, prefer tasks with `severity: critical` regardless of
   `source`.
3. Otherwise, alternate between `source: brainstorm` and
   `source: code-health`, picking the lowest-numbered eligible task
   from each source in turn. If one source is empty, pick from the
   other.

A task is *eligible* when its `status` is `locked` and all its
preconditions (intent ref present, decision ref present for brainstorm
tasks, findings present for code-health tasks) are satisfied.

## Per-task execution flow

1. Read `intent_ref`, `decision_ref`, and any linked FIND entries
   (`docs/code-health/00-findings.md`).
2. Update the task `status` to `in-progress` in `docs/tasks/queue.md`.
3. Create branch `task/T-NNN-<slug-from-title>` from the current `main`.
4. Execute end-to-end. Respect the task's `Touch scope` and `Out of scope`
   strictly — if a change you need is out of scope, stop and mark the
   task `blocked` with a reason in `docs/tasks/queue.md`.
5. Run the audit-before-execute checklist (`_audit-discipline.md`).
   Record the audit result; it goes into the PR body's `Audit results`
   section.
6. Run all relevant tests locally. If any touched file has code-health
   tooling configured (`docs/code-health/_tooling.md`), run those tools
   on the touched files too.
7. Commit, push the branch, open a PR. The PR body uses
   `docs/tasks/PR-TEMPLATE.md` (also auto-applied through
   `.github/pull_request_template.md`).
8. Update the task `status` to `pr-open` in `docs/tasks/queue.md` and
   append the `pr_url`.
9. If `source: code-health`, update each resolved FIND entry in
   `docs/code-health/00-findings.md` to `resolved` with the PR URL.
10. Move to the next eligible task.

## Stop conditions

- No more eligible tasks → stop and report.
- A blocker is hit on the current task → mark `blocked` with a reason
  in `docs/tasks/queue.md`, then move on.
- CI fails on an open PR → mark the task `ci-failing` in the queue,
  stop the session. The next session picks it up first via rule 1.

## Reporting

One-line summary per task completed. No narration of intermediate
steps.
