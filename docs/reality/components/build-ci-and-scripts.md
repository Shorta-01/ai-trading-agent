# Reality — build, CI, scripts

**Scope.** The repo-wide tooling glue: `AGENTS.md` rules, `Makefile`, repo-root `pyproject.toml`, the two GitHub Actions workflows (`ci.yml` + `code-health.yml`), and the two operator scripts (`check_product_tracking.py`, `project_status.py`). Sibling docs cover the infra layer (`infra-docker-and-compose.md`) and the web client (`web-api-client-and-text.md`).

## In-scope files

| File | Lines | Role |
|---|---:|---|
| `AGENTS.md` | 34 | Repo-wide locked rules (Dutch UI, no secrets, audit-trail, etc.) |
| `Makefile` | 17 | Developer-side targets: `test`, `lint`, `typecheck`, `web-build` |
| `pyproject.toml` (repo root) | 35 | Cross-cutting tooling config for `vulture` + `bandit` |
| `.github/workflows/ci.yml` | 277 | Six parallel build/test jobs (5 Python + 1 web) |
| `.github/workflows/code-health.yml` | 199 | Report-only audit sweep — ruff/mypy/vulture/bandit/pip-audit/radon + eslint/tsc/knip/ts-prune/npm-audit |
| `scripts/check_product_tracking.py` | 184 | Enforces tracking-docs invariants (developer-only gate) |
| `scripts/project_status.py` | 82 | Local status board; runs the tracker as a subprocess |

## 1. `AGENTS.md` — repo-wide locked rules

Top of file (`AGENTS.md:3`) points to the locked doctrine `docs/intent/_trading-system-doctrine.md` (adoption record `docs/decisions/0002-trading-system-doctrine.md`). Conflict rule (`:4`): "Where this file conflicts with the doctrine, the doctrine wins."

### Product safety boundaries (`AGENTS.md:6`)

- `:7` — "AI Trading Agent is a full trading system that submits user-approved orders to IBKR (paper or real-money account, treated identically). See doctrine §1–§3."
- `:8` — "The system never submits an order without explicit user approval. The two-grid / two-approval lifecycle … is mandatory."
- `:9` — "IBKR is the single source of truth for positions, cash, orders, and fills (doctrine §2). The system never holds an authoritative state that contradicts IBKR."

### Architecture and implementation rules (`AGENTS.md:11-16`)

- "No business logic in UI." (`:12`)
- "No hardcoded secrets." (`:13`)
- "No hardcoded tickers in core logic." (`:14`)
- "No Raspberry Pi-specific application logic." (`:15`)
- "Do not add external API calls without documented adapter and test strategy." (`:16`)

### Data, audit, and reliability rules (`AGENTS.md:18-25`)

- "No silent data correction." (`:19`)
- "Every decision must be logged." (`:20`)
- "No advice without audit trail." (`:21`)
- "All data must be backed up and restorable." (`:22`)
- "A backup is not trusted until restore is tested." (`:23`)
- "Jobs must be idempotent." (`:24`)
- "Scheduled job failures must be visible." (`:25`)

### AI and calculation rules (`AGENTS.md:27-30`)

- "Every financial calculation must have tests." (`:28`)
- "Every AI output must be schema-validated." (`:29`)
- "AI may not override risk rules." (`:30`)

### UI language and clarity rules (`AGENTS.md:32-34`)

- "Keep UI Dutch and simple." (`:33`)
- "Every UI field must have simple Dutch help text." (`:34`)

All seven sentinel guardrails are present verbatim in `AGENTS.md`. This doc is the canonical reference for the cross-cluster reality finding "Dutch-UI invariant verified" (T-008 `web-pages.md` §7), "AI may not override risk rules" (T-006 §11 Anthropic Claude provider, T-008 confirmation gates), and "Every decision must be logged" (operationalised by `scripts/check_product_tracking.py` — §6 below).

## 2. `Makefile` (17 lines)

- Phony declaration: `.PHONY: test lint typecheck web-build` (`Makefile:1`). No default goal → bare `make` runs `test` (first target).
- No `SHELL :=` (GNU make default `/bin/sh`).
- No target-to-target dependencies.

### Targets

