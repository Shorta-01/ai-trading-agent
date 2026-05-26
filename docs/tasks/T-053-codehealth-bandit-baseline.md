```yaml
id: T-053
title: Run `bandit` baseline (Python security smells) and emit FIND entries
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

Run `bandit -r apps packages -x tests -ll` and triage findings into FIND-XXX entries or `_dismissed.md` rows.

## Context

`-ll` flag = report low-and-up severity findings. AGENTS.md bans hardcoded secrets and silent data correction — bandit findings touching those areas get bumped to severity `critical` regardless of bandit's own rating. `depends_on:` —.

## Touch scope

Create / append to:
- `docs/code-health/02-anti-patterns.md`
- `docs/code-health/04-bugs.md` (where the smell is an actual vulnerability)
- `docs/code-health/_dismissed.md`

Run:
- `bandit -r apps packages -x tests -ll -f json | tee /tmp/bandit-baseline.json`
- Also keep a human-readable copy: `bandit -r apps packages -x tests -ll | tee /tmp/bandit-baseline.txt`.

## Acceptance criteria

- [ ] Raw output captured (JSON + text).
- [ ] Every distinct finding becomes a FIND-XXX or `_dismissed.md` row.
- [ ] AGENTS.md-relevant findings (`hardcoded secrets`, silent suppression of exceptions tied to financial calc) marked severity `critical`.
- [ ] FIND schema honoured. ID convention: `FIND-BANDIT-NNN`.
- [ ] No source modification.

## Out of scope

- Adding `# nosec` comments.
- Configuring a `.bandit` skip-list.

## Verification

- Raw outputs present.
- Sum of FIND-BANDIT-* + dismissed rows = total finding count.

## Notes

Common bandit categories to expect: `assert_used` in tests (excluded), `try_except_pass`, `hardcoded_password_string` false positives on test fixtures, `request_without_timeout`, `subprocess_*`.
