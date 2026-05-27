# Bugs — populated in Phase 1d

## FIND-PIPAUDIT-001 — `fastapi==0.136.3` is a malicious release injecting an undocumented `fastar` dependency (MAL-2026-4750)

- **Tool:** `pip-audit 2.10.0`, raw output `/tmp/pip-audit-baseline.json` (T-054).
- **Package:** `fastapi`
- **Installed version:** `0.136.3`
- **Fixed version:** none listed by the advisory (the malicious release does not have a "fixed-in" pointer — the remediation is to pin away from `0.136.3`).
- **Advisory ID:** `MAL-2026-4750` (no CVE alias yet).
- **Project pin:** `apps/api/pyproject.toml:7` declares `"fastapi>=0.115.0"` with no upper bound. The unbounded `>=` resolved to the malicious `0.136.3` at install time.
- **Evidence (advisory body, abridged):**

  > "This release of fastapi 0.136.3 modifies pyproject.toml and PKG-INFO to add an undocumented dependency 'fastar>=0.9.0' to the [project.optional-dependencies] standard group … The README documents every other dependency in the [standard] group (httpx, jinja2, python-multipart, uvicorn, fastapi-cli, email-validator, pydantic-settings, pydantic-extra-types) but does not mention 'fastar'. Because the documented recommended install command is `pip install \"fastapi[standard]\"`, every user following the official documentation silently pulls the unrelated 'fastar' package onto their developer or CI machine. The name 'fastar' is a typosquat-shaped substitution against 'fastapi'/'fastapi-*' namespaces … Whoever controls 'fastar' on PyPI gains code execution at install time on a very large user base."

- **Why it matters (plain English):** the project pins `fastapi>=0.115.0` and resolved to the tainted `0.136.3`. The malicious payload only triggers when someone runs `pip install fastapi[standard]` (which pulls the typosquat `fastar` package as a "standard" extra). The project does **not** currently install with `[standard]` — `grep -rn "fastapi\[standard\]\|fastar"` across infra/docker, apps, packages, and `.github/workflows/` returned zero matches, and `pip show fastar` confirms it is not installed in the current venv. So the blast radius today is **theoretical**: any developer or CI run that hand-types `pip install fastapi[standard]` would silently pull the typosquat. The bare `fastapi` install path used by this project does not trigger the payload.

  However: the project is still running a release that the PyPA advisory database flags as malicious. The maintainer's PyPI account is implicitly compromised or hostile; future minor releases under the same line are not safe to trust by default.

- **Fix approach:**

  1. **Pin away from `0.136.3`** in `apps/api/pyproject.toml`: change `"fastapi>=0.115.0"` to a bounded range (e.g. `"fastapi>=0.115.0,<0.136"` or pin a specific known-clean version like `"fastapi==0.115.6"`).
  2. **Re-resolve** the venv (`pip install --upgrade fastapi`) to drop `0.136.3`.
  3. **Add a CI guard**: ensure `pip-audit` runs against the lockfile / resolved env at merge time so future malicious releases are caught before they land. (Out of scope for the fix itself — this is a separate Phase 4 task.)

