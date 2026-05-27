# Architecture Review 03 — Frontend Stack

**Scope.** Verdict-driven assessment of the Next.js + React + TypeScript frontend at `apps/web/`. 8 architectural questions with the locked 5-part format (current implementation + state-of-the-art alternative + verdict + perf implication + concrete improvement). Recommendations belong in Track 1c.

**Reality docs referenced**: T-008 (pages + components + grids), T-009 (`apiClient.ts` + infra/CI for web), T-036 §7 (frontend isolation already verdicted state-of-the-art at the macro level).

## 0. Verdict matrix at a glance

| # | Architectural choice | Verdict |
|---|----------------------|---------|
| 1 | Next.js 15.2.6 + App Router | **State-of-the-art** |
| 2 | React 19.0.1 | **State-of-the-art** |
| 3 | TypeScript 5.7.2 + `strict: true` + `noEmit` | **State-of-the-art** |
| 4 | 29 of 48 components mark `"use client"` (~60% client-side) | **Outdated** |
| 5 | No state-management library (no React Query / SWR / Zustand) | **Risky** |
| 6 | Manual fetch wrappers + 1879-line `apiClient.ts` with hand-typed responses | **Outdated** |
| 7 | Inline styles + `globals.css` (no Tailwind / no design system) | **Outdated** |
| 8 | Polling-heavy data refresh (18 `setInterval` sites) | **Risky** |

**Distribution**: 3 state-of-the-art + 3 outdated + 2 risky. **No "acceptable"** rating — the frontend is bimodal. Framework + language at leading edge; data + state + styling layer at conservative-2018 patterns.

## 1. Next.js 15.2.6 + App Router

### Current implementation

`apps/web/package.json`:
```json
"next": "15.2.6"
```

`apps/web/app/` directory exists (App Router; NOT `pages/` legacy router). Page layout per T-008 §3: 16 routed pages across `/`, `/portefeuille`, `/ibkr-acties`, `/decision-package/[id]`, `/instellingen`, `/admin/reconciliation`, `/volglijst`, etc.

`apps/web/next.config.ts`:
```typescript
const nextConfig: NextConfig = {
  reactStrictMode: true,
};
```