- **`test`** (`Makefile:3-5`): `cd apps/api && pytest`, then `cd apps/worker && pytest`. **No coverage flag, no `-q`. Packages (`domain`/`portfolio`/`storage`) are not tested by `make test`.**
- **`lint`** (`Makefile:7-10`): `cd apps/api && ruff check .`, `cd apps/worker && ruff check .`, `cd apps/web && npm run lint`. **Packages are not linted by `make lint`.**
- **`typecheck`** (`Makefile:12-14`): `cd apps/api && mypy src`, `cd apps/worker && mypy src`. **Packages are not type-checked by `make typecheck`.**
- **`web-build`** (`Makefile:16-17`): `cd apps/web && npm run build`.

### Coverage gaps

The Makefile covers only `apps/api`, `apps/worker`, and `apps/web`. Three packages are **silent in the local developer loop** — `packages/domain`, `packages/portfolio`, `packages/storage`. A developer who runs `make lint && make typecheck && make test` and pushes can see CI surprises if any package code regresses. CI does cover them — see §4.

Other notable absences from the Makefile: no target for `check_product_tracking.py`, no target for `project_status.py`, no code-health (vulture/bandit/pip-audit/radon) target, no e2e/Playwright target, no install target.

## 3. Repo-root `pyproject.toml` (35 lines)

Header comment locks the file's purpose (`pyproject.toml:1-12`):

- "Repo-root tooling config for Phase 1d code-health audit." (`:1`).
- "This file intentionally does NOT declare a Python package — each app and package keeps its own `pyproject.toml` and its own tool config." (`:3-4`).
- "Per-package ruff and mypy settings are unchanged and continue to live in their respective package pyproject files; this file does not override them." (`:10-12`).

### Tool sections

- `[tool.vulture]` (`pyproject.toml:14`):
  - `min_confidence = 80` (`:15`).
  - `paths = ["apps/api/src", "apps/worker/src", "packages/domain/src", "packages/portfolio/src", "packages/storage/src"]` (`:16-22`).
  - `exclude = ["*/tests/*", "*/migrations/*"]` (`:23-26`).
- `[tool.bandit]` (`pyproject.toml:28`):
  - `exclude_dirs = ["tests", ".venv", "node_modules"]` (`:29`).
  - Inline comment: bandit is report-only in Phase 0; project-wide skips deferred (`:30-31`).
- `pyproject.toml:33-35` — comment-only: "radon has no `[tool.radon]` section in pyproject; it reads CLI flags."

### Cross-reference with T-050…T-053 baselines

- **T-050 ruff**: NOT configured at repo root (per-package config per `:10-12`).
- **T-051 mypy**: NOT configured at repo root (per-package config per `:10-12`).
- **T-052 vulture**: configured here (`:14-26`).
- **T-053 bandit**: configured here (`:28-31`).
- **T-054 pip-audit**: no config block; called bare in CI (`code-health.yml:118`).
- **T-055 radon**: no config block; CLI flags only.

## 4. `.github/workflows/ci.yml` (277 lines)

### Workflow-level

- `name: CI` (`ci.yml:1`).
- Triggers (`:3-6`): `pull_request:` (all events, no branch filter), `push: branches: [main]`.
- `permissions: contents: read` (`:8-9`).
- **No `concurrency:` / `cancel-in-progress:` block** — concurrent runs are not cancelled.
- No matrix declarations; each stack hard-coded to a single version.

### Repeated 4-attempt checkout-with-retry pattern (every job)

Each job inlines the same ~28-line block: 4 attempts of `actions/checkout@v4` with sleeps of 10 s / 30 s / 60 s between tries; attempts 1-3 use `continue-on-error: true` with `if:` chains; attempt 4 has no `continue-on-error` (final failure fails the job). Per-job line ranges: `domain` `:19-47`, `portfolio` `:58-86`, `storage` `:102-130`, `api` `:145-173`, `worker` `:195-223`, `web` `:239-267`.

### Job dependencies

**No `needs:` declarations anywhere.** All six jobs run independently in parallel. No fan-in, no aggregator, no required-status job inside the workflow.

### Six parallel jobs

#### `domain` (`ci.yml:13-54`)

- `runs-on: ubuntu-latest`, `defaults.run.working-directory: packages/domain` (`:14-17`).
- Steps after checkout: `actions/setup-python@v5` Python 3.12 (`:48-50`), `pip install -e .[dev]` (`:51`), `ruff check .` (`:52`), `mypy src` (`:53`), `pytest -q` (`:54`).

#### `portfolio` (`ci.yml:55-94`)

