# Architecture Review 00 — Summary

**Scope.** Synthesis of the Track 1b architecture review — 7 verdict-driven docs across 56 architectural questions covering monorepo structure, Python stack, frontend stack, data + storage, testing + CI, performance + scale, and security + observability + ops. Each question received the locked 5-part verdict format (current implementation + state-of-the-art alternative + verdict + perf implication + concrete improvement). This summary is **the input** to Track 1c gap analysis — not its conclusion.

**Track 1b docs**: T-036 `01-monorepo-structure.md`, T-037 `02-python-stack.md`, T-038 `03-frontend-stack.md`, T-039 `04-data-and-storage.md`, T-040 `05-testing-and-ci.md`, T-041 `06-performance-and-scale.md`, T-042 `07-security-observability-ops.md`.

## 0. Aggregate verdict distribution

**56 architectural questions verdicted across 7 docs.**

| Verdict | Count | % |
|---------|-------|---|
| State-of-the-art | 11 | 20% |
| Acceptable | 13 | 23% |
| Outdated | 17 | 30% |
| Risky | 15 | 27% |

| Doc | SotA | Acceptable | Outdated | Risky | Total |
|-----|------|------------|----------|-------|-------|
| T-036 Monorepo | 1 | 3 | 3 | 1 | 8 |
| T-037 Python stack | 2 | 3 | 1 | 2 | 8 |
| T-038 Frontend stack | 3 | 0 | 3 | 2 | 8 |
| T-039 Data + storage | 2 | 2 | 2 | 2 | 8 |
| T-040 Testing + CI | 2 | 3 | 2 | 1 | 8 |
| T-041 Perf + scale | 0 | 2 | 3 | 3 | 8 |
| T-042 Security + obs + ops | 1 | 0 | 3 | 4 | 8 |
| **Totals** | **11** | **13** | **17** | **15** | **56** |

### Observations on the distribution

1. **~20% state-of-the-art is unusually high** for a Phase-1 product — most codebases at this stage have fewer "clear best practice" choices. The codebase has invested specifically in correctness-critical areas (data discipline, audit trails, test discipline) at the cost of generic infrastructure investments.

2. **~27% risky is also unusually high** — most codebases stay below 15-20%. The codebase has accepted more architectural risk than typical, concentrated in scaling + security + ops layers.

3. **The "middle" is thin** — only 23% acceptable. The codebase tends toward extremes: either clearly good or clearly concerning. Few choices are merely "fine".

4. **T-041 (perf) has zero state-of-the-art ratings; T-042 (security) has zero acceptable ratings** — these two layers are the weakest by design choice. Both received deferred attention relative to domain correctness.

## 1. The dominant meta-pattern: asymmetric discipline

The single most-repeated observation across all 7 docs: the codebase exhibits **asymmetric discipline** — extraordinary rigor at one layer paired with absence at an adjacent layer. The pattern surfaces in slightly different language in each doc:

| Doc | Asymmetry stated |
|-----|------------------|
| T-036 | "Tooling lags structure" — modern macro-split + 2018-era tooling layer |
| T-037 | "Async commitment incoherent" — async-first framework + 0 async routes |
| T-038 | "Bimodal stack" — modern framework + 2018-era data layer |
| T-039 | "Discipline at value layer + structure-debt at code layer" |
| T-040 | "Discipline at test layer + infrastructure-debt at support layer" |
| T-041 | "Defensible at intended scale, fragile beyond" |
| T-042 | "Audit-trail discipline + network-defense void" |

The same shape — **rigor concentrated at the domain / correctness layer, gaps at the supporting infrastructure layer** — appears in every architecture-review doc.

### Why this matters

The asymmetry has two interpretations:

1. **Charitable**: the team prioritised getting the financial / trading logic right (Decimal-as-string, audit chains, real-impl tests, 12-gate safety) and accepted infrastructure debt knowingly. The asymmetry is intentional triage.

2. **Less charitable**: the team has strong domain instincts but limited operational / scale / security experience. The infrastructure gaps are blind spots rather than choices.

The truth is probably a mix. Either way, the asymmetry is the system's defining architectural signature. Phase 1c gap analysis can either invest to close the asymmetry OR document it as the intentional posture.

## 2. The 4 strongest pieces (state-of-the-art highlights)

11 questions earned `state-of-the-art` verdicts. The 4 most consequential:

### 2.1 Decimal-as-string + `MONEY_NUMERIC = Numeric(20, 6)` discipline (T-039 §5)