Minimal config — just `reactStrictMode: true` (which enables React's double-render warnings in dev). No experimental flags, no custom webpack config, no edge runtime overrides.

### State-of-the-art alternative

Next.js 15.2 IS the state-of-the-art (released early 2025). The App Router is the modern Next.js path; the Pages Router is in maintenance.

Modern alternatives that fully replace Next.js: **Remix** (now React Router v7), **TanStack Start**. But Next.js is the dominant choice in 2025; choosing it is the safe modern call.

### Verdict — State-of-the-art

Next 15.2 is current. App Router is the modern decision. `reactStrictMode: true` catches lifecycle bugs in dev. Minimal config = minimal surface area for bugs.

The only critique-direction is §4 below: the codebase doesn't take full advantage of App Router's RSC (React Server Components) capability — 60% of components are explicitly `"use client"`. That's not a Next.js choice, that's a usage pattern. The framework choice itself is leading-edge.

### Performance implication

Modern. Turbopack (dev), webpack (build), edge runtime support, native streaming SSR. None of these are used heavily yet but they're available.

### Improvement direction (for Track 1c)

None for the framework itself. See §4 for RSC underutilisation.

## 2. React 19.0.1

### Current implementation

`apps/web/package.json`:
```json
"react": "19.0.1",
"react-dom": "19.0.1",
"@types/react": "19.0.2",
"@types/react-dom": "19.0.2"
```

React 19 GA: December 2024 (~3 months before this audit). Type definitions explicitly aligned at 19.0.2. The codebase migrated quickly.

React 19 brings: `use()` hook for promise unwrapping, Server Components stable, Actions for form submissions, automatic batching extended.

T-030 §2.1 documented a historic bug related to `use()` — the codebase chose `useParams()` instead of `use(params)` because the latter required a Suspense boundary the parent layout didn't provide. The team encountered React 19's new features and adapted.

### State-of-the-art alternative

React 19 IS the state-of-the-art. Alternatives: Preact (lighter; loses ecosystem), SolidJS (faster reactivity; different mental model), Svelte 5 (compile-time reactivity).

For a Next.js codebase, the React version is effectively forced — Next 15 requires React 19. The choice is downstream of §1.

### Verdict — State-of-the-art

React 19 within ~3 months of GA. The codebase is actively keeping up with the React ecosystem.

### Performance implication

React 19 has improved automatic batching + Server Components. Concrete perf gains land mostly through RSC adoption (§4).

### Improvement direction (for Track 1c)

None for React itself.

## 3. TypeScript 5.7.2 + `strict: true` + `noEmit`

### Current implementation

`apps/web/package.json`: `"typescript": "5.7.2"`.

`apps/web/tsconfig.json`:
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "paths": { "@/*": ["./*"] }
  }
}
```

`strict: true` enables all strict checks (`strictNullChecks`, `strictFunctionTypes`, `strictBindCallApply`, `strictPropertyInitialization`, `noImplicitAny`, `noImplicitThis`, `alwaysStrict`, `useUnknownInCatchVariables`).

`noEmit: true` — TypeScript is a type-checker only; `next build` and the build pipeline handle code emission. Standard for Next.js.

T-056 (the TSC baseline) confirmed 0 production type errors; one test-fixture drift surfaced but doesn't block builds.

### State-of-the-art alternative

This IS state-of-the-art TypeScript configuration in 2025. The only stricter setting available is `noUncheckedIndexedAccess: true` (treats array access as `T | undefined`) — strong opinion-divider. The current config does NOT enable it.

### Verdict — State-of-the-art

TypeScript 5.7 is current (released late 2024). Strict mode is the modern minimum. The bundler-mode `moduleResolution` matches Next 15's bundler. `isolatedModules: true` ensures each file is independently transpilable (required by SWC + Turbopack).

T-056 confirming 0 prod type errors validates that the strict config is being respected by the codebase — not just enabled and ignored.

### Performance implication

`strict: true` adds type-check cost but the bundler doesn't see it (`noEmit`). `incremental: true` caches type-check results across runs. `skipLibCheck: true` skips node_modules type-checking.

### Improvement direction (for Track 1c)

Optionally enable `noUncheckedIndexedAccess: true` for stricter array-access safety. Optional only.

## 4. 60% of components are `"use client"`

### Current implementation

Grep proof:
- `grep -rln '"use client"' apps/web/app/ apps/web/components/` returns **29** files.
- `find apps/web/app apps/web/components -name "*.tsx" -not -name "*.test.tsx"` returns **48** files.
- **29 of 48 components are explicitly client-side** (~60%).

App Router default: components are server components unless they declare `"use client"`. Server components run on the server, render to HTML, and ship no JavaScript to the browser. Client components ship JavaScript and re-hydrate.

Each `"use client"` declaration creates a boundary: that component AND ALL its imported children become client. So 29 client roots may pull in significantly more code than the count suggests.

T-008 §1 documented the per-page split — most page wrappers (`page.tsx`) are server components that mount client components below.

### State-of-the-art alternative

The modern Next.js / React 19 pattern is "**server-first, client-when-needed**":
- Pages: server components by default.
- Data fetching: server-side (in the page component itself), passed down as props.
- Client islands: only for interactivity (forms, polling, drag-and-drop, etc.).

A typical RSC-heavy codebase has ~10-20% client components. The current 60% suggests interaction-heavy components OR overly broad `"use client"` declarations.

### Verdict — Outdated

The 60% client ratio defeats much of the App Router's purpose. Each `"use client"` boundary increases the client bundle size + forces client-side rendering + loses RSC's automatic data-loading benefits.

T-021 §3 documented `<PortefeuilleRealtimeSection>` polling 4 endpoints every 30s — that's a client component by necessity (polling needs browser timers). But T-028 documented `/admin/reconciliation/page.tsx` doing parallel fetches in `useEffect` — that could be a server component with the fetches happening server-side.

Each "use client" added without a strong reason is a missed opportunity. T-038 verdicts the pattern, not individual choices.

### Performance implication

**Larger initial JavaScript bundle.** Each client component adds to the hydration cost. For a dashboard with 5+ visible cards, that's significant network + CPU on first paint.

**No server-side prefetch.** Server components could pre-fetch the API data at request time + render with it; client components must request the data after hydration, creating a request waterfall.

### Improvement direction (for Track 1c)

Audit each `"use client"` for necessity. Convert truly-static-display components to server components. The result: smaller bundles + faster Time-to-Interactive.

## 5. No state-management library

### Current implementation

`apps/web/package.json` dependencies:
- `next`, `react`, `react-dom` only.

Grep proof:
- `grep -rln "zustand\|redux\|jotai\|recoil\|react-query\|tanstack-query\|swr" apps/web/` returns **zero** matches.

State is managed entirely with:
- `useState` for local component state.
- `useEffect` for side effects (data fetching, subscriptions).
- `useCallback` for memoised functions.
- Component composition for sharing state across siblings (lift state up).

No global store, no client-side cache, no automatic refetching, no optimistic updates, no request deduplication.

T-028 §2.1 documented the consequence: after every successful action (e.g., acknowledge a manual-review row), the entire page re-fetches **4 endpoints in parallel** via `Promise.all` — not because it needs to, but because there's no smaller-grained cache invalidation.

T-025 §6 documented: `<ColdStartBanner>` and `/volglijst/page.tsx` both poll `/watchlist/confirmation-state` independently. Acknowledging in one tab doesn't propagate to others until their polls catch up (up to 60s lag).

### State-of-the-art alternative

In 2025 React, **server state** (data from the API) and **client state** (UI-only state) are managed separately:
- **Server state**: TanStack Query (React Query) or SWR. Automatic caching, refetching, request deduplication, mutation orchestration, optimistic updates, retry logic.
- **Client state**: Zustand or Jotai for global. `useState` / `useReducer` for local.

For a dashboard polling 4-5 endpoints with shared data, TanStack Query reduces:
- Network requests (deduped across components).
- Re-renders (only on data change, not every poll tick).
- Code volume (replaces manual `useEffect` + `setInterval` orchestration).

### Verdict — Risky

The risk is operational + scale:
1. **Stale data ambiguity** (per T-025 §6 / T-028 §6) — different browser tabs / components see different "current state" depending on their poll cycle.
2. **No optimistic updates** — every action waits for server confirmation before UI updates (per T-026 / T-027 / T-028 patterns).
3. **Network noise** — 18 `setInterval` sites (§8) duplicate requests for the same data across components.
4. **Maintenance cost** — every component reimplements the same fetch + retry + error pattern by hand. Drift across implementations is inevitable.

The codebase works at single-user scale today. It would degrade quickly under any concurrent multi-tab + multi-user scenario.

### Performance implication

**Network overhead**: 18 independent `setInterval` cycles vs 1 deduped query layer = 18× the request count.

**Render cost**: every poll triggers a re-render even when data hasn't changed (no equality-check dedup).

### Improvement direction (for Track 1c)

Adopt TanStack Query for server state. Single biggest frontend-modernisation win.

## 6. Manual fetch wrappers + 1879-line `apiClient.ts`

### Current implementation

`apps/web/lib/apiClient.ts:1879 LOC`. Structure:
- `getJson<T>(path)` + `postJson<T>(path, body)` helpers (`:1356-1428`) — thin `fetch` wrappers that return a `FetchState<T>` discriminated union (`{ok: true, data: T} | {ok: false, message}`).
- `apiClient` object at `:1430` exporting ~80 named methods, each a one-line composition of `getJson` or `postJson` with a typed endpoint.
- Response types hand-declared above each section — e.g., `ColdStartWatchlistItem`, `ReconciliationStatusResponse`, etc. T-009 §2 inventoried this — every response type the backend produces is **manually re-declared** in TypeScript.

T-009 §2 documented this as a known finding: when the Python Pydantic models change, the TypeScript types must be hand-updated. The drift is held in check by tests, not by codegen.

### State-of-the-art alternative

- **OpenAPI codegen**: `openapi-typescript` or `orval` reads the FastAPI OpenAPI schema and generates TypeScript types automatically. Single source of truth.
- **`@hey-api/openapi-ts`** (modern open-source codegen): generates both types and a client.
- **End-to-end type safety via tRPC**: requires server + client share TypeScript; this codebase's Python backend rules this out.

For a Python backend + TypeScript frontend split, OpenAPI codegen is the canonical solution. FastAPI auto-generates the OpenAPI schema at `/openapi.json` — no extra backend work needed.

### Verdict — Outdated

Manual type re-declaration in 2025 is a 2018-era pattern. The 1879-LOC `apiClient.ts` is a maintenance hazard:
- Adding a new endpoint requires: backend implementation + Pydantic model + manual TS interface + manual `apiClient` method binding.
- Changing a backend response shape silently desyncs the frontend; only caught at runtime when the type expectation fails.

T-009 explicitly flagged this. T-038 verdicts it.

### Performance implication

No runtime perf impact. The cost is developer time + drift-induced bugs.

### Improvement direction (for Track 1c)

Generate TS types from `/openapi.json`. The `apiClient` methods can stay (they're thin wrappers); the type declarations can be regenerated per build.

## 7. Inline styles + `globals.css` (no Tailwind / no design system)

### Current implementation

- `apps/web/app/globals.css` — single global stylesheet.
- 16 components use inline `style={{}}` props (grep proof).
- No `tailwindcss`, no `styled-components`, no `emotion`, no `@stitches/react`, no `panda-css` in dependencies.
- No design tokens, no component library (no `shadcn/ui`, no `radix-ui`, no `mui`).

Sample inline-style pattern (from `<ColdStartBanner>` per T-025 §1):
```tsx
style={{
  background: "#fef3c7",
  color: "#92400e",
  border: "1px solid #fbbf24",
  padding: "10px 14px",
  borderRadius: 6,
  fontSize: 14,
  margin: "6px 0",
  display: "flex",
  gap: 12,
  alignItems: "center",
  justifyContent: "space-between",
}}
```

Colors, spacing, border radii are all magic numbers / hex codes scattered across components. No central tokens.

### State-of-the-art alternative

In 2025 React, the dominant styling approaches are:
- **Tailwind CSS v4** — utility-first, atomic CSS, design tokens via config. Massive ecosystem.
- **`shadcn/ui`** — copy-paste components built on `radix-ui` + Tailwind. Default for new React apps in 2024-2025.
- **CSS Modules** — older, simpler, no runtime cost.
- **Vanilla Extract** — type-safe CSS-in-TypeScript.

For a Dutch-localised Phase-1 trading dashboard, `shadcn/ui` + Tailwind is the path of least resistance to a coherent visual system.

### Verdict — Outdated

The current inline-style + globals.css pattern is what React looked like in 2018. Problems:
- **No design tokens** — `#fef3c7` appears in multiple components. Changing the warn-banner colour requires grep-and-replace.
- **No theme support** — dark mode would require touching every inline style.
- **No shared component primitives** — every button is restyled from scratch (T-025/T-026/T-027/T-028 documented 3 different button styles for similar actions).
- **No accessibility primitives** — `<button>` styled inline lacks the focus-visible + hover + disabled patterns that a library like Radix provides for free.

