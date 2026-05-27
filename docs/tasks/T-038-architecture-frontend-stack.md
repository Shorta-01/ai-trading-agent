```yaml
id: T-038
title: Write architecture review doc — 03 frontend stack
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

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/architecture-review/03-frontend-stack.md` does not exist (verified). Every code site is already cited in T-008 + T-009 reality docs + T-036:
  - T-008 — frontend pages + components + grids (16 pages, 30 non-test components).
  - T-009 — `apiClient.ts` (~1879 LOC) + infra/Docker/CI for web.
  - T-036 §7 — frontend isolation verdicted state-of-the-art.
  - `apps/web/package.json`, `apps/web/tsconfig.json`, `apps/web/eslint.config.mjs`, `apps/web/next.config.ts`.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the verdict-driven architecture review of the frontend stack.
  - `03-frontend-stack.md` — 8-question verdict-driven assessment: (1) Next.js 15.2.6 + App Router, (2) React 19.0.1, (3) TypeScript 5.7.2 + strict, (4) Client/Server component split (29 of 48 `"use client"`), (5) No state-management library, (6) Manual fetch wrappers + 1879-line apiClient.ts, (7) Inline styles + globals.css (no Tailwind), (8) Polling-heavy data refresh (18 `setInterval` sites).
- **Step 3 (one-line change):** write one verdict-driven architecture review of the frontend stack.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 8 architectural choices enumerated; 5-part verdict format applied to each; verdicts span at least 3 ratings; client-heavy "use client" pattern verdicted; no-state-mgmt-library pattern verdicted; manual-apiClient pattern verdicted (cross-ref T-009); recommendations deferred to Track 1c; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — Python stack (T-037 — merged sibling), data + storage (T-039 — next), testing + CI (T-040 — future).

## Goal

Produce one verdict-driven architecture review of the frontend stack — Next.js + React + TypeScript versions, the App Router with client/server component split, state management (or lack thereof), data fetching pattern, styling, polling. The dominant story: a modern (React 19, Next 15) but conservative frontend that has not adopted any data-fetching library (no React Query / SWR / Zustand) — every component manages its own useState + useEffect + setInterval polling. This is the inverse of the Python stack: there, modern framework + conservative async usage; here, modern framework + conservative state management.

## Context

`depends_on:` T-001 … T-010 (reality docs). T-008 + T-009 inventoried what exists; T-038 verdicts the language + framework choices for the frontend.

## Touch scope

Create:
- `docs/architecture-review/03-frontend-stack.md`

Read: T-008 + T-009 reality docs + `apps/web/package.json` + `tsconfig.json` + `eslint.config.mjs` + `next.config.ts`.

## Acceptance criteria

- [ ] Output file exists at `docs/architecture-review/03-frontend-stack.md`.
- [ ] 8 architectural choices enumerated (Next.js 15, React 19, TS 5.7, "use client" split, state mgmt, fetch wrappers, styling, polling).
- [ ] 5-part verdict format applied to each.
- [ ] Verdicts span at least 3 ratings.
- [ ] "use client" 60% pattern explicitly verdicted (counts cited from grep).
- [ ] No-state-management-library pattern verdicted.
- [ ] 1879-line `apiClient.ts` manual-types pattern verdicted (cross-ref T-009 §2).
- [ ] No source modification.

## Out of scope

- Monorepo structure (T-036 — merged).
- Python stack (T-037 — merged).
- Data + storage (T-039 — next).
- Testing + CI deep dive (T-040 — future).
- Performance + scale (T-041 — future).
- Security + ops (T-042 — future).
- Summary (T-043 — last).
- Concrete fixes (Track 1c).

## Verification

- File exists.
- 8 choices × 5-part verdict.
- Multi-rating distribution.
- "use client" count grep-proven.
- T-009 cross-reference cited.

## Notes

T-038 is the 3rd of 8 Track 1b architecture review docs. The dominant pattern is **modern framework + conservative state**. React 19 + Next 15 are recent (released 2024-Q4); the codebase migrated quickly. But the data layer is hand-rolled — no React Query / SWR / Zustand. Every component polls via its own setInterval, manages local state, re-fetches on every render. This is the kind of architecture that scales fine for ~10 users with a few open tabs but degrades quickly past that. Phase 1c will need to decide whether to adopt a data layer.
