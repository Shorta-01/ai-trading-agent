```yaml
id: T-042
title: Write architecture review doc — 07 security observability ops
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/487
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/architecture-review/07-security-observability-ops.md` does not exist (verified). Every code site is already cited in T-006 / T-007 / T-009 / T-019 / T-020 / T-041 reality docs:
  - T-006 — API infrastructure (no auth in scope).
  - T-007 — worker scheduler + `worker_run_audit` heartbeat.
  - T-009 — `.env.example` bare keys silent-drop finding.
  - T-019 — `ibkr_submission_audit` + `ibkr_submission_lifecycle` + `ibkr_executions` (3 audit tables).
  - T-020 — `reconciliation_audit` + `reconciliation_run_audit` + `unmatched_execution_audit` + `manual_review_queue` (4 audit tables).
  - T-041 §7 — no APM / no profiling already verdicted risky.
  - T-053 — bandit baseline (1 B101 assert-pattern finding only).
  - T-054 — pip-audit (1 HIGH fastapi MAL CVE).
  - T-058 — npm audit (1 HIGH next umbrella with 22 GHSAs).
  - `apps/api/src/portfolio_outlook_api/main.py:111` — single /health endpoint.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the verdict-driven architecture review of security + observability + operations.
  - `07-security-observability-ops.md` — 8-question verdict-driven assessment: (1) Zero authentication / authorization on API routes, (2) Zero CORS / CSRF / TrustedHost middleware, (3) No API rate limiting, (4) Plain-text env vars (no SecretStr, no vault integration), (5) Append-only audit tables (8+ named `*_audit` + UNIQUE idempotency keys — the standout state-of-the-art piece), (6) Unstructured logging (`logging.basicConfig` only, no structlog), (7) One /health endpoint, no /ready / /metrics / Prometheus, (8) No backup / DR tooling visible (no pg_dump scripts, no restore procedures).
- **Step 3 (one-line change):** write one verdict-driven architecture review of security + observability + operations.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 8 architectural choices enumerated; 5-part verdict format applied to each; verdicts span at least 3 ratings; zero-auth pattern verdicted risky (dominant security finding); append-only audit pattern verdicted state-of-the-art (standout praise); AGENTS.md "All data must be backed up and restorable" mandate cross-referenced; recommendations deferred to Track 1c; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — all prior architecture-review docs (T-036-T-041) merged. Summary (T-043 — last) will synthesize.

## Goal

Produce one verdict-driven architecture review of security + observability + operations. The dominant story: a codebase with **rigorous audit-chain discipline** (8+ append-only `*_audit` tables, UNIQUE idempotency keys, hash chains) but **zero traditional auth/authz infrastructure**. The intended single-user / single-tenant scope makes auth not strictly necessary, but the absence of even basic CORS / CSRF / rate-limiting layers means the system has no defense-in-depth if the deployment topology ever changes.

## Context

`depends_on:` T-001 … T-010 (all reality docs). T-019 / T-020 inventoried the audit tables. T-053 / T-054 / T-058 ran security baseline scans. T-041 §7 already verdicted observability as risky from a perf angle. T-042 widens to the full security / observability / ops surface.

## Touch scope

Create:
- `docs/architecture-review/07-security-observability-ops.md`

Read: T-006 / T-007 / T-009 / T-019 / T-020 / T-041 / T-053 / T-054 / T-058 reality docs + `apps/api/src/portfolio_outlook_api/main.py`.

## Acceptance criteria

- [ ] Output file exists at `docs/architecture-review/07-security-observability-ops.md`.
- [ ] 8 architectural choices enumerated.
- [ ] 5-part verdict format applied to each.
- [ ] Verdicts span at least 3 ratings.
- [ ] Zero-auth pattern verdicted risky as dominant security finding.
- [ ] Append-only audit-table pattern verdicted state-of-the-art (the standout piece).
- [ ] AGENTS.md "All data must be backed up and restorable" mandate cross-referenced.
- [ ] No source modification.

## Out of scope

- All prior architecture-review docs (T-036-T-041 — merged siblings).
- Summary (T-043 — last).
- Code-health findings deep dive (T-050-T-059 already merged).
- Performance-specific observability (T-041 §7 already covers).
- Concrete fixes (Track 1c).

## Verification

- File exists.
- 8 choices × 5-part verdict.
- Multi-rating distribution.
- Zero-auth surfaced as dominant security finding.
- Audit-table pattern verdicted state-of-the-art.

## Notes

T-042 is the 7th of 8 Track 1b architecture review docs. The codebase exhibits an unusual asymmetry: extraordinary discipline at the **forensic / audit-trail** layer (every state change is recorded with idempotency keys, hash chains, content-addressed provenance — see T-017, T-019, T-020) but **near-zero defense at the network / authn / authz layer**. This is consistent with the "single-user paper trading on the operator's own machine" scope, but creates a brittle deployment posture: any move toward multi-user, public-internet, or cloud deployment requires a security-architecture rebuild from zero.
