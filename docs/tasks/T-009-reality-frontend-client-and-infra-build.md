```yaml
id: T-009
title: Write reality docs for the frontend client/text layer and the infra/build layer
phase: P1
status: pr-open
source: brainstorm
owner: claude
created: 2026-05-26
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/450
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** all three target files under `docs/reality/components/` do not exist (verified). 19 source files (~3098 LoC) + 2 intent docs (`docs/deployment.md` 197 lines, AGENTS.md 34 lines) read in parallel by three subagents:
  - Agent A — web client/text: `apps/web/lib/apiClient.ts` (1879), `apps/web/lib/uiText.ts` (9), `apps/web/next.config.ts` (7), `apps/web/playwright.config.ts` (38), `apps/web/vitest.config.ts` (20), `apps/web/eslint.config.mjs` (19), `apps/web/vitest.setup.ts` (1) ≈ 1973 lines.
  - Agent B — infra/docker: `apps/api/Dockerfile` (25), `apps/web/Dockerfile` (27), `apps/worker/Dockerfile` (21), `infra/docker/docker-compose.yml` (70), `infra/docker/.env.example`, `infra/docker/README.md` (79), `docs/deployment.md` (197 — intent) ≈ 419 lines.
  - Agent C — build/CI/scripts: `Makefile` (17), repo-root `pyproject.toml` (35), `.github/workflows/ci.yml` (277), `.github/workflows/code-health.yml` (199), `scripts/check_product_tracking.py` (184), `scripts/project_status.py` (82), AGENTS.md (34) ≈ 828 lines.
- **Step 2 (one-line per touched file):** three target files do not exist; each holds one cluster reality doc:
  - `web-api-client-and-text.md` — `apiClient.ts` method catalogue (endpoint → method → return type) + `uiText.ts` registry summary + the three config files (next/playwright/vitest) + eslint config + vitest setup.
  - `infra-docker-and-compose.md` — per-image Dockerfile structure (api/web/worker), docker-compose.yml services + env-var → settings-class mapping, `.env.example`, deployment intent.
  - `build-ci-and-scripts.md` — Makefile targets, repo-root `pyproject.toml`, both CI workflows (ci.yml + code-health.yml) with trigger + job matrix + tool calls, both Python scripts.
- **Step 3 (one-line change):** write three cited reality docs covering the entire web client/text + infra + build/CI tree, no source modified.
- **Step 4 (criteria measurable):** yes — six acceptance criteria: three files exist; `apiClient.ts` method catalogue (endpoint → method → return type with refs); locked Dutch microcopy registry (`uiText.ts`) summarised; per-image Dockerfile structure documented; `docker-compose.yml` services + env-var → settings-class mapping; CI workflows enumerated (every workflow's trigger + job matrix + tool calls — must equal `ls .github/workflows/*.yml`: `ci.yml` + `code-health.yml`); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — pages + components (T-008); test files themselves (read for behaviour, not catalogued); branch-protection policy (lives in `docs/tasks/_branch-protection-checklist.md`).

## Goal

Produce three reality docs: the frontend API-client / locked-text layer, the Docker/Compose layer, and the build/CI/scripts layer.

## Context

`depends_on:` —. Intent inputs: `docs/deployment.md`, AGENTS.md.

## Touch scope

Create:
- `docs/reality/components/web-api-client-and-text.md`
- `docs/reality/components/infra-docker-and-compose.md`
- `docs/reality/components/build-ci-and-scripts.md`

Read: `apps/web/lib/apiClient.ts`, `apps/web/lib/uiText.ts`, `apps/web/{next,playwright,vitest}.config.ts`, `apps/web/eslint.config.mjs`, `apps/web/vitest.setup.ts`, `apps/{api,web,worker}/Dockerfile`, `infra/docker/{docker-compose.yml,.env.example,README.md}`, `Makefile`, repo-root `pyproject.toml`, `.github/workflows/*.yml`, `scripts/*.py`, `docs/deployment.md`, AGENTS.md.

## Acceptance criteria

- [ ] Three output files at the locked filenames.
- [ ] `apiClient.ts` method catalogue: endpoint → method name → return type sketch + cited refs.
- [ ] Locked Dutch microcopy registry (`uiText.ts`) summarised with refs.
- [ ] Dockerfile structure per image (api / web / worker): base, stages, install, run; multi-stage notes for web.
- [ ] `docker-compose.yml` services + env-var → settings-class mapping.
- [ ] CI: every workflow's trigger + job matrix + tool calls (ruff, mypy, pytest, npm lint/test/build/e2e, code-health), with refs.
- [ ] No source / config modification.

## Out of scope

- Frontend pages and components (T-008).
- Test FILES themselves (read for behaviour, do not catalogue every test).
- Branch-protection policy (lives in `docs/tasks/_branch-protection-checklist.md`).

## Verification

- All three files exist.
- Workflow catalogue matches `ls .github/workflows/*.yml`.

## Notes

`web-api-client-and-text.md` content overlaps slightly with T-008 (which references apiClient consumption). Document the client itself here; T-008 documents how pages/components use it.
