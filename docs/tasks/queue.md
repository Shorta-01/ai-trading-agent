# Audit Workflow Task Queue

The canonical list of audit-workflow tasks. New rows are append-only;
existing rows are updated only to change `status` and append `pr_url`.
The full schema for each row lives in `docs/tasks/_task-template.md`,
and the rules for picking the next task live in
`docs/tasks/_standing-prompt.md`.

Each row identifies a task by `T-NNN`. Larger tasks have a working
file at `docs/tasks/T-NNN-<slug>.md`; small ones can be tracked here
alone.

## In Progress

_None._

## Locked

_None._

## Blocked

_None._

## CI-Failing

_None._

## Done

_None._
