## Task

`T-NNN — <goal>`

## References

- Task row: `docs/tasks/queue.md` (`T-NNN`)
- Intent ref: `docs/intent/<file>.md#<section>` _(brainstorm tasks)_
- Decision ref: `docs/decisions/NNNN-<slug>.md` _(brainstorm tasks)_
- Findings resolved: `FIND-XXX, FIND-XXX` _(code-health tasks; list IDs
  from `docs/code-health/00-findings.md`)_

## Summary

- _Bullet 1: plain English, what changes._
- _Bullet 2: plain English, why it changes._
- _Bullet 3: …_
- _(3–5 bullets total)_

## Files touched

- `path/to/file_one.py`
- `path/to/file_two.tsx`
- _(complete list)_

## Tests

- Added: _list new tests, or "none"_
- Updated: _list changed tests, or "none"_
- All passing: _yes / no_ — _link to local or CI run_

## Audit results

_Output of the audit-before-execute checklist (`docs/tasks/_audit-discipline.md`)._

- Step 1 (read all touched files): _done_
- Step 2 (one-line per touched file):
  - `path/to/file_one.py` — _what it currently does_
  - `path/to/file_two.tsx` — _what it currently does_
- Step 3 (one-line change): _<the change>_
- Step 4 (criteria measurable): _yes_
- Step 5 (out-of-scope does not block goal): _confirmed_

## CI status

- _green / red_ — _link to the CI run_

## Risk / rollback

- Blast radius: _which systems are affected if this is wrong_
- Reversibility: _easy / medium / hard, and how to revert_
- Rollback steps: _if non-trivial, list them_