### Performance implication

Inline styles re-create style objects on every render. No CSS deduplication. The bundle ships every style declaration verbatim. For a small dashboard, the cost is negligible; for a large surface, it adds up.

### Improvement direction (for Track 1c)

Adopt Tailwind v4 + `shadcn/ui`. The migration can be incremental — new components use the new stack; old ones stay until refactored.

## 8. Polling-heavy data refresh (18 `setInterval` sites)

### Current implementation

Grep proof: `grep -rn "setInterval\|POLL_INTERVAL"` in `apps/web/components/` and `apps/web/app/` returns **18** sites.

Documented polling intervals per reality docs:
- `<ColdStartBanner>` — 60s (T-025 §1.2).
- `<PortefeuilleRealtimeSection>` — 30s (T-021 §3).
- Multiple status widgets — various intervals.

Each polling component:
1. Declares its own `POLL_INTERVAL_MS` constant.
2. Sets up `setInterval` in `useEffect`.
3. Tracks `cancelled` via a closure boolean.
4. Cleans up in the effect return.

No coordination across components. If 3 components want the same data at different intervals, the API gets 3 independent polling streams.

### State-of-the-art alternative

- **TanStack Query `refetchInterval`** — declarative polling per query; multiple components subscribing to the same query share one poll cycle.
- **Server-Sent Events (SSE)** — server pushes updates when state changes; eliminates polling entirely.
- **WebSockets** — bidirectional; overkill for read-only status updates.
- **Service Worker + Background Sync** — for true offline-first patterns.

