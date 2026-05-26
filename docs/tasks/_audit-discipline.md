# Audit-Before-Execute Discipline

The rule for every task in this workflow: audit first, change second.
"Audit" here is concrete and short — it is not a separate phase, it is
a checklist run at the top of each task before any edit is made.

## The six steps

1. **Read all files in the touch scope before editing any of them.**
   Touch scope is the list of files declared in the task's working
   file. Read every one in full (not just the line that looks
   relevant). If you find yourself wanting to edit a file you have not
   read, stop and read it.

2. **State what each touched file currently does, in one line.** Write
   a single line per file. The point is to prove understanding, not to
   produce documentation. If you cannot write the line, you do not
   understand the file yet — read more.

3. **State what the change is, in one line.** One line for the whole
   task. If it takes more than a line, the task is too broad and
   should be split.

4. **Verify the acceptance criteria are measurable.** Each criterion
   must be something you could check with a command, a test, or a
   direct observation. Vague criteria ("works correctly",
   "is cleaner") are rejected and rewritten before execution starts.

5. **Verify the out-of-scope list does not block the goal.** Read the
   out-of-scope list and confirm that nothing on it is actually a
   prerequisite for the acceptance criteria. If it is, either move it
   into scope or split the task into a dependency + the original.

6. **Only then execute.** Make the change, run the verification, open
   the PR.

## Why each step exists

- Step 1 prevents partial-information edits, which are the dominant
  cause of regressions during audit-driven refactors.
- Step 2 catches "I thought it did X but it does Y" before it becomes
  a bug.
- Step 3 forces the change to be small enough to describe.
- Step 4 prevents claiming completion on subjective criteria.
- Step 5 catches scope traps where the out-of-scope list is in
  tension with the goal.
- Step 6 is a reminder that the first five are cheap and the sixth is
  expensive — getting the order wrong is the costly mistake.

## Where the audit is recorded

For tasks with a working file at `docs/tasks/T-NNN-<slug>.md`, record
the audit (steps 1–5) inline in that file before starting work. For
tasks without a working file, the audit lives in the PR description
under a short "Audit" subsection.