The single clearest piece of financial-system discipline in the entire codebase. No floats anywhere except the `ibapi.Order` boundary (T-019 §3). 89 `MONEY_NUMERIC` columns. Pydantic + `Decimal` validators reject float assignment. JSON serialisation is string-preserving end-to-end.

This is the **gold standard** for financial Python in 2025. Most production fintech systems reach for this discipline only after a bug-driven incident. This codebase has it from the start.

### 2.2 53-migration linear Alembic chain (T-039 §3)

53 numbered + descriptively named migrations in linear order across the codebase's lifetime. No merges, no branches. The chain enables deterministic deployment via `alembic upgrade head`. The largest migration (~13 KB) is well-scoped to one feature; no mega-migrations.

This is the **cleanest organisational signal** in the codebase — same domain (storage schema) as the 3116-LOC `metadata.py` single file (verdicted outdated) but executed with discipline.

### 2.3 1% mock ratio in 240-file Python test suite (T-040 §2)

3 of 240 test files use mocks. The other 237 exercise real Pydantic models, real SQLAlchemy queries, real Decimal math, real Alembic migrations. The few mocks are at genuine external boundaries (IBKR, Anthropic, EODHD).

This is **extraordinary** for a codebase of this size. The Detroit-school real-impl pattern is the right call for financial systems (mock drift is a silent risk) but very few codebases achieve this discipline at scale.

### 2.4 8+ append-only `*_audit` tables + UNIQUE idempotency keys (T-042 §5)

`ibkr_submission_audit`, `reconciliation_audit`, `worker_run_audit`, `action_draft_audit`, `cold_start_seed_audit`, `watchlist_confirmation_audit`, `manual_review_queue`, `unmatched_execution_audit`, `ibkr_executions`. Every state-changing operation writes an append-only audit row. UNIQUE constraints on the natural-key axis enforce idempotency. Hash-chain provenance (T-017 + T-019) enables forensic reconstruction.

This satisfies AGENTS.md "Every decision must be logged" + "No advice without audit trail" mandates rigorously.

### Summary: the 4 highlights are concentrated in domain correctness

All 4 are at the **data + state-change layer**. The codebase's rigor is concentrated where the team correctly identified the highest stakes: financial precision, schema evolution, forensic audit. The investment in these layers is visible and high-quality.

## 3. The 4 weakest pieces (Critical Track 1c priorities)

15 questions earned `risky` verdicts. The 4 highest-priority for Track 1c:

### 3.1 Zero authentication on the API (T-042 §1)

