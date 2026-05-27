# Architecture Review 01 — Monorepo Structure

**Scope.** Verdict-driven assessment of the repository's structural choices. 8 architectural questions, each with the locked 5-part format: current implementation (with file refs) + state-of-the-art alternative (named patterns) + verdict (`state-of-the-art` / `acceptable` / `outdated` / `risky`) + performance implication + concrete improvement. Recommendations belong in Track 1c gap analysis; T-036 captures verdicts only.

**Reality docs referenced**: T-001-T-010 (component reality across `apps/` + `packages/`), T-010 specifically for the 6 stub packages, T-009 for infra/CI.

## 0. Verdict matrix at a glance

| # | Architectural choice | Verdict |
|---|----------------------|---------|
| 1 | Apps + packages layout (`apps/` × 3 + `packages/` × 9) | **Acceptable** |
| 2 | No workspace manager (no `uv`, no `pnpm-workspace.yaml`, no Bazel/Nx) | **Outdated** |
| 3 | 6 of 9 packages are README-only stubs | **Risky** |
| 4 | Makefile orchestration (`test / lint / typecheck / web-build`) | **Outdated** |
| 5 | Per-app CI jobs (7 separate workflow jobs) | **Acceptable** |
| 6 | Per-package dev-tool config duplication (each `pyproject.toml` re-declares ruff/mypy) | **Outdated** |
| 7 | Frontend isolation (only `apps/web` is TypeScript; rest is Python) | **State-of-the-art** |
| 8 | Docker/infra layout (`infra/docker/` separate from `apps/`) | **Acceptable** |

**Distribution**: 1 state-of-the-art, 3 acceptable, 3 outdated, 1 risky. No pat-on-back overall; the structure is sound at the macro level but needs modernisation at the tooling layer.

## 1. Apps + packages layout

### Current implementation

The repo splits into two top-level conceptual buckets per T-001-T-010:

- **`apps/`** — 3 deployable units:
  - `apps/api/` (FastAPI service; T-005, T-006)
  - `apps/worker/` (APScheduler + IBKR adapter; T-007)
  - `apps/web/` (Next.js + React frontend; T-008, T-009)
- **`packages/`** — 9 internal libraries:
  - 3 with source: `packages/domain/` (T-001, 4 reality files), `packages/portfolio/` (T-002, 4 reality files), `packages/storage/` (T-003)
  - 6 README-only stubs: `packages/ai/`, `packages/analytics/`, `packages/audit/`, `packages/data_providers/`, `packages/risk/`, `packages/tax/` (T-010 — all 6 documented as architectural signal)

Root configs: `pyproject.toml` (tooling-only — code-health tools per `:1-30`), `Makefile` (per-app commands per §4), `.github/workflows/ci.yml` (per-job CI per §5).

### State-of-the-art alternative

The `apps/` + `packages/` (or `apps/` + `libs/`) bifurcation is the **Nx + Turborepo + pnpm-workspaces** pattern — battle-tested across thousands of mid-to-large monorepos. The distinction "apps deploy, packages compile into apps" is the explicit Lerna / Nx model. Same idea also surfaces in `cargo workspaces` (Rust) and `go.mod` workspaces.

### Verdict — Acceptable

The conceptual split is correct. The packages-deploy-into-apps mental model is widely understood. Where it falls down is the lack of an enforcement layer (§2) — without a workspace manager, the layout is convention, not constraint.

### Performance implication

Negligible at the layout level. The structure neither helps nor hinders build performance. Per T-009, the per-app `pyproject.toml` setups mean each app's Docker build can scope its dependency tree narrowly — that IS a perf win at the per-app level, attributable to the layout.

### Improvement direction (for Track 1c)

Either:
- Adopt `uv` workspace mode (released 2024, native multi-package workspace support), OR
- Document the convention explicitly in a `MONOREPO.md` at root so contributors don't need to reverse-engineer the pattern.

## 2. No workspace manager

### Current implementation

There is no Python workspace manager. Each Python package has its own `pyproject.toml`:
- `packages/domain/pyproject.toml`
- `packages/portfolio/pyproject.toml`
- `packages/storage/pyproject.toml`
- `apps/api/pyproject.toml`
- `apps/worker/pyproject.toml`

