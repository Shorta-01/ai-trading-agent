# Task Template

Status set: `locked | in-progress | pr-open | pr-merged | done | blocked | ci-failing`.

- `locked` — task is defined and ready to be picked up. The default
  for a newly-created task.
- `in-progress` — actively being worked on in the current session.
- `pr-open` — PR is open with the changes; awaiting CI + review.
- `ci-failing` — PR is open but CI is red. Highest priority next
  session (see `_standing-prompt.md` rule 1).
- `pr-merged` — PR merged to `main`; cleanup steps may still be due.
- `done` — task fully complete (PR merged, all post-merge steps done,
  any findings flipped to `resolved`).
- `blocked` — cannot proceed; reason recorded in `docs/tasks/queue.md`.

## Front matter

Every task working file at `docs/tasks/T-NNN-<slug>.md` starts with the
fields below in this exact order. Use a fenced block or a YAML front
matter block — either is fine, as long as the fields and order match.

```yaml
id: T-NNN                                  # zero-padded sequential
title: <short imperative>                  # also drives the branch slug
phase: P1 | P2 | P3 | P4 | P5
status: locked                             # default on creation
source: brainstorm | code-health
severity: critical | high | medium | low   # REQUIRED when source is code-health; optional otherwise
owner: claude
created: YYYY-MM-DD
intent_ref: docs/intent/<file>.md#<section>      # REQUIRED when source is brainstorm
decision_ref: docs/decisions/NNNN-<slug>.md      # REQUIRED when source is brainstorm
findings: [FIND-XXX, FIND-XXX]                    # REQUIRED when source is code-health
pr_url:                                           # filled in when status reaches pr-open
```

## Body sections

```markdown
## Goal

_One sentence: the outcome this task delivers._

## Context

_Why this task exists. Reference the brainstorm entry, the gap-analysis
row, or the code-health finding it traces back to._

## Touch scope

_Files / directories that may be modified by this task. Anything not
on this list is out of scope by default._

## Acceptance criteria

- [ ] _Measurable criterion 1_
- [ ] _Measurable criterion 2_

## Out of scope

- _Explicit non-goals to prevent scope creep._

## Verification

_Concrete commands, signals, or observations that prove the criteria
are met. Used during audit-before-execute step 4._

## Notes

_Free-form working notes, decisions surfaced during execution, links
to related tasks._
```

## Field rules

- `id` is zero-padded and monotonically increasing. Never reused.
- `title` is the source of truth for the branch slug used by the
  standing prompt: `task/T-NNN-<slug-from-title>`.
- `source: brainstorm` → `intent_ref` and `decision_ref` are required.
- `source: code-health` → `findings` is required and `severity` is
  required. `intent_ref` / `decision_ref` are optional.
- `pr_url` stays empty until status reaches `pr-open`. Once set, it is
  never removed; subsequent merges and follow-ups update `status`, not
  `pr_url`.