179 FastAPI routes. Zero `Depends(...)` for authentication. Zero JWT / OAuth2 / cookie session handling. No user model. Any caller who reaches the API can call any route, including order submission (T-026's JA token is client-side only per T-026 §4 originating finding).

The verdict depends entirely on deployment topology, which is undocumented. At localhost-only: fine. At any LAN or public exposure: catastrophic.

### 3.2 No backup / DR tooling (T-042 §8)

AGENTS.md explicitly mandates "All data must be backed up and restorable" + "A backup is not trusted until restore is tested". The codebase has zero `pg_dump` scripts, zero restore procedures, zero DR runbook. The mandate is recorded; the enforcement is absent.

This is the most clear-cut case of **intent stronger than implementation** in the audit. The audit-chain rigor (§2.4) makes the loss of those chains particularly painful — the forensic history would be permanently destroyed.

### 3.3 Single-worker uvicorn deployment (T-041 §1)

`apps/api/Dockerfile:25` runs `uvicorn portfolio_outlook_api.main:app` with no `--workers` flag. One Python process, one GIL, one Starlette threadpool of 40 threads. Combined with §3.4 below, the API is effectively single-threaded for any CPU-bound work.

### 3.4 Threadpool-40 + DB-pool-5 mismatch (T-041 §2 + T-039 §7)

Starlette schedules 179 sync routes (T-037 §2) into a 40-thread pool. SQLAlchemy `create_engine` uses default `pool_size=5, max_overflow=10`. **15 max simultaneous DB connections × 40 threads** = pool saturation is the throughput ceiling, not Postgres throughput. Multi-tab dashboards (T-021 §3 + T-025 §9.10) trigger saturation at ~3-5 concurrent users.

### Summary: the 4 critical gaps cluster around scale + security

All 4 are infrastructure-layer concerns: production-deployment readiness (workers + pool), security (auth + backups). The domain layer is not implicated in any of the 4 critical gaps — the asymmetric-discipline pattern from §1 maps directly here.

## 4. The 17 recurring patterns observed

Across the 7 docs, several patterns repeated in different language but with the same underlying shape:

### 4.1 Patterns about discipline + rigor (concentrated at domain layer)

1. **Decimal-as-string discipline** (T-039 §5).
2. **Append-only audit doctrine** (T-042 §5 + multiple cross-refs).
3. **Real-implementation testing** (T-040 §2).
4. **mypy --strict universal coverage** (T-037 §3 — cross-ref to T-051 baseline).
5. **Pydantic v2 with `extra="forbid"`** (T-037 §4).
6. **Hash-chain provenance** (T-017 + T-019 — cross-ref).

### 4.2 Patterns about gaps + drift (concentrated at infrastructure layer)

7. **6 README-only stub packages** signal architectural intent that the codebase doesn't honor (T-036 §3).
8. **Tooling lags structure** (T-036 §9.1).
9. **Async commitment incoherent** (T-037 §9.1).
10. **Hand-rolled where ecosystem has solutions** (T-038 §9.2 — OpenAPI codegen, TanStack Query, Tailwind all skipped).
11. **60% "use client" defeats App Router RSC** (T-038 §9.3).
12. **Missing tiers between Python and Postgres** (T-039 §9.2 — no Redis, no pgBouncer, no read replicas).
13. **No measurement layer** (T-040 §9.3 + T-041 §9.2 + T-042 — no coverage, no APM, no metrics).
14. **Stacked scale ceilings** (T-041 §9.1).
15. **Audit-trail discipline + network-defense void** (T-042 §9.1).
16. **Intent stronger than implementation** (T-042 §9.2 — AGENTS.md backup mandate).
17. **Every gap dormant at intended scope, severe beyond** (T-041 §9.3 + T-042 §9.3).

### 4.3 The unifying observation

Patterns 1-6 ("discipline") concentrate at the **domain / correctness** layer. Patterns 7-17 ("gaps") concentrate at the **infrastructure / supporting** layer. The split is clean. No pattern straddles both halves.

## 5. Track 1c priority roll-up

Each Track 1b doc nominated Track 1c follow-up items at Critical / High / Medium / Low priority. Roll-up across all 7 docs:

### 5.1 Critical (2 items)

- **T-042 §1 — Define deployment topology** + add auth layer if anything beyond localhost. Architectural blocker for any non-localhost deployment.
- **T-042 §8 — Backup tooling** + restore procedure + test the restore. AGENTS.md mandate explicitly violated.

### 5.2 High (~10 items)

- T-036 §2 — Workspace manager (uv workspaces).
- T-036 §3 — Resolve 6 stub packages (delete OR populate).
- T-037 §7 — Relax `ibapi==9.81.1.post1` exact pin.
- T-038 §5 — Adopt TanStack Query (state mgmt).
- T-038 §6 — OpenAPI codegen for TS types.
- T-038 §7 — Tailwind + shadcn/ui (design tokens).
- T-038 §8 — Replace polling with query-cache + SSE.
- T-039 §7 — SQLAlchemy pool tuning (pre-prod blocker).
- T-040 §4 — Add `coverage.py` + `pytest-cov` + CI gate.
- T-041 §1 — Gunicorn + multi-worker uvicorn.
- T-041 §3 — Add Redis caching layer.
- T-041 §7 — OpenTelemetry instrumentation.
- T-042 §2 — TrustedHostMiddleware + CORS.
- T-042 §7 — `/ready` + `/metrics` endpoints.

### 5.3 Medium (~10 items)

- T-036 §4 — Replace Makefile with `just` or `nx`.
- T-036 §6 — Extract shared per-package tool config.
- T-039 §2 — Split `metadata.py` by domain area.
- T-039 §6 — Split `sql_repositories.py` or generic base class.
- T-040 §3 — Add `conftest.py` with shared fixtures.
- T-040 §5 — Add `pytest-xdist` for test parallelism.
- T-040 §8 — Contract tests via OpenAPI schema.
- T-041 §5 — Background job queue (RQ + Redis).
- T-042 §3 — `slowapi` rate limiting.
- T-042 §4 — `SecretStr` for API keys.
- T-042 §6 — `structlog` structured logging.

### 5.4 Low (multiple items)

- T-036 §1 / §5 / §8 — minor monorepo + CI improvements.
- T-038 §4 — Audit "use client" boundaries.
- T-039 §1 / §4 — Postgres-via-Testcontainers + JSON Pydantic validation.
- T-040 §6 / §7 — pytest markers + matrix-strategy CI.
- T-042 §1 — Track 1c could also recommend documenting the localhost-only posture explicitly if that's the chosen path.

### 5.5 Track 1c priorities are uneven across the 7 docs

| Doc | Critical | High | Medium | Low |
|-----|----------|------|--------|-----|
| T-036 Monorepo | 0 | 2 | 2 | 4 |
| T-037 Python stack | 0 | 1 | 1 | 6 |
| T-038 Frontend stack | 0 | 4 | 0 | 4 |
| T-039 Data + storage | 0 | 1 | 2 | 5 |
| T-040 Testing + CI | 0 | 1 | 3 | 4 |
| T-041 Perf + scale | 0 | 5 | 1 | 2 |
| T-042 Security + obs | 2 | 3 | 3 | 0 |

Track 1c will inherit a heavy security/perf/frontend agenda + lighter monorepo/Python/testing/data agenda. The data layer (T-039) and Python language (T-037) earned the lowest follow-up counts — the verdicts there were closest to "already correct".

## 6. What Track 1b did not assess

By scope (per the architecture-review/README mandate "recommendations belong in the gap analysis, not here"), Track 1b verdicted choices without prescribing fixes. Specifically out of scope for Track 1b but in scope for Track 1c:

- **Concrete implementation plans** for any of the §5 items.
- **Effort estimates** in story points / weeks.
- **Sequencing** — which fix unblocks which.
- **MoSCoW** prioritisation (Must / Should / Could / Won't).
- **Cost-benefit analysis** for each fix.

Track 1c (T-044-T-049 — 6 gap-analysis docs) will produce these.

## 7. The 8 closed Track 1a → Track 1b cross-references

Several Track 1b verdicts were direct re-surfacings of Track 1a reality findings. Sample cross-references:

| Track 1a originating finding | Track 1b verdict | Why it matters |
|------------------------------|--------------------|----------------|
| T-019 §4.8 — `cancel_order` not wired in worker | T-042 §1 — Zero auth (client-side ritual only) | Both stem from "no defense-in-depth beyond UI gates" |
| T-020 §10.1 — `IbkrReconciler.tick` not wired to APScheduler | T-041 §5 — No background queue + T-042 §7 — Minimal healthchecks | Operational gap surfaces in multiple architecture layers |
| T-022 §6 — TOB-net expected return not implemented | T-038 §5 — No state management library | Both reflect "compute primitive exists, wrapping layer absent" |
| T-024 §10.11 — Weight floor 5% vs intent 10% | (numeric drift; Track 1c will reconcile) | First numeric contradiction found in Track 1a |
| T-026 §6 — "Future update" banner is accidentally truthful (T-034) | T-042 §1 — Audit trail vs auth asymmetry | The codebase's UI text often lags its implementation reality |

Track 1c will collate these cross-references into concrete fix proposals.

## 8. The verdict on the verdicts

In one sentence: **The codebase is exceptionally well-built where it had to be (data + state-change discipline) and exceptionally under-built where it could afford to be (network defense + production-deployment infrastructure), and the asymmetry is consistent enough to be a deliberate design posture.**

Track 1c gap analysis can:
1. **Close the asymmetry** by investing in network + scale + ops infrastructure. Heavy lift but uniform-quality result.
2. **Document the asymmetry** as the intentional single-user paper-trading posture + constrain deployment to match. Lighter lift but limits the system's scaling future.

Either path is defensible; the choice belongs to Track 1c + downstream phases.

## 9. References

- `docs/architecture-review/01-monorepo-structure.md` (T-036)
- `docs/architecture-review/02-python-stack.md` (T-037)
- `docs/architecture-review/03-frontend-stack.md` (T-038)
- `docs/architecture-review/04-data-and-storage.md` (T-039)
- `docs/architecture-review/05-testing-and-ci.md` (T-040)
- `docs/architecture-review/06-performance-and-scale.md` (T-041)
- `docs/architecture-review/07-security-observability-ops.md` (T-042)
- `docs/architecture-review/README.md` (the track scope)
- All Track 1a reality docs referenced through Track 1b cross-refs.

## 10. Closes Track 1b

T-043 closes the 8-doc Track 1b Architecture Review (T-036-T-043). With Track 1b complete, the audit moves to:

- **Track 1c Gap Analysis** (T-044-T-049): 6 docs analysing concrete fixes informed by Track 1b verdicts.
- **Functional-review additions** (T-011b, T-011c, T-012b, T-016b, T-021b): 5 carry-forward tasks from the 2026-05-26 brainstorm.

Phase 1 audit total tasks remaining after T-043 merges: **11** (6 gap analysis + 5 functional-review additions).
