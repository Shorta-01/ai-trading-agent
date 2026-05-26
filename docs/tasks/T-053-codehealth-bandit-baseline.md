```yaml
id: T-053
title: Run `bandit` baseline (Python security smells) and emit FIND entries
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: (set on push)
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** `docs/code-health/02-anti-patterns.md`, `04-bugs.md`, `_dismissed.md` read at their current state (`02-anti-patterns.md` was the Phase 0 stub; `_dismissed.md` carried T-050 / T-051 / T-052 sections). Inspected the actual source for the 1 MEDIUM (`eodhd_client.py:148`), 5 B105 (`enums.py`), 10 B106 (reconciliation `pass_*` files + `settings.py:705,710`), 3 B110 (`ibkr_tws_readonly_adapter.py:118`, `status_routes.py:3149,3179`), 1 B112 (`predictor_backtester.py:162`), and a representative subset of the 20 B101 (`action_draft.py:256-262, :498-505`; `valuation_conversion_totals.py:275-285`).
- **Step 2 (one-line per touched file):**
  - `docs/code-health/02-anti-patterns.md` — pre-edit: stub; post-edit: `FIND-BANDIT-001` umbrella entry covering 20 B101 occurrences across 8 files.
  - `docs/code-health/_dismissed.md` — pre-edit: T-050 + T-051 + T-052 sections; post-edit: T-053 section appended with 20 dismissals grouped by test code (B105, B106, B110, B112, B310).
  - `docs/code-health/04-bugs.md` — unchanged (no actual vulnerability in the baseline).
- **Step 3 (one-line change):** run bandit, file 1 umbrella FIND for the B101 `assert`-for-mypy-narrowing pattern (20 sites), and dismiss the 20 false-positives / documented-intent findings (B105 enum values, B106 reference-id kwargs, B110 boundary catches already in T-050 `BLE001`, B112 per-fold catch already documented, B310 config-derived URL).
- **Step 4 (criteria measurable):** yes — raw output JSON + text captured; 1 FIND covers 20 B101 occurrences; 20 individual dismissal rows account for the remaining 20 findings; sum = 40 = total finding count.
- **Step 5 (out-of-scope does not block goal):** confirmed — no `# nosec` comments added; no `.bandit` skip-list configured; no source modification.

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
