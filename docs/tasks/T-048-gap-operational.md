```yaml
id: T-048
title: Write gap analysis doc — 05 operational gaps
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/gap-analysis/05-operational-gaps.md` does not exist (verified). T-041 (perf + scale) + T-042 (security + obs + ops) primary sources — 7 risky verdicts between them. T-044 + T-045 + T-046 + T-047 cross-referenced operational items as "belongs to T-048". T-048 inherits those.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the operational / security / observability / deployment gap analysis.
  - `05-operational-gaps.md` — gap-entry-per-gap for operational concerns: (1) Authentication topology undefined + zero auth on 179 routes, (2) Backup / DR tooling absent (AGENTS.md mandate violated), (3) Single-worker uvicorn deployment, (4) SQLAlchemy pool tuning vs Starlette threadpool, (5) No `TrustedHostMiddleware` / CORS / CSRF, (6) No API rate limiting, (7) Plain-text env vars / no SecretStr, (8) Unstructured logging (no structlog), (9) Healthchecks: no `/ready`, no `/metrics`, no Prometheus, (10) No background job queue, (11) Zero caching layer (no Redis, no LRU), (12) No APM / OpenTelemetry / distributed tracing, (13) No CDN / no static-asset caching headers, (14) Settings Categories 1 + 3 + 4 + 5 infrastructure absent, (15) Connection-lost ghost-order recovery gap.
- **Step 3 (one-line change):** write one gap-analysis doc enumerating operational gaps.
- **Step 4 (measurable):** yes — eight acceptance criteria: file exists; ≥ 12 operational gap entries; each entry uses the 6-part format; MoSCoW spans at least 3 ratings; effort spans at least 2 sizes; each entry cites originating reality doc; cross-reference to T-044/T-045/T-046/T-047 + T-049; AGENTS.md backup-mandate violation surfaced as critical; auth-topology decision surfaced as critical pre-deployment blocker; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — UI gaps (T-044), schema/incomplete (T-045), quant (T-046), AI provider (T-047), summary (T-049).

## Goal

Produce one gap-analysis doc focused on operational / security / observability / deployment gaps. The dominant gap-pair: **define deployment topology + add auth layer** (Critical pre-deploy blocker) + **add backup tooling** (AGENTS.md mandate explicitly violated, Critical). These two combined define whether the system can leave its current "localhost paper-trading scope" without being a security incident waiting to happen.

## Context

`depends_on:` T-006 (API infra), T-007 (worker scheduler), T-009 (infra/CI), T-029 (settings UI), T-041 (perf), T-042 (security + obs + ops — primary source). T-042's 4 risky + 3 outdated verdicts directly inform T-048 priorities.

## Touch scope

Create:
- `docs/gap-analysis/05-operational-gaps.md`

Read: T-006 + T-007 + T-009 + T-029 + T-041 + T-042 reality docs + T-044-T-047 cross-references.

## Acceptance criteria

- [ ] Output file exists at `docs/gap-analysis/05-operational-gaps.md`.
- [ ] ≥ 12 operational gap entries.
- [ ] Each entry uses the 6-part format.
- [ ] MoSCoW spans at least 3 ratings.
- [ ] Effort spans at least 2 sizes.
- [ ] Each entry cites originating reality doc.
- [ ] Cross-reference table to T-044/T-045/T-046/T-047 + T-049 included.
- [ ] AGENTS.md backup-mandate violation surfaced.
- [ ] Auth-topology decision surfaced as critical pre-deployment blocker.
- [ ] No source modification.

## Out of scope

- UI/feature gaps (T-044 — merged).
- Incomplete implementation (T-045 — merged).
- Quant gaps (T-046 — merged).
- AI integration gaps (T-047 — merged).
- Summary (T-049 — next, the last).

## Verification

- File exists.
- 6-part format consistent.
- AGENTS.md backup mandate surfaced as critical.
- Auth topology surfaced as critical pre-deployment blocker.
- Cross-reference table present.

## Notes

T-048 is the 5th of 6 Track 1c docs. The pattern across T-042 (architecture review) and T-048 (gap analysis) is identical: operational gaps are concentrated, severe, and at intent-vs-reality cliffs. The codebase has near-perfect audit-trail discipline + zero auth + zero backup tooling. Closing the operational gaps is what converts this codebase from "single-user paper trading on the operator's machine" into "production-ready service" — a category transition, not an incremental improvement.
