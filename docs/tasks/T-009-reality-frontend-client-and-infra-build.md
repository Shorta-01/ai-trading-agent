```yaml
id: T-009
title: Write reality docs for the frontend client/text layer and the infra/build layer
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