- **No `defaults.run.working-directory`** — the one outlier. Each step uses an explicit `cd packages/portfolio && …`.
- After checkout: setup-python 3.12 (`:87-89`); `cd packages/domain && pip install -e .` (`:90`) — domain installed as sibling dep first; then `cd packages/portfolio && pip install -e .[dev]` (`:91`); ruff (`:92`); mypy (`:93`); `pytest -q` (`:94`).

#### `storage` (`ci.yml:96-137`)

- `defaults.run.working-directory: packages/storage` (`:98-100`).
- Steps: setup-python 3.12 (`:131-133`); `pip install -e .[dev]` (`:134`); ruff (`:135`); mypy (`:136`); `pytest -q` (`:137`).
- Standalone — no sibling pre-install.

#### `api` (`ci.yml:139-187`)

- `defaults.run.working-directory: apps/api` (`:141-143`).
- Steps: setup-python 3.12 (`:174-176`); sibling installs in dep order — `packages/domain` (`:177`), `packages/storage` (`:178`), `packages/portfolio` (`:179`); **then `apps/worker` (`:183`)**, annotated with inline comment at `:180-182` referencing **Task 133**: "the api consumes the worker's pure-function Action Draft composer (no network/IO). Pre-install editable so pip sees the local package and skips a PyPI lookup that would 404." Then `pip install -e .[dev]` (`:184`), ruff (`:185`), mypy (`:186`), `pytest` (`:187` — no `-q` here).

#### `worker` (`ci.yml:189-231`)

- `defaults.run.working-directory: apps/worker` (`:191-193`).
- Steps: setup-python 3.12 (`:224-226`); sibling install `packages/storage` (`:227`); `pip install -e .[dev]` (`:228`); ruff (`:229`); mypy (`:230`); `pytest` (`:231`).

#### `web` (`ci.yml:233-277`)

- `defaults.run.working-directory: apps/web` (`:235-237`).
- Steps: `actions/setup-node@v4` Node 22 (`:268-270`); `npm install --legacy-peer-deps` (`:271`); `npm run lint` (`:272`); `npm run build` (`:273`); `npm test` (`:274`); inline comment at `:275` cites **Task 126b** ("Playwright smoke. Install chromium only to keep CI fast."); `npx playwright install --with-deps chromium` (`:276`); `npm run test:e2e` (`:277`).

### Pinned versions + cache strategy

- `actions/checkout@v4`, `actions/setup-python@v5` (Python 3.12), `actions/setup-node@v4` (Node 22).
- **No caching anywhere** — no `actions/cache@`, no `cache:` parameter on `setup-python` or `setup-node`. Cold installs on every PR.

### Conditional execution

Only `if:` conditions are the checkout-retry guards. No path filters, no event-type gating, no concurrency cancellation.

## 5. `.github/workflows/code-health.yml` (199 lines)

### Workflow-level

- `name: code-health` (`code-health.yml:1`).
- Header comment (`:3-8`): "run code-health tools in report-only mode on every PR and on pushes to main. Findings do not fail the build until Phase 1d baselines them and we tighten gates." Explicitly **additive** to `ci.yml`.
- Triggers identical to `ci.yml`: `pull_request:` + `push: branches: [main]` (`:10-13`).
- `permissions: contents: read` (`:15-16`).
- **No `concurrency:`, no `needs:` between the two jobs** — they run in parallel.

### Job: `python-health` (`code-health.yml:20-129`)

- `name: python health (report-only)` (`:21`).
- `runs-on: ubuntu-latest` (`:22`).
- **`continue-on-error: true`** (`:23-24`) — any finding is a soft failure.
- No `defaults.run.working-directory` — runs from repo root.
- Steps after the checkout-retry pattern (`:26-54`):
  - `actions/setup-python@v5` Python 3.12 (`:56-58`).
  - Tool install (`:60-69`): `pip install --upgrade pip` then `ruff>=0.6.0`, `mypy>=1.11.0`, `vulture`, `bandit`, `pip-audit`, `radon`.
  - Editable project installs (`:71-77`): `packages/domain`, `packages/storage`, `packages/portfolio`, `apps/worker`, `apps/api` — in that order (mirrors the `ci.yml api` job dependency order).
  - **ruff** (`:79-86`) — `if: always()`; loops over all 5 source roots; each call suffixed `|| true`. Each invocation grouped with `::group::ruff $pkg` / `::endgroup::` for log folding. **T-050 baseline sweep**.
  - **mypy --strict** (`:88-95`) — `if: always()`; same loop; **harsher than per-package `ci.yml`** mypy (which uses per-package config, not `--strict`). **T-051 baseline sweep**.
  - **vulture** (`:97-105`) — `if: always()`; single call across all five `src` dirs; `--min-confidence 80` (mirrors `pyproject.toml:15`). **T-052 baseline**.
  - **bandit** (`:107-112`) — `if: always()`; `bandit -r apps packages -x tests -ll`. **T-053 baseline**.
  - **pip-audit** (`:114-119`) — `if: always()`; bare. **T-054**.
  - **radon** (`:121-129`) — `if: always()`; `radon cc -s -a apps packages` + `radon mi -s apps packages`. **T-055**.