The frontend has no `pnpm-workspace.yaml` or `npm` workspaces declaration. `apps/web/package.json` stands alone.

Inter-package dependencies are pulled via local-path installs (e.g., `apps/api/pyproject.toml` lists `packages/domain` via path syntax). No central lockfile; each package has (or would have) its own.

### State-of-the-art alternative

- **Python**: `uv workspace` (released 2024-Q2) — single root `pyproject.toml` with member declarations, single lockfile, parallel install. Or `rye workspace`. Or older but proven: `pdm` workspaces.
- **JavaScript**: `pnpm workspaces` (single workspace lockfile, hard-link dedup, fastest install). Or `nx` (which sits on top).
- **Combined**: `mise.toml` for tool versioning across multiple language stacks.

### Verdict — Outdated

The pattern of "one `pyproject.toml` per package" was the standard 2019-2022. Modern (2024+) Python tooling explicitly supports workspaces. The repo's split-pyproject pattern produces:
- N lockfiles (one per package).
- N `.venv` directories per developer.
- Re-installs on every dependency change.
- CI dependency caching is per-package, not shared.

### Performance implication

**Significant cold-start cost**. A fresh `git clone + per-package pip install -e .` walks N package indexes, resolves N times, downloads duplicated transitive deps N times. With `uv workspaces`, the same operation is O(unique_packages), not O(N × unique_packages).

Per T-009 CI walkthrough: each of the 7 CI jobs (domain / portfolio / storage / api / worker / web + 2 others) runs its own setup. A unified workspace setup could share the install step across 5-6 jobs.

### Improvement direction (for Track 1c)

`uv workspace` is the clear migration target. Single root `pyproject.toml` declares members; per-package `pyproject.toml` declares its inputs; one root `uv.lock`. CI install step becomes `uv sync` once at the matrix-job level.

## 3. The 6 stub packages

### Current implementation

Per T-010 reality doc, 6 of 9 packages under `packages/` are **README-only stubs**:
- `packages/ai/`
- `packages/analytics/`
- `packages/audit/`
- `packages/data_providers/`
- `packages/risk/`
- `packages/tax/`

None have `pyproject.toml`. None have `src/`. None are importable. Each contains only a `README.md` describing intent.

T-010 §3 documented that **the actual implementation lives elsewhere** — e.g., AI logic lives in `apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py` (T-006, T-023); tax logic lives in `packages/portfolio/src/portfolio_outlook_portfolio/belgian_tax.py` (T-022); audit chains live in storage tables (T-003). The "named stub without source" pattern documents intent but does not enforce structure.

### State-of-the-art alternative

There are two reasonable patterns:
- **Empty-module roadmap stubs**: each stub has a minimal `pyproject.toml` + `src/<package>/__init__.py` with no real code. Imports work; the structure enforces "here's where this should land". Used by many large monorepos to signal future structure.
- **No stub at all**: delete the README directories. The roadmap lives in a single ROADMAP.md at root.

The current state — README-only directories — is **neither**. It signals intent but cannot be imported, cannot be tested, and the actual implementations are scattered across already-existing packages.

### Verdict — Risky

The stubs create two specific risks:
1. **Cognitive confusion** — new contributors see `packages/ai/` and assume AI lives there. T-010 documents this explicitly: "named-stub-without-source pattern recorded as architectural signal".
2. **Misleading architecture diagrams** — any diagram that lists the `packages/` directory shows 9 packages; in reality only 3 ship code. Documentation and reality drift.

The risk is not safety-critical (no order-execution path goes through the stubs), but it's a maintenance-time hazard. T-010 §3 already documented the architecture risk.

### Performance implication

