```yaml
id: T-040
title: Write architecture review doc — 05 testing and CI
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/485
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/architecture-review/05-testing-and-ci.md` does not exist (verified). Every code site is already cited in T-009 + T-050-T-059 reality docs:
  - T-009 — full CI/scripts inventory + Docker layout.
  - T-050-T-058 — per-tool code-health baselines (ruff, mypy, vulture, bandit, pip-audit, radon, tsc, knip+ts-prune, npm audit).
  - T-059 — master findings consolidation.
  - T-036 §5 — per-app CI jobs already verdicted acceptable.
  - T-037 §1, §3 — Python 3.12 + mypy --strict already verdicted state-of-the-art.
  - T-038 §3 — TypeScript strict mode already verdicted state-of-the-art.
  - `apps/api/tests/`, `apps/worker/tests/`, `packages/*/tests/` (240 test files, 56k LOC).
  - `apps/web/vitest.config.ts`, `apps/web/playwright.config.ts`.
  - `.github/workflows/ci.yml` (8 jobs), `.github/workflows/code-health.yml` (2 jobs).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the verdict-driven architecture review of testing + CI.
  - `05-testing-and-ci.md` — 8-question verdict-driven assessment: (1) 240-file / 56k-LOC Python test suite + 1.8x test:source ratio, (2) Real-implementation testing discipline (3 of 240 tests use mocks ~1%), (3) Zero `conftest.py` / no shared fixtures, (4) No code coverage measurement (no `coverage.py` / `pytest-cov` / no CI gate), (5) No test parallelism (no pytest-xdist; Playwright workers=1), (6) Only `pytest.mark.parametrize`; no custom markers (no @slow / @integration / @ibkr), (7) CI 10-job matrix (8 ci + 2 code-health) with 3-attempt checkout retry, (8) Frontend test split: Vitest unit + Playwright e2e + no contract / no visual / no a11y tests.
- **Step 3 (one-line change):** write one verdict-driven architecture review of testing + CI.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 8 architectural choices enumerated; 5-part verdict format applied to each; verdicts span at least 3 ratings; the real-implementation discipline (1% mock ratio) verdicted state-of-the-art; the no-coverage gap verdicted risky; the no-conftest pattern verdicted; recommendations deferred to Track 1c; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — code-health findings deep dive (T-050-T-059 already merged), perf+scale (T-041 next), security+ops (T-042 future).

## Goal

Produce one verdict-driven architecture review of testing + CI — the test suite shape, the testing discipline (real vs mock), the CI pipeline structure. The dominant story: a high test-volume codebase with **real-implementation testing discipline** (rare and praiseworthy) but with **zero coverage measurement** and **zero parallelism** — strong tests + weak infrastructure. The codebase chose to test extensively and chose to test with real implementations; both are state-of-the-art. The misses are in the support layer.

## Context

`depends_on:` T-001 … T-010. T-009 covered the CI inventory; T-050-T-059 each ran one tool against the codebase and produced findings. T-040 verdicts the architectural choices in testing + CI.

## Touch scope

Create:
- `docs/architecture-review/05-testing-and-ci.md`

Read: T-009 + T-050-T-059 reality docs + test directory inventory + CI workflows.

## Acceptance criteria

- [ ] Output file exists at `docs/architecture-review/05-testing-and-ci.md`.
- [ ] 8 architectural choices enumerated.
- [ ] 5-part verdict format applied to each.
- [ ] Verdicts span at least 3 ratings.
- [ ] Real-implementation testing discipline (1% mock ratio) verdicted state-of-the-art.
- [ ] No-coverage gap verdicted risky.
- [ ] No-conftest pattern verdicted.
- [ ] Recommendations deferred to Track 1c.
- [ ] No source modification.

## Out of scope

- Monorepo (T-036 merged).
- Python (T-037 merged).
- Frontend (T-038 merged).
- Data + storage (T-039 merged).
- Performance + scale (T-041 next).
- Security + ops (T-042 future).
- Summary (T-043 last).
- Code-health findings deep dive (T-050-T-059 merged).
- Concrete fixes (Track 1c).

## Verification

- File exists.
- 8 choices × 5-part verdict.
- Multi-rating distribution.
- Real-impl discipline verdicted state-of-the-art.
- No-coverage gap verdicted risky.

## Notes

T-040 is the 5th of 8 Track 1b architecture review docs. The most surprising finding is the **1% mock ratio** — 3 out of 240 Python test files use any mocking. This is extraordinarily rare for a codebase of this size. The codebase tests with real Pydantic models, real SQLAlchemy queries, real Decimal math. This is the **strongest single testing-discipline signal** in the audit. The trade-off: tests run sequentially (no parallelism support), no coverage gate exists, and no shared fixture layer. Strong discipline + weak infrastructure.