### Job: `web-health` (`code-health.yml:131-199`)

- `name: web health (report-only)` (`:132`).
- `runs-on: ubuntu-latest` (`:133`), `continue-on-error: true` (`:134`).
- `defaults.run.working-directory: apps/web` (`:135-137`).
- Steps after checkout-retry (`:139-167`):
  - `actions/setup-node@v4` Node 22 (`:169-171`).
  - `npm install --legacy-peer-deps` (`:173-174`).
  - Ephemeral install (`:176-179`) — comment: "Installed as ephemeral dev tools — not added to package.json so we do not perturb the existing dependency lock during Phase 0." `npm install --no-save --legacy-peer-deps knip ts-prune`.
  - **eslint** (`:181-183`) — `if: always()`; `npm run lint -- --max-warnings=9999 || true`. Warning ceiling raised so the existing script never blocks.
  - **tsc --noEmit** (`:185-187`) — `if: always()`; `npx tsc --noEmit || true`. **T-056 baseline**.
  - **knip** (`:189-191`) — `if: always()`; `npx knip || true`. **T-057 baseline**.
  - **ts-prune** (`:193-195`) — `if: always()`; `npx ts-prune || true`. **T-057 sibling**.
  - **npm audit** (`:197-199`) — `if: always()`; `npm audit --omit=dev || true`.

### Tool inventory coverage map

| Tool | code-health.yml line | Baseline task |
|---|---|---|
| ruff | `:79-86` | T-050 |
| mypy --strict | `:88-95` | T-051 |
| vulture | `:97-105` | T-052 |
| bandit | `:107-112` | T-053 |
| pip-audit | `:114-119` | T-054 |
| radon | `:121-129` | T-055 |
| eslint (raised warnings) | `:181-183` | — |
| tsc --noEmit | `:185-187` | T-056 |
| knip | `:189-191` | T-057 |
| ts-prune | `:193-195` | T-057 |
| npm audit | `:197-199` | — |

**Observation**: every tool is wrapped in `|| true` and `if: always()`, and both jobs declare `continue-on-error: true`. **The entire workflow is observational — it cannot block a PR.**

## 6. `scripts/check_product_tracking.py` (184 lines)

### Invariant enforced (one-line summary)

The script enforces that the five product-tracking docs exist, that `next-task.md` has a `# Task <N>` title, that `current-state.md` carries a `Huidige toestand: **na Task <N>…**` marker which is **not older than** the first completed task it lists, and that the latest completed Task token is mentioned in `task-history.md`, `version-1-backlog.md`, and `version-1-scope-register.md`.

### Constants

- `REPO_ROOT = Path(__file__).resolve().parents[1]` (`:8`).
- `REQUIRED_FILES` (`:9-15`): `docs/product/next-task.md`, `…/current-state.md`, `…/task-history.md`, `…/version-1-backlog.md`, `…/version-1-scope-register.md`.
- `MARKER_RE` (`:20-22`): `r"Huidige toestand:\s*\*\*na\s+Task\s+(\d+)([A-Z]?)(?:-(R)(\d*))?\*\*"`.
- `COMPLETED_TASK_RE` (`:23-26`): `r"Task\s+(\d+)([A-Z]?)(?:-(R)(\d*))?\s*:\s*\*\*completed\*\*"` (case-insensitive).

### Task ID model

`@dataclass(frozen=True, order=True) class TaskId` (`:29-35`) with fields `number`, `suffix_rank` (0 or 1), `suffix_letter`, `repair_rank`. Comparability is the point — used at `:109` for stale-marker comparison. `parse_task_id(...)` (`:37-46`) maps regex groups to a `TaskId`; `format_task(...)` (`:49-56`) renders e.g. `132A-R1`.