Zero direct perf impact (the stubs don't import). Indirect: developer time wasted investigating where features actually live. Per T-022's Belgian tax surface, T-023's AI surface, T-001's domain types — these are scattered when the stub names suggest co-location.

### Improvement direction (for Track 1c)

Either move the implementations into the named stubs (high-cost refactor), or delete the stubs + record the design intent in a single roadmap doc (low-cost; T-010 already laid the groundwork). Track 1c will decide.

## 4. Makefile orchestration

### Current implementation

`Makefile` at repo root, 18 LOC:

```make
.PHONY: test lint typecheck web-build

test:
	cd apps/api && pytest
	cd apps/worker && pytest

lint:
	cd apps/api && ruff check .
	cd apps/worker && ruff check .
	cd apps/web && npm run lint

typecheck:
	cd apps/api && mypy src
	cd apps/worker && mypy src

web-build:
	cd apps/web && npm run build
```

The `Makefile` is the only cross-language orchestration layer. It is **incomplete**:
- No target for the 3 Python packages (`domain`, `portfolio`, `storage`).
- No target for frontend type-check (`cd apps/web && npm run typecheck`).
- No target for `alembic` migrations.
- No target for the integration test suite.
- No `clean`, `setup`, or `bootstrap` target.

### State-of-the-art alternative

- **`just`** (rust-written task runner): modern syntax, supports per-target documentation, recipe parameters, alias targets.
- **`nx run-many`**: cross-language task orchestration with parallelism + caching.
- **`turbo` (Turborepo)**: JS-focused but supports any-language tasks; build-graph aware.
- **`mise tasks`**: language-version-aware task runner built into mise.

### Verdict — Outdated

Makefile orchestration was state-of-the-art ~2010-2018. By 2024 standards, Make's quirks (tab-vs-space, shell escaping, lack of dependency tracking for tasks) are a hindrance. The Makefile here also doesn't cover much of the actual surface — developers fall back to direct `cd apps/X && cmd` commands.

The biggest "outdated" tell: no parallelism. `make test` runs api tests then worker tests serially. With `just` or `nx`, `just test-all` could parallelise.

### Performance implication

**Serial execution**. The CI workflow does parallelise (per §5) but local dev `make test` does not. A full local test run is ~2× slower than it could be with a parallel orchestrator.

### Improvement direction (for Track 1c)

Migrate to `just` or `nx`. Add the missing targets (3 packages, frontend type-check, alembic). Track 1c.

## 5. Per-app CI jobs

### Current implementation

`.github/workflows/ci.yml` defines 7+ separate jobs:
- `domain` — packages/domain tests + lint + typecheck
- `portfolio` — packages/portfolio tests + lint + typecheck
- `storage` — packages/storage tests + lint + typecheck
- `api` — apps/api tests + lint + typecheck
- `worker` — apps/worker tests + lint + typecheck
- `web` — apps/web build + tests + lint

Each job has its own checkout, setup-python (or setup-node), install, and run steps. Each step has retry logic for the checkout (3 attempts with backoff per T-009 finding).

### State-of-the-art alternative

- **Matrix-based job**: single job definition with `strategy.matrix.package: [domain, portfolio, storage, api, worker, web]`. Same parallelism, less YAML duplication, easier to add a 7th package.
- **Build-graph driven**: `nx affected` only runs tests for packages touched by the PR's diff. Massive CI time savings on incremental PRs.
- **`turbo run`**: cache-aware; if `domain` hasn't changed, the test step is skipped entirely (cache hit).

### Verdict — Acceptable

The per-job split achieves the goal (parallelism + isolation). The YAML duplication is verbose but readable. Adding a 7th package would require copy-pasting ~30 LOC of YAML — annoying but not catastrophic.

The acceptable rating reflects: the CHOICE is fine; the EXECUTION is verbose. It's neither dangerous nor modernised.

### Performance implication

CI runtime is bounded by the slowest of the 7 jobs (well-parallelised). Cold-start time per job is wasteful (each repeats checkout + install). With caching, this is acceptable.

T-058's `npm audit` baseline (per merged T-058 PR) showed the web job has the longest install step (~minutes for node_modules). Splitting it from the Python jobs lets Python jobs complete while web compiles.

### Improvement direction (for Track 1c)

Migrate to `strategy.matrix` for DRY-ness. Consider `nx affected` if PR frequency justifies the setup cost. Track 1c.

## 6. Per-package dev-tool config duplication

### Current implementation

Each of the 5 Python `pyproject.toml` files declares its own:
- `[tool.ruff]` config
- `[tool.mypy]` config
- `[tool.pytest]` config
- Per-package `dependencies` / `dev-dependencies`

The root `pyproject.toml` (`:1-30`) ONLY declares the code-health cross-cutting tools (vulture, bandit, radon — per T-009 finding). It does NOT define an extends-from root for ruff or mypy.

Per T-009: minor drift exists between the 5 ruff configs — line-length values match (120) but per-file ignores differ. No central rule says "all packages must inherit from `tools/ruff.toml`".

### State-of-the-art alternative

- **Root config + extends**: `[tool.ruff]` at root + `extends = "../ruff.toml"` in each package's `pyproject.toml`. Ruff supports this since 0.1.
- **Mypy config inheritance**: `mypy.ini` at root + per-package overrides for path mapping only.
- **Shared `[tool.pytest]` in `pytest.ini`** at root + per-package opt-in.

The current pattern is the OLD pattern — 2020-era Python project layout assumed each package was standalone.

### Verdict — Outdated

The duplication is real risk: a future ruff version that changes default rules requires editing 5 files. The drift T-009 documented (per-file ignores diverging) is a present hazard. A code-health PR that wants to bump ruff to a new version has to verify behavior across 5 configs.

T-050 (the ruff baseline) explicitly inventoried the per-file ignores across 5 configs — that inventory cost time that wouldn't exist under a root-config model.

### Performance implication

Negligible direct perf impact. Indirect: drift discovery time, refactor cost when one rule changes.

### Improvement direction (for Track 1c)

Extract shared tool configs to root. Each package's `pyproject.toml` becomes a thin layer over root defaults. Track 1c.

## 7. Frontend isolation

### Current implementation

`apps/web/` is the ONLY TypeScript/JavaScript code in the entire repository. The other 8 directories (apps/api + apps/worker + 9 packages) are Python. Per T-009:
- `apps/web/package.json` — single Node.js manifest.
- `apps/web/` contains: Next.js app (`/app`), components, library code, tests, all in TS.
- No shared types between Python + TypeScript — types cross the API boundary via JSON; the frontend re-declares them in `apiClient.ts` (T-009 §2).

The two languages don't share code; they share contracts via the JSON Schema implicit in FastAPI responses.

### State-of-the-art alternative

- **Same**: clean language boundary. Modern web monorepos with both languages overwhelmingly use this pattern.
- **OpenAPI-driven type generation** (orval, openapi-typescript): auto-generate TS types from FastAPI's OpenAPI schema. Removes the manual re-declaration in `apiClient.ts`.

### Verdict — State-of-the-art

The split is correct and the only one that scales. Mixing Python and TypeScript in the same package (e.g., via WASM bridges or RPC stubs) is an anti-pattern for this kind of app. The clean boundary at the API contract is the right call.

T-009's apiClient.ts re-declares types manually — that's the one improvement direction. But the language separation itself is sound.

### Performance implication

Optimal. Each stack builds independently. Type-checking is parallel. Dependency graphs are disjoint.

### Improvement direction (for Track 1c)

Adopt OpenAPI type generation to eliminate the manual re-declarations. Optional; the manual approach also works.

## 8. Docker/infra layout

### Current implementation

`infra/` directory at root with `infra/docker/` subdirectory. Per T-009 §3:
- `infra/docker/api/Dockerfile` — API service.
- `infra/docker/worker/Dockerfile` — worker service.
- `infra/docker/web/Dockerfile` — frontend.
- `infra/docker/postgres/` — local Postgres for dev (init scripts).
- Root `docker-compose.yml` orchestrates the stack.

Apps live in `apps/`; their Dockerfiles live in `infra/docker/`. The Dockerfiles reference the app sources via build context. T-009 §3 noted the split: the build context is the repo root, so the Dockerfile can `COPY apps/api/src/...`.

### State-of-the-art alternative

- **Dockerfile-next-to-app**: `apps/api/Dockerfile`, `apps/worker/Dockerfile`, `apps/web/Dockerfile`. Build context narrowed to the app dir. Faster builds.
- **Layered/cached buildx**: `docker buildx` with multi-stage caching, especially across the install step.
- **Nix-based reproducible builds**: `nix build .#api` etc. — extreme reproducibility, steeper learning curve.

### Verdict — Acceptable

The `infra/docker/` directory model is fine. It centralises Dockerfiles, which makes "where do I deploy from?" answerable in one glob. The cost is wider build contexts (root-relative) which means Docker has to scan more files even if the app's code didn't change.

The `apps/X/Dockerfile` model is more modern but the current pattern works.

### Performance implication

Wider build contexts mean Docker's `COPY . .` (or selective COPY) walks more files than strictly necessary. With `.dockerignore` excluding `node_modules`, `.venv`, `tests/`, this is manageable.

### Improvement direction (for Track 1c)

Move Dockerfiles next to their apps OR add explicit `.dockerignore` to limit build context. Either works; the latter is lower-cost.

## 9. Observations across the 8 questions

### 9.1 Pattern: tooling lags structure

The macro structure (apps + packages, language boundary at API) is sound and modern. The tooling (Makefile, no workspace manager, per-package config duplication) is 2018-era. The mismatch suggests the structure was designed first; the tooling layer has not been modernised since the initial scaffold.

### 9.2 Pattern: stubs as architectural intent

The 6 README-only stubs (T-010) signal intent that hasn't been honored. The system's AI logic, tax logic, audit logic etc. all live elsewhere. This is the largest single architectural drift in the repo structure.

### 9.3 Pattern: CI as a parallelism workaround

The 7-job CI matrix achieves parallelism that the local Makefile lacks. The CI is more sophisticated than the local dev environment — usually a smell. Investing in `just` or `nx` would lift the local experience to the CI's level.

### 9.4 What's clearly good

- Language boundary (frontend / backend) is the modern best practice.
- The `apps/` vs `packages/` split is widely understood and defensible.
- Per-package CI isolation prevents cross-package test failures from masquerading as global failures.

### 9.5 What's clearly outdated

- Makefile orchestration (no parallelism, missing targets).
- Per-package tool config duplication (drift hazard).
- No workspace manager (slow installs, no central lockfile).

### 9.6 What's risky

- 6 stub packages signal intent that does not match implementation reality. Cognitive load on new contributors. T-010 originating finding.

## 10. Summary table

| # | Question | Verdict | Track-1c priority |
|---|----------|---------|--------------------|
| 1 | Apps + packages layout | Acceptable | Low |
| 2 | No workspace manager | Outdated | **High** (perf + DX) |
| 3 | 6 stub packages | **Risky** | **High** (cognitive + arch) |
| 4 | Makefile orchestration | Outdated | Medium |
| 5 | Per-app CI jobs | Acceptable | Low |
| 6 | Per-package tool config | Outdated | Medium (drift) |
| 7 | Frontend isolation | State-of-the-art | None |
| 8 | Docker/infra layout | Acceptable | Low |

**Recommendations are deferred to Track 1c.** The verdicts here are the input.

## 11. References

- `pyproject.toml` (root tooling-only config)
- `Makefile` (18 LOC; per-app orchestration)
- `.github/workflows/ci.yml` (7+ per-app jobs)
- `infra/docker/` (per-app Dockerfiles)
- `apps/api/pyproject.toml`, `apps/worker/pyproject.toml`, `apps/web/package.json`
- `packages/domain/pyproject.toml`, `packages/portfolio/pyproject.toml`, `packages/storage/pyproject.toml`
- `packages/{ai,analytics,audit,data_providers,risk,tax}/README.md` — 6 stubs
- T-001 `domain-primitives-and-money.md` (`packages/domain` reality)
- T-002 `portfolio-money-and-accounting.md` (`packages/portfolio` reality)
- T-003 `storage-package-and-migrations.md` (`packages/storage` reality)
- T-006 `api-infrastructure-and-ai.md`
- T-007 `worker-orchestration-and-scheduling.md`
- T-008 `web-pages.md`, `web-components-status-and-shared.md`, `web-components-feature-grids.md`
- T-009 `web-api-client-and-text.md`, `infra-docker-and-compose.md`, `build-ci-and-scripts.md`
- T-010 `stub-packages.md` (the 6-stub originating finding)
- T-022 `belgian-tax-computation.md` (tax logic in `packages/portfolio`, NOT `packages/tax`)
- T-023 `ai-explanation-and-budget.md` (AI logic in `apps/api`, NOT `packages/ai`)
- T-050 ruff baseline (per-file-ignore inventory across 5 configs)
- T-058 npm audit baseline (web build cost)