For a moderate-traffic dashboard with multiple subscribers to the same status, TanStack Query + SSE is the modern combo: polling for endpoints that don't support SSE, push for ones that do.

### Verdict — Risky

The risk is twofold:
1. **Wasted bandwidth + server load** — every browser tab polling every 30-60s = N tabs × M components × 1 / interval = constant baseline traffic to the API even when nothing has changed.
2. **Race conditions** — independent polls produce independent "latest" state. T-025 §9.10 documented: `<ColdStartBanner>` and `/volglijst/page.tsx` poll the same endpoint independently; cross-tab consistency lags up to 60s. T-028 §7 documented the same pattern for the manual review queue.

Single-user / single-tab: invisible. Multi-tab / multi-user: visible.

### Performance implication

**Constant baseline traffic**. With ~5 components polling at average 60s = ~5 requests/minute per tab, baseline. Across 100 tabs = ~500 req/min just for status checks. The system-tick docs (T-031-T-035) didn't audit API capacity but per T-037 §2 the 40-thread sync threadpool would handle this comfortably until traffic grows.

### Improvement direction (for Track 1c)

Adopt TanStack Query (per §5 §6) — its `refetchInterval` deduplicates polls automatically. Evaluate SSE for the highest-frequency status updates.

## 9. Observations across the 8 questions