### Five rules

1. **Required files exist** (`:59-63`, called `:156-157`). Failure: `"MISSING: <path>"`.
2. **`next-task` has a title** (`:66-74`). Regex `r"^#\s+Task\s+\d+[A-Z]?(?:-R)?"`. Failure: `"MISSING: next-task task title line starting with '# Task <number|suffix>'"`.
3. **`current-state` contains the Dutch marker** (`:77-82`). Substring check for `"Huidige toestand:"`.
4. **Marker not stale** (`:93-122`). Strict `MARKER_RE` match required (`:95-101`); marker `TaskId` compared against the first `COMPLETED_TASK_RE` hit (`:109-115`). Failure: `"STALE: current-state marker Task <X> is older than first completed Task <Y>"`.
5. **Latest completed task tracked in three downstream docs** (`:125-150`). Builds `f"Task {format_task(first_task)}"` and substring-checks `task-history.md`, `version-1-backlog.md`, `version-1-scope-register.md`.

### Entry point + exit code

`main()` (`:153-180`): runs `check_file_exists` first; only runs rules 2–5 if all required files exist (`:159`); partitions results into `failed`/`passed`; prints summary; returns `1` on any failure or `0` on full pass. CLI guard at `:183-184`: `sys.exit(main())`.

## 7. `scripts/project_status.py` (82 lines)

A developer-side status board.

### Output (`main()` at `:63-78`)

Print order:

1. `"Local project workflow status"` (`:64`).
2. `"=" * 30` underline (`:65`).
3. `f"Current next task: {read_next_task_title()}"` (`:66`).
4. `f"Product tracking checker: {product_tracking_check_status()}"` (`:67`).
5. blank line + `"Product tracking files:"` (`:68`).
6. For each of the 5 `TRACKING_FILES`: `"- {OK|MISSING}: {relative_path}"` (`:69-72`).
7. blank line + `f"Git: {git_info()}"` (`:74`).
8. Final reminder (`:75-78`): `"Reminder: GitHub CI status moet extern in GitHub worden geverifieerd; dit script kan CI niet valideren."`

### Helpers

- `read_next_task_title()` (`:17-24`) — first `"# "` line in `docs/product/next-task.md`.
- `git_info()` (`:27-41`) — shells out `git rev-parse --abbrev-ref HEAD` + `--short HEAD`; falls back to `"WARNING: git info niet beschikbaar in deze omgeving"` on `OSError`/`SubprocessError`.
- `product_tracking_check_status()` (`:44-60`) — subprocess-runs `sys.executable scripts/check_product_tracking.py` with `check=False, capture_output=True`; returns `"PASS"` if `returncode == 0` else `"FAIL"`.

### Entry point

Bare `if __name__ == "__main__": main()` (`:81-82`). **No `sys.exit()`** — always returns 0. Informational, not a gate.

### Where it is called from

- **Not called from the `Makefile`** — no target references it.
- **Not called from either CI workflow.**
- Developer-only invocation: `python scripts/project_status.py`.

## 8. Cross-cuts

### Makefile vs CI vs code-health mirroring

