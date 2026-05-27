```yaml
id: T-041
title: Write architecture review doc — 06 performance and scale
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/486
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/architecture-review/06-performance-and-scale.md` does not exist (verified). Every code site is already cited in T-037 / T-038 / T-039 reality docs:
  - T-037 §2 — 0-async/179-sync FastAPI route pattern (Starlette threadpool of 40).
  - T-037 §3 — AsyncIO essentially unused.
  - T-038 §5 — no state-management library on the frontend.
  - T-038 §8 — 18 polling sites (poll-heavy refresh).
  - T-039 §7 — SQLAlchemy `pool_size=5` default vs threadpool of 40 = pool saturation.
  - T-039 §8 — single Postgres + no caching layer.
  - T-024 §3.1 — `POST /predictor/backtest/run` is synchronous (no background queue).
  - `apps/api/Dockerfile:25` — uvicorn invoked without `--workers` flag (single process).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the verdict-driven architecture review of performance + scale.
  - `06-performance-and-scale.md` — 8-question verdict-driven assessment: (1) Single-worker uvicorn (no `--workers`, no Gunicorn), (2) Starlette threadpool-of-40 + SQLAlchemy pool-of-5 mismatch (synthesises T-037 §2 + T-039 §7), (3) Zero caching layer (no Redis, no in-process LRU caches), (4) Polling-everywhere frontend (18 setInterval sites synthesises T-038 §8), (5) No background job queue (long ops like backtest hit the API thread synchronously), (6) Largest modules (status_routes.py 4014 LOC, sql_repositories.py 6617 LOC, apiClient.ts 1879 LOC), (7) No profiling / APM / distributed tracing, (8) No CDN / static-asset caching headers / no edge runtime.
- **Step 3 (one-line change):** write one verdict-driven architecture review of performance + scale.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 8 architectural choices enumerated; 5-part verdict format applied to each; verdicts span at least 3 ratings; single-worker uvicorn verdicted; threadpool-vs-pool synthesis verdicted as risky/dominant finding; no-observability gap verdicted risky; recommendations deferred to Track 1c; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — monorepo (T-036), Python (T-037), frontend (T-038), data (T-039), testing (T-040) all merged. Security + ops (T-042 next).

## Goal

Produce one verdict-driven architecture review of performance + scale. The dominant story: the codebase is correct for single-user paper trading but has multiple stacked **scale ceilings** — single-worker uvicorn + 40-thread Starlette pool + 5-connection SQLAlchemy pool + zero caching + polling-everywhere frontend + synchronous long-op routes. Each is acceptable in isolation; combined, they put a hard ~100 RPS ceiling on the API. T-041 makes this stacking explicit.

## Context

`depends_on:` T-001 … T-010. T-037 §2 surfaced the async-incoherence problem; T-039 §7 surfaced pool tuning; T-038 §8 surfaced polling. T-041 synthesises perf observations + adds new infra-perf findings (uvicorn workers, no APM, no CDN).

## Touch scope

Create:
- `docs/architecture-review/06-performance-and-scale.md`

Read: T-037 / T-038 / T-039 / T-024 reality docs + `apps/api/Dockerfile` + `apps/web/Dockerfile`.

## Acceptance criteria

- [ ] Output file exists at `docs/architecture-review/06-performance-and-scale.md`.
- [ ] 8 architectural choices enumerated.
- [ ] 5-part verdict format applied to each.
- [ ] Verdicts span at least 3 ratings.
- [ ] Single-worker uvicorn deployment surfaced.
- [ ] Threadpool-vs-pool size mismatch synthesised from T-037 §2 + T-039 §7.
- [ ] No-caching-layer pattern verdicted.
- [ ] Recommendations deferred to Track 1c.
- [ ] No source modification.

## Out of scope

- All prior architecture-review docs (T-036-T-040 — merged siblings).
- Security + ops (T-042 — next).
- Summary (T-043 — last).
- Concrete fixes (Track 1c).
- Specific perf benchmarking (not in scope of the audit; T-041 verdicts the choices that determine perf, not measured perf).

## Verification

- File exists.
- 8 choices × 5-part verdict.
- Multi-rating distribution.
- Single-worker uvicorn surfaced.
- Threadpool-vs-pool mismatch synthesised.

## Notes

T-041 is the 6th of 8 Track 1b architecture review docs. The dominant pattern is **stacked scale ceilings**: each choice (single-worker uvicorn, sync routes, small DB pool, no caching, polling) is independently acceptable for the intended single-user paper-trading scope, but they compound. Phase 1c will need to decide whether to commit to the small-scale architecture (and document the ceiling) or invest in horizontal-scale upgrades (workers, async, pool tuning, caching, push-not-poll).