### 9.1 Pattern: bimodal stack — modern framework + 2018-era data layer

The split is striking: Next 15 / React 19 / TS 5.7 / strict mode are leading-edge. State + fetching + styling are 2018 patterns (useState everywhere, manual apiClient, inline styles, setInterval polling). The team adopted new framework features rapidly but stayed conservative on supporting libraries.

### 9.2 Pattern: hand-rolled where the ecosystem has solved problems

- Manual type re-declaration in `apiClient.ts` — OpenAPI codegen exists.
- Manual `setInterval` polling — TanStack Query exists.
- Manual style scattering — Tailwind exists.
- Manual cache invalidation (re-fetch all on action) — query-cache exists.

The codebase repeatedly chose "build it ourselves" where mainstream React tooling solves the same problem.

### 9.3 Pattern: 60% "use client" defeats App Router

Migrating to App Router (§1) + then marking 60% of components "use client" (§4) is a common-but-suboptimal pattern. The framework was chosen for RSC; the codebase doesn't use RSC. Net result: framework cost (App Router setup, server/client distinction) without framework benefit (smaller bundles, server-side data fetching).

### 9.4 What's clearly good

- Framework version currency (Next 15, React 19).
- TypeScript 5.7 + strict mode + 0 prod type errors (per T-056).
- ESLint 9 flat config + Next ruleset.
- Vitest + Playwright split (unit + e2e).

### 9.5 What's clearly outdated

- Client-component ratio (60% "use client").
- Manual `apiClient.ts` with hand-typed responses.
- Inline styles + globals.css (no Tailwind / no design tokens).

### 9.6 What's risky

- No state management → cross-tab consistency depends on poll cycles.
- 18 independent setInterval sites → bandwidth + race conditions at scale.

## 10. Summary table

| # | Question | Verdict | Track-1c priority |
|---|----------|---------|--------------------|
| 1 | Next.js 15.2 + App Router | State-of-the-art | None |
| 2 | React 19.0.1 | State-of-the-art | None |
| 3 | TypeScript 5.7.2 + strict | State-of-the-art | None |
| 4 | 60% "use client" | Outdated | **Medium** (RSC under-use) |
| 5 | No state management | **Risky** | **High** (TanStack Query) |
| 6 | Manual apiClient.ts | Outdated | **High** (OpenAPI codegen) |
| 7 | Inline styles + globals.css | Outdated | **High** (Tailwind + shadcn) |
| 8 | Polling-heavy refresh | **Risky** | **High** (coupled to §5) |

**Recommendations deferred to Track 1c.**

## 11. References

- `apps/web/package.json` — Next 15.2.6, React 19.0.1, TypeScript 5.7.2, ESLint 9, Vitest, Playwright
- `apps/web/tsconfig.json` — strict + noEmit + bundler module resolution
- `apps/web/eslint.config.mjs` — flat config + Next ruleset
- `apps/web/next.config.ts` — minimal config + reactStrictMode
- `apps/web/lib/apiClient.ts:1879 LOC` — manual fetch wrappers + hand-typed responses
- `apps/web/app/globals.css` — single global stylesheet
- `apps/web/app/` — 16 routed pages (T-008 §3 inventory)
- `apps/web/components/` — 48 .tsx files, 29 marked `"use client"`
- T-008 `web-pages.md`, `web-components-status-and-shared.md`, `web-components-feature-grids.md`
- T-009 `web-api-client-and-text.md` (the apiClient.ts inventory + manual-types finding)
- T-021 `portfolio-valuation-and-cost-basis.md` §3 (`<PortefeuilleRealtimeSection>` 30s polling)
- T-025 `user-confirm-starter-watchlist.md` §1.2 + §9.10 (`<ColdStartBanner>` 60s polling + cross-tab lag)
- T-028 `user-acknowledge-manual-review.md` §2.1 + §6 (4-endpoint re-fetch pattern)
- T-030 `user-review-decision-package-detail.md` §2.1 (useParams vs use() historic bug)
- T-036 §7 (frontend isolation — already state-of-the-art at macro level)
- T-056 `tsc --noEmit` baseline (0 prod type errors)
- T-058 `npm audit` baseline (web dependency CVEs)