| Action | `Makefile` | `ci.yml` | `code-health.yml` |
|---|---|---|---|
| ruff (apps/api) | `:8` | `:185` | `:79-86` (loop) |
| ruff (apps/worker) | `:9` | `:229` | `:79-86` (loop) |
| ruff (packages/*) | — | `:52, :92, :135` | `:79-86` (loop) |
| mypy (apps/api) | `:13` | `:186` | `:88-95` (loop, `--strict`) |
| mypy (apps/worker) | `:14` | `:230` | `:88-95` (loop, `--strict`) |
| mypy (packages/*) | — | `:53, :93, :136` | `:88-95` (loop, `--strict`) |
| pytest (apps/api) | `:4` | `:187` | — |
| pytest (apps/worker) | `:5` | `:231` | — |
| pytest (packages/*) | — | `:54, :94, :137` | — |
| web lint | `:10` | `:272` | `:181-183` (warnings raised) |
| web build | `:17` | `:273` | — |
| web unit tests | — | `:274` | — |
| web e2e (Playwright chromium) | — | `:276-277` | — |
| vulture / bandit / pip-audit / radon | — | — | `:97-129` |
| tsc --noEmit / knip / ts-prune / npm audit | — | — | `:185-199` |
| product-tracking checker | — | — | — |

**Makefile gaps**: no `pytest` for `packages/*`, no web tests beyond `lint`+`build`, no e2e, no security/dead-code/complexity tools, no product-tracking checker, no `project_status` target.

**`ci.yml` gaps relative to `code-health.yml`**: `ci.yml` does NOT run vulture, bandit, pip-audit, radon, knip, ts-prune, or tsc-noEmit. Those live only in the report-only `code-health.yml` workflow.

### Neither CI workflow invokes `scripts/*.py`

Both `ci.yml` and `code-health.yml` grep clean for `check_product_tracking.py` or `project_status.py`. The **"Every decision must be logged" guardrail at `AGENTS.md:20` is enforced socially / by convention, not by CI**. A developer who never runs `python scripts/check_product_tracking.py` (or its wrapper `python scripts/project_status.py`) locally can push tracking-doc drift without any pipeline detection.

### `check_product_tracking.py` enforcement scope

The script enforces structural propagation of completed-task tokens across `docs/product/*.md` files. It does **not** check:

- That `docs/tasks/T-NNN-*.md` files exist (the task-working-file pattern this Phase 1 workflow uses).
- That `docs/decisions/0NNN-*.md` ADRs exist for any decision.
- That `AGENTS.md` itself is consistent with `docs/intent/_trading-system-doctrine.md`.

A Phase 4 brainstorm could extend the checker (or wire it into CI), but the current product-tracking-checker is narrower than the AGENTS.md guardrail it operationalises.

### Inline task references in `ci.yml`

Two inline comments cite specific tasks:

- `ci.yml:180-182` — **Task 133** — explains why `apps/worker` must be editable-installed before `apps/api`: "the api consumes the worker's pure-function Action Draft composer (no network/IO)".
- `ci.yml:275` — **Task 126b** — "Playwright smoke. Install chromium only to keep CI fast."

These are the only inline task references in the workflow YAML and document non-obvious install ordering / e2e scope decisions.

## 9. Cross-cutting observations

- **Two parallel CI workflows trigger identically** on every PR + main push (`ci.yml:3-6`, `code-health.yml:10-13`). `ci.yml` is the gating workflow; `code-health.yml` is fully report-only via `continue-on-error: true` + `|| true` on every tool. A merge can land with red code-health.
- **No caching anywhere** — both workflows install from scratch on every PR. Pip + npm cold installs significantly inflate CI runtime; a Phase 4 perf brainstorm could add `actions/cache@v4` keyed on `pyproject.toml` + `package-lock.json` hashes.
- **The 4-attempt checkout-retry block is copy-pasted six times** in `ci.yml` (and twice in `code-health.yml`) — ~28 lines each, ~170 lines duplicated. A reusable workflow or composite action would compress the file substantially. Phase 4 candidate.
- **No `needs:` graph in `ci.yml`** — all six jobs run independently. Branch-protection rules presumably enforce required-status aggregation externally (out of scope for this doc per the task spec, lives in `docs/tasks/_branch-protection-checklist.md`).
- **Repo-root `pyproject.toml` is intentionally minimal** — only vulture + bandit configured. The choice to keep ruff/mypy per-package (per the `:10-12` comment) keeps per-package teams autonomous but increases the surface area an `ESLint`-style global config would simplify.
- **`make test` is silent on `packages/*`** — a developer can pass the Makefile loop and break package tests in CI. The Makefile is a convenience layer, not a CI parity tool.
- **The `project_status.py` reminder line at `:75-78`** explicitly says it cannot validate GitHub CI — operators must check externally. That correctly reflects the reality that the script has no GitHub API client.
- **AGENTS.md doctrine vs reality**: of the 7 sentinel guardrails, the script + workflow surface enforces **none** automatically. "Every decision must be logged" (`AGENTS.md:20`) has a checker (`scripts/check_product_tracking.py`) that is *not wired into CI*; "AI may not override risk rules" (`:30`) is enforced inside the application code (T-006 §11 Anthropic provider, T-007 `worker-actions-and-reconciliation.md` §4 safety re-check); "No hardcoded secrets" (`:13`) is honoured by the `.env.example` doctrine (cross-ref `infra-docker-and-compose.md` §4). The remaining four are not directly validated by any tool in this layer.