- **Complexity:** small (one-line pyproject change + venv refresh).
- **Severity:** **high**. (Per the task spec, CVSS-missing defaults to medium; this finding is bumped to high because (a) the advisory is a confirmed malicious release rather than a regular CVE, (b) the project is actively running it, and (c) AGENTS.md's "No external API calls without documented adapter and test strategy" doesn't directly cover supply-chain but the spirit of the project's safety posture argues for prompt remediation.)
- **Related findings:** none — this is the only supply-chain advisory in the baseline. The four pip CVEs in the dismissed list are build-time-tool-only.

## FIND-NPMAUDIT-001 — `next@15.2.6` is exposed to 22 distinct GHSA advisories (high-severity umbrella, production dependency)

- **Tool:** `npm audit 10.x`, raw outputs `/tmp/npm-audit-prod.json` + `/tmp/npm-audit-prod.txt` + `/tmp/npm-audit-full.json` + `/tmp/npm-audit-full.txt` (T-058).
- **Package:** `next`.
- **Installed version:** `15.2.6` (pinned at `apps/web/package.json:7`).
- **Vulnerable range:** `9.3.4-canary.0 - 16.3.0-canary.5` (npm audit aggregates all 22 advisories into one package row).
- **Fixed version:** `15.5.18` (per `npm audit fix --force` proposal at `/tmp/npm-audit-prod.txt:29, 36`).
- **Prod / dev flag:** **prod** (`next` is a runtime dependency, declared in the `dependencies` block at `apps/web/package.json:7`, NOT `devDependencies`).
- **Project pin:** `apps/web/package.json:7` declares `"next": "15.2.6"` (exact pin).

### Inventory (22 GHSAs, all rolled up under `next` by npm audit)

| GHSA | Severity | CWE | Class |
|---|---|---|---|
| `GHSA-g5qg-72qw-gw5v` | moderate | CWE-524 | Cache Key Confusion for Image Optimization API Routes |
| `GHSA-xv57-4mr9-wg8v` | moderate | CWE-20 | Content Injection Vulnerability for Image Optimization |
| `GHSA-4342-x723-ch2f` | moderate | CWE-918 | Improper Middleware Redirect → SSRF |
| `GHSA-w37m-7fhw-fmv9` | moderate | CWE-497, -502, -1395 | Server Actions Source Code Exposure |
| `GHSA-mwv6-3258-q52c` | **high** | CWE-400, -502, -1395 | DoS with Server Components |
| `GHSA-9g9p-9gw9-jx7f` | moderate | CWE-400, -770 | self-hosted DoS via Image Optimizer remotePatterns |
| `GHSA-h25m-26qc-wcjf` | **high** | CWE-400, -502 | HTTP request deserialization DoS (insecure RSC) |
| `GHSA-ggv3-7p47-pfv8` | moderate | CWE-444 | HTTP request smuggling in rewrites |
| `GHSA-3x4c-7xq6-9pq8` | moderate | CWE-400 | Unbounded `next/image` disk cache exhaustion |
| `GHSA-q4gf-8mx6-v5v3` | **high** | CWE-770 | DoS with Server Components |
| `GHSA-8h8q-6873-q5fj` | **high** | CWE-770 | DoS with Server Components (variant) |
| `GHSA-26hh-7cqf-hhc6` | **high** | CWE-288 | Middleware/Proxy bypass via segment-prefetch — incomplete fix follow-up |
| `GHSA-3g8h-86w9-wvmq` | low | CWE-349 | Middleware/Proxy redirects cache-poisoned |
| `GHSA-ffhc-5mcf-pf4q` | moderate | CWE-79 | XSS in App Router with CSP nonces |
| `GHSA-vfv6-92ff-j949` | low | CWE-328 | Cache poisoning via RSC cache-busting collisions |
| `GHSA-gx5p-jg67-6x7h` | moderate | CWE-79 | XSS in `beforeInteractive` scripts with untrusted input |
| `GHSA-mg66-mrh9-m8jx` | **high** | CWE-770 | DoS via connection exhaustion (Cache Components apps) |
| `GHSA-h64f-5h5j-jqjh` | moderate | CWE-770 | DoS in Image Optimization API |
| `GHSA-c4j6-fc7j-m34r` | **high** | CWE-918 | SSRF in apps using WebSocket upgrades |
| `GHSA-wfc6-r584-vfw7` | moderate | CWE-436 | Cache poisoning in RSC responses |
| `GHSA-267c-6grr-h53f` | **high** | CWE-288 | Middleware/Proxy bypass via segment-prefetch (App Router) |
| `GHSA-36qx-fr4f-26g5` | **high** | CWE-863 | Middleware/Proxy bypass in Pages Router (i18n) |

**Severity ranking by GHSA**: 9 high + 11 moderate + 2 low → npm audit's aggregated package severity is **high** (driven by the worst-of-set rule).

### Why it matters (plain English)

Several of the high-severity advisories require specific runtime conditions to be exploitable. The most relevant exposure surface for this project's frontend (per `docs/reality/components/web-pages.md` §1 — Next.js 15 App Router, `"use client"` for every data-touching page, no `output: "standalone"`, no `next/image` `remotePatterns` declared in `next.config.ts:3-6`):

- **`next/image` advisories (`GHSA-g5qg-72qw-gw5v`, `GHSA-xv57-4mr9-wg8v`, `GHSA-9g9p-9gw9-jx7f`, `GHSA-3x4c-7xq6-9pq8`, `GHSA-h64f-5h5j-jqjh`)** — likely **not exploitable today**: the project does not use `next/image` anywhere (verifiable by `grep -r "next/image" apps/web/` returning zero hits in the T-008 page survey) and `next.config.ts` declares no `images.remotePatterns`. Per `docs/reality/components/web-api-client-and-text.md` §5, the only Next.js config field set is `reactStrictMode: true`.
- **Middleware / Proxy bypass advisories (`GHSA-4342-x723-ch2f`, `GHSA-26hh-7cqf-hhc6`, `GHSA-267c-6grr-h53f`, `GHSA-3g8h-86w9-wvmq`, `GHSA-ggv3-7p47-pfv8`, `GHSA-36qx-fr4f-26g5`)** — likely **not exploitable today**: the project has no `middleware.ts` (verifiable by `find apps/web/app -name 'middleware.ts'` returning nothing) and uses App Router, not Pages Router (`apps/web/app/` directory structure per T-008 §3).
- **Server Components / Server Actions DoS advisories (`GHSA-mwv6-3258-q52c`, `GHSA-h25m-26qc-wcjf`, `GHSA-w37m-7fhw-fmv9`, `GHSA-mg66-mrh9-m8jx`, `GHSA-q4gf-8mx6-v5v3`, `GHSA-8h8q-6873-q5fj`)** — **mostly not exploitable today**: per T-008 `web-pages.md` §5, the project is "client-first, not server-first" — every API-touching page declares `"use client"`. No page uses `async` server-component data fetching, and there are no Server Actions defined (verifiable by `grep -r '"use server"' apps/web/` returning zero hits). The four pure-server placeholder pages (`/suggesties`, `/onderzoek`, `/historiek`) are static.
- **XSS advisories (`GHSA-ffhc-5mcf-pf4q`, `GHSA-gx5p-jg67-6x7h`)** — **not exploitable today**: no CSP nonces in the project (`grep -r 'CSP\|Content-Security' apps/web/`), no `beforeInteractive` `<Script>` tags.
- **WebSocket SSRF (`GHSA-c4j6-fc7j-m34r`)** — **not exploitable today**: no WebSocket upgrade routes.
- **Cache poisoning (`GHSA-vfv6-92ff-j949`, `GHSA-wfc6-r584-vfw7`)** — relevant for App Router apps; per `apiClient.ts` (T-009 `web-api-client-and-text.md` §1), all GETs use `cache: "no-store"`, so client-driven caches are not in play. Server-side RSC cache poisoning would require an attacker to control a URL that flows into RSC rendering — not currently exposed.

**Real-world risk today**: the project ships `next@15.2.6` in production, but the runtime configuration (no middleware, no `next/image`, no Server Actions, no WebSocket upgrades, no CSP nonces, no `beforeInteractive` scripts, client-first data fetching with no-store) means **none of the 22 advisories has a clear current exploitation path against this codebase**. The exposure is latent: any future feature that adds middleware, `next/image`, or Server Actions immediately activates the relevant subset.

### Fix approach

1. **Upgrade `next`** to `15.5.18` (the `fixAvailable.version` in `/tmp/npm-audit-prod.json`). The advisory list resolves wholesale on this version.
2. The bump from `15.2.6` to `15.5.18` is a **patch+minor** within the same major (`15.x`); per Next.js's stability policy this should not break the App Router contract. Smoke-test via the existing Playwright suite (`apps/web/playwright.config.ts:25` runs `next start` against a production build).
3. Re-resolve via `npm install --legacy-peer-deps` to refresh `package-lock.json`.
4. **Out of scope for T-058** — this task is the baseline only; the upgrade is Phase 4 territory (per task spec "No `package.json` / `package-lock.json` modification").
5. **CI guard candidate (Phase 4)**: `code-health.yml:197-199` already runs `npm audit --omit=dev || true` report-only on every PR. A future tightening could remove `|| true` for HIGH-severity prod advisories so a new HIGH is a hard block.

### Complexity / severity

- Complexity to fix: **small** — `npm install next@15.5.18 --legacy-peer-deps` + smoke test.
- Severity: **HIGH** (per task spec for prod CVEs: follows npm-audit's rating, which is `high` here).

### Related findings

- `FIND-NPMAUDIT-002` (`postcss` transitive via `next` → also resolves when `next` is bumped).
- `FIND-PIPAUDIT-001` is the Python parallel: a single advisory cluster on a runtime dependency with a clean upgrade path. The pattern across both: the project's "no upper bound on direct deps" approach (`apps/api/pyproject.toml:7` for fastapi, `apps/web/package.json:7` for next) lets the resolver pick versions that later land in the advisory database. Phase 4 brainstorm candidate: lockfile-only pinning policy with `pip-audit` + `npm audit` running against the lock at merge time.

## FIND-NPMAUDIT-002 — `postcss@8.4.31` XSS via unescaped `</style>` in CSS stringify output (moderate, transitive via `next`)

- **Tool:** `npm audit 10.x`, raw outputs same as FIND-NPMAUDIT-001 (T-058).
- **Package:** `postcss`.
- **Installed version:** `8.4.31` (transitive).
- **Vulnerable range:** `<8.5.10`.
- **Fixed version:** `8.5.10` (rolls in when `next` upgrades to `15.5.18` per `/tmp/npm-audit-prod.txt:36`).
- **Prod / dev flag:** **prod** (transitive via `next` → which is prod).
- **Advisory:** `GHSA-qx2v-qp2m-jg93` (CWE-79, XSS).
- **Advisory body (abridged)**: PostCSS does not escape `</style>` substrings in CSS string values when serialising. If untrusted CSS values flow through PostCSS into a `<style>` block, the closing tag breaks out of CSS context into HTML, enabling XSS.

### Why it matters (plain English)

PostCSS is the CSS pipeline transformer used by Next.js's build system. The Next.js install at `apps/web/node_modules/postcss` (per `/tmp/npm-audit-prod.txt:37`) is the only path. Exploitability requires untrusted user input to flow into a CSS value during build or runtime stringification — not a current attack surface for this project (the frontend uses Tailwind-style CSS through Next.js with no user-controlled CSS input). The advisory is real but the project doesn't currently expose the attack surface.

### Fix approach

- Same upgrade as FIND-NPMAUDIT-001 (`next@15.5.18`) — the `postcss` bump is transitive and resolves automatically.

### Complexity / severity

- Complexity: same as FIND-NPMAUDIT-001 (single upgrade resolves both).
- Severity: **MEDIUM** (per task spec for prod CVEs: follows npm-audit's `moderate` rating).

### Related findings

- `FIND-NPMAUDIT-001` (parent dependency).

## FIND-NPMAUDIT-003 — `@eslint/plugin-kit@0.2.8` + `eslint@9.17.0` ReDoS in `ConfigCommentParser` (low → low, dev-only)

- **Tool:** `npm audit 10.x`, raw outputs same as FIND-NPMAUDIT-001 (T-058).
- **Packages:**
  - `@eslint/plugin-kit` — installed `0.2.8`, vulnerable `<0.3.4`, fixed `0.3.4`+.
  - `eslint` — installed `9.17.0`, vulnerable `9.10.0 - 9.26.0` (depends on vulnerable `@eslint/plugin-kit`).
- **Fix proposed:** `eslint@9.39.4` (per `/tmp/npm-audit-full.txt:6`).
- **Prod / dev flag:** **dev-only** (`eslint` is declared in `apps/web/package.json` `devDependencies`; only invoked during `npm run lint` at CI build time, never bundled into the production runtime).
- **Advisory:** `GHSA-xffm-g5w8-qvg7` (CWE-1333 — Inefficient Regular Expression Complexity / ReDoS).
- **Advisory body (abridged)**: `@eslint/plugin-kit`'s `ConfigCommentParser` uses a regex with catastrophic backtracking on certain crafted comment payloads. Parsing a malicious ESLint config-comment can hang the lint process.

### Why it matters (plain English)

ReDoS in a lint-time tool is **low-impact**: the worst case is that a malicious `// eslint-disable-next-line` comment in a contributor's PR hangs the linter, which is a denial-of-service against the CI runner, not against runtime users. No code execution. The project's `code-health.yml:181-183` web-health step caps lint warnings at 9999 and pipes through `|| true`, so a hung lint would manifest as a CI timeout rather than a hidden vulnerability.

The package is also reachable through `eslint-config-next` (per T-009 `web-api-client-and-text.md` §8 and `infra-docker-and-compose.md` cross-reference): the dependency tree is `eslint-config-next → eslint → @eslint/plugin-kit`. Any lint config update that bumps `eslint` past `9.26.0` resolves the chain.

### Fix approach

1. Bump `eslint` to `9.39.4` via `npm install --save-dev --legacy-peer-deps eslint@9.39.4` — the transitive `@eslint/plugin-kit` bump comes along.
2. Verify ESLint's flat-config plugins (`next/core-web-vitals`, `next/typescript`) are compatible with eslint 9.39.x — they are (the `eslint` peerDep range is `>=8.57.0 || ^9.0.0 || ^10.0.0` per the lock-file inspection above).
3. Out of scope for T-058.

### Complexity / severity

- Complexity to fix: **trivial** (single devDep bump).
- Severity: **LOW** (per task spec for dev-only CVEs: original npm-audit `low` → downgraded one rank but already at floor — stays `low`).

### Related findings

- `FIND-KNIP-001` in `docs/code-health/01-dead-code.md` flagged `eslint-config-next` as unused; T-009 `web-api-client-and-text.md` §8 corrected that as a false positive. The eslint chain documented here is the same dep tree.

## FIND-NPMAUDIT-004 — esbuild dev-server CSRF + vite path-traversal + 3 transitive vitest packages (moderate → low, dev-only)

- **Tool:** `npm audit 10.x`, raw outputs same as FIND-NPMAUDIT-001 (T-058).
- **Packages (all dev-only):**

  | Package | Installed | Vulnerable range | Fixed | Own advisory? |
  |---|---|---|---|---|
  | `esbuild` | `0.21.5` (via `@vitejs/plugin-react → vite`) | `<=0.24.2` | `0.25.0+` | yes — `GHSA-67mh-4wv8-2f99` |
  | `vite` | `5.4.21` (via `@vitejs/plugin-react`) | `<=6.4.1` | `6.4.2+` | yes — `GHSA-4w7w-66w2-5vf9` |
  | `@vitest/mocker` | `2.1.9` | `<=3.0.0-beta.4` | `3.0.0+` | transitive via `vite` |
  | `vite-node` | `2.1.9` | `<=2.2.0-beta.2` | `2.2.0+` | transitive via `vite` |
  | `vitest` | `2.1.9` (pinned at `apps/web/package.json:30` `"vitest": "^2.1.9"`) | `0.0.1 - 0.0.12 \|\| 0.0.29 - 0.0.122 \|\| 0.3.3 - 3.0.0-beta.4` | `4.1.7+` (BREAKING) | transitive via `@vitest/mocker` + `vite` + `vite-node` |

- **Fix proposed:** `vitest@4.1.7` — per `/tmp/npm-audit-full.txt:16` flagged as a **breaking change** (vitest 2.x → 4.x crosses two majors).
- **Prod / dev flag:** **dev-only** (entire vitest + vite chain is `devDependencies` per `apps/web/package.json:30`; only used by `vitest.config.ts:14` `test.environment: "jsdom"` unit tests).

### Advisories (2 own + 3 transitive)

- **`GHSA-67mh-4wv8-2f99`** on `esbuild` (moderate, CWE-346 — Origin Validation Error): "esbuild enables any website to send any requests to the development server and read the response". Dev-server-only — affects `vite dev` mode where esbuild's HTTP dev server lacks CORS protection. Not relevant outside `npm run dev` / `vitest watch`.
- **`GHSA-4w7w-66w2-5vf9`** on `vite` (moderate, CWE-22 + CWE-200 — Path Traversal + Sensitive Info Exposure): dev-server-side path-traversal allowing arbitrary file read from the dev server's filesystem. Same dev-server-only scope.

### Why it matters (plain English)

Both advisories target the **dev server**, not the production bundle. The project's runtime artefact is `next build → next start` (per `apps/web/Dockerfile:15, :27` and `apps/web/playwright.config.ts:25`), which does not use Vite or esbuild's HTTP dev server. Vitest's `jsdom` environment runs in-process at test time, not via a dev server.

**Exploitation surface today**: a developer running `npm test` (vitest) locally inside a browser that visits a malicious site **could** theoretically be exposed to the esbuild dev-server CSRF — but only if vitest's transitive esbuild is actively listening on an HTTP port and the developer browses elsewhere during the test run. In the CI configuration at `ci.yml:274` (`npm test`) the test runner exits immediately after the suite; no long-lived dev server. **Production exposure: none.**

### Fix approach

The chain has **no in-major-version fix**:
- `vitest@2.x` (installed) is bound to vulnerable `vite@5.4.21` (per `npm list` above).
- `vitest@3.x` was the first non-vulnerable line.
- `npm audit fix --force` proposes `vitest@4.1.7` (skipping 3.x), which is two majors ahead and brings breaking API changes (vitest 4 removed `expect.poll`, changed several mock APIs).

Options for Phase 4:
1. **Conservative**: bump to `vitest@3.x` (e.g. `3.2.x`) which gets `vite@6.x` and resolves both advisories with smaller test-API drift than vitest 4. Manual upgrade, not what `npm audit fix --force` proposes.
2. **Aggressive**: take `npm audit fix --force`'s `vitest@4.1.7` and absorb the breaking-test-API churn.
3. **Status-quo**: accept the dev-only LOW severity until a production test-tooling brainstorm decides.

Out of scope for T-058.

### Complexity / severity

- Complexity to fix: **medium** (option 1 — conservative bump to vitest 3.x + verify the existing tests still pass) to **large** (option 2 — vitest 4 migration). Both are non-trivial relative to FIND-NPMAUDIT-001's clean `next` upgrade.
- Severity: **LOW** (per task spec for dev-only CVEs: original npm-audit `moderate` → downgraded one rank → `low`).

### Related findings

- None directly; this is the vitest test-tooling dev chain. `FIND-NPMAUDIT-003` is a sibling dev-only finding on the ESLint side.
