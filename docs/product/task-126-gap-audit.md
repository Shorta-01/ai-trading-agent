# Task 126 brief — gap audit against V1.1-feature-complete HEAD

**Audit date:** 2026-05-25
**Audit baseline:** commit `a84b56d` (Task 189: V1.1 release readiness — Slice 34). V1 (Slices 1–22, Tasks 145–177) and V1.1 (Slices 23–34, Tasks 178–189) are feature-complete.

This file is the bridge between the Task 126 brief (drafted in the
Task 125 era) and the project state after V1 + V1.1 shipped. Each
section states **what the brief asks**, **what HEAD already has**, and
**what Claude AI should do** with the resulting gap.

Legend for the action column:

- **DONE** — the brief item is already shipped (often differently from the brief but functionally equivalent). No action.
- **GAP** — the brief identifies a real outstanding gap. Claude AI should ship it, mechanically adapted to current HEAD.
- **OBSOLETE** — the brief item has been superseded by a V1/V1.1 lock. Skip it.
- **CONFLICT** — the brief contradicts a V1/V1.1 lock. Do NOT execute as-written; re-scope or refuse.
- **NEEDS DECISION** — owner must confirm the framing before Claude AI moves.

---

## 0. Top-level framing

| Brief assumes | HEAD reality | Action |
|---|---|---|
| We are at Task 125-ish; one PR will ship Task 126. | We are at Task 189 (V1.1 feature-complete). The next nominal step is V1.2 scope discussion per `next-task.md`. | **NEEDS DECISION** — owner must confirm whether this brief replaces the V1.2 scope discussion or runs alongside it. **Claude AI should NOT silently re-open V1.1 as if Task 126 is the active slice.** |
| One PR, 800–1400 LoC. | The genuinely-outstanding gaps (see §2 + §3 below) are M-sized but tractable. The schema rework (§3.3 below) is potentially L. | **GAP** — once owner approves, split into 2–3 PRs along the natural seams (badge UX, in-memory STORE cleanup, schema `ibkr_account_id` rollout). |

---

## 1. Items the brief asks for that are already DONE

### 1.1 Paper-only enforcement removal

- **Brief asks:** retire the paper-only-V1 lock; replace with mode-display-only doctrine.
- **HEAD:** Slice 13 (Task 168, `9effe41`'s ancestor) already relaxed `account_mode_mismatch` from a hard gate to an informational signal. `/ibkr/account/mode` exists at `apps/api/src/portfolio_outlook_api/status_routes.py:3208` and reports the detected mode without gating. The §21.1 V1 lock + the §22.x V1.1 locks both state explicitly that mode is reported, not enforced. The brief's `## Task 126 product locks` section to be added is effectively a duplicate of `## Task 127 decision lock` already in `docs/product/locked-decisions.md`.
- **Action:** **DONE** — Claude AI should NOT add a fresh "Task 126 product locks" section. If the owner wants the wording tightened, surface it under a renamed `## V1.1 mode-display lock review` block, not as a new task lock.

### 1.2 Top-strip mount in `app/layout.tsx`

- **Brief asks:** mount `AccountModeBadge` at the top of every screen.
- **HEAD:** `apps/web/app/layout.tsx` already imports + renders `<AccountModeBadge />`. The component is wired into the shell.
- **Action:** **DONE** for the mount. The badge implementation is a 5-line stub — see §2.1.

### 1.3 `apps/worker` directory exists

- **Brief asks:** create worker tree with `ibkr_gateway.py`.
- **HEAD:** `apps/worker/src/portfolio_outlook_worker/` exists with `config.py`, `health.py`, `main.py`, `storage_readiness.py`. The worker tree is a thin shell — no IBKR code, no APScheduler (that lives in `apps/api`).
- **Action:** **DONE** for the directory; **CONFLICT** for putting IBKR there — see §3.4.

### 1.4 Five IBKR snapshot tables

- **Brief asks:** add fields to "all five IBKR snapshot tables".
- **HEAD:** five tables exist with slightly different names:
  - `ibkr_sync_runs` (already has `account_mode TEXT NOT NULL`)
  - `ibkr_account_cash_snapshots` (has nullable `account_ref TEXT`)
  - `ibkr_position_snapshots` (has nullable `account_ref TEXT`)
  - `ibkr_open_order_snapshots` (has nullable `account_ref TEXT`)
  - `ibkr_execution_snapshots` (has nullable `account_ref TEXT`)
- **Action:** **DONE** for the tables existing; **GAP** for the `account_ref` → `ibkr_account_id NOT NULL` rename — see §3.3.

---

## 2. Items the brief asks for that are GENUINELY OUTSTANDING

### 2.1 `AccountModeBadge` real implementation

- **Brief asks:** polling component with three visual states (Paper neutral blue, Live amber, Disconnected grey), masked account ID, 500 ms first-mount flash.
- **HEAD:** `apps/web/components/AccountModeBadge.tsx` is **five lines** — renders a static `<StatusBadge label="Paper" status="vergrendeld" />`. It has not been touched since the paper-only era.
- **Action:** **GAP**. Claude AI should:
  1. Replace the stub with a `"use client"` component that polls `GET /ibkr/account/mode` every 30 s.
  2. Mask the account ID (prefix + last 4 chars). The current `/ibkr/account/mode` route returns mode + `display_label` but **not the account ID** — extend the route to include `account_id` (masked server-side is also OK, but client-side masking is fine since `/ibkr/account/mode` already lives behind the same trust boundary).
  3. Render three visual states per the brief's colour spec (neutral blue `#1e40af` / amber `#f59e0b` / grey `#6b7280`).
  4. 500 ms saturated flash on first mount.
  5. New Vitest test `apps/web/components/AccountModeBadge.test.tsx` covers all three states + masking.
  6. Keep Dutch wording: "Paper-rekening: DU•••4567", "Echte rekening: U•••7321", "Geen IBKR-verbinding".

### 2.2 `InMemoryIbkrSyncStore` legacy purge

- **Brief asks:** delete the module-level `STORE = InMemoryIbkrSyncStore()`. Routes should read from durable repositories. Brief claims "three in-memory STORE constructions"; only **one** exists.
- **HEAD:** `apps/api/src/portfolio_outlook_api/ibkr_sync.py:50` defines `class InMemoryIbkrSyncStore`, line 59 instantiates `STORE`, and **seven routes in `status_routes.py`** (lines 417, 441, 464, 482, 504, 526, 550) plus the legacy `run_sync` orchestrator (lines 265–293) all read/write `STORE` directly. `apps/api/tests/test_ibkr_sync_endpoints.py` clears it between tests.
- The V1 morning chain does NOT use `STORE` — it goes through `SqlAlchemyIbkrSyncSnapshotRepository` (durable). So `STORE` is genuinely stranded code on the `/ibkr/sync/*` legacy routes only.
- **Action:** **GAP**. Claude AI should:
  1. Replace each of the seven `from portfolio_outlook_api.ibkr_sync import STORE` lines in `status_routes.py` with reads against `SqlAlchemyIbkrSyncSnapshotRepository` (the same one the V1 morning chain already uses). The connection lifecycle pattern is already established in the Slice 33 `/claude/budget/status` route — copy that.
  2. Rewrite `ibkr_sync.run_sync(...)` to persist via the repository instead of `STORE.runs.append(...)`.
  3. Delete `class InMemoryIbkrSyncStore` + the module-level `STORE = ...` line.
  4. Update `test_ibkr_sync_endpoints.py` to seed/clean via the repo's fake or via SQLite-in-memory (consult `test_storage_unavailable_returns_503` patterns already used elsewhere).
  5. Add `test_ibkr_sync_routes_no_inmemory.py`: assert `grep "STORE = InMemoryIbkrSyncStore" apps/api/` returns nothing, and a unit test that mocks the storage layer down + asserts the route returns **HTTP 503 with Dutch error** `{"detail": "Opslag is niet beschikbaar. Synchronisatie kan niet worden uitgevoerd."}`. The fail-closed contract is genuinely new and worth pinning.

### 2.3 Real Portefeuille grid populated from durable IBKR data

- **Brief asks:** `/portefeuille` shows a real positions grid + cash card from `/ibkr/sync/positions/latest` and `/ibkr/sync/cash/latest`. Empty-state Dutch message. Disconnected banner.
- **HEAD:** `apps/web/app/portefeuille/page.tsx` already imports `IbkrPositionSnapshot`, `IbkrCashSnapshot`, etc. from `lib/apiClient`. **Inspection of the page is required** before declaring this DONE vs GAP — the imports being present is not proof the grid is wired end-to-end against real data.
- **Action:** **NEEDS DECISION → likely GAP**. Claude AI should:
  1. Read `apps/web/app/portefeuille/page.tsx` end-to-end and report whether the grid is already wired to `/ibkr/sync/positions/latest` + `/ibkr/sync/cash/latest`.
  2. If yes — confirm the empty-state Dutch message + disconnected banner exist; if not, ship them.
  3. If no — ship the grid + cash card + empty-state + disconnected banner per the brief.
  4. Either way, ship a Playwright smoke test that hits `/portefeuille` and asserts the badge is visible + the empty-state Dutch message appears when disconnected.

### 2.4 Dockerfile monorepo fixes

- **Brief asks:** API + worker Dockerfiles must copy `packages/{domain,storage,portfolio}` before installing; web Dockerfile must use `npm run build && npm start`.
- **HEAD:** all three Dockerfiles only copy the local `apps/<x>` tree and run `pip install --no-cache-dir .` (api/worker) or `npm install` + `npm run dev` (web). They will fail any monorepo-aware build because `packages/*` editable deps aren't present in the image.
- **Action:** **GAP**. Claude AI should:
  1. Rewrite the three Dockerfiles to build from the monorepo root: copy `packages/domain`, `packages/storage`, `packages/portfolio`; install them editable first; install the app last.
  2. Switch `apps/web/Dockerfile` to a production-shaped layout: `npm ci` → `npm run build` → `CMD ["npm", "start"]`.
  3. Verify `cd infra/docker && docker compose up --build` brings every service up with green healthchecks (or report which healthcheck doesn't exist yet — `apps/worker/health.py` already exists; the others need verification).
  4. **Do NOT add `psycopg[binary]>=3.2`** without first establishing what driver the storage layer currently uses (the brief says add it; `apps/api/pyproject.toml` doesn't currently list psycopg by name — investigate before adding).

### 2.5 `ibkr_account_id` tagging on snapshot tables + audit table

- **Brief asks:** new migration adds `ibkr_account_id TEXT NOT NULL` to all five snapshot tables + adds `ibkr_connection_audit` table.
- **HEAD:** snapshot tables use **nullable `account_ref TEXT`** instead. `system_events` table covers most of the connection-audit need (severity, event_code, related_entity_type / related_entity_id, technical_summary, redacted_details_json). No dedicated `ibkr_connection_audit` table exists.
- **Action:** **GAP, partially OBSOLETE**. Claude AI should:
  1. **Decision needed before coding**: should `ibkr_account_id` be a rename of `account_ref`, or a new NOT-NULL column with a backfill step? V1.1 ship rows may have `account_ref=NULL`. Default plan: ship migration `0045_ibkr_account_id_backfill` that (a) adds `ibkr_account_id TEXT` non-null with a `DEFAULT settings.ibkr_account_id` backfill, (b) drops `account_ref` after copy, (c) adds the new index `ix_ibkr_<table>_account_id`. Migration must be reversible.
  2. **Reject the new `ibkr_connection_audit` table** — `system_events` already covers it. Instead, emit `system_events` rows with `category='ibkr_connection'`, `event_code` ∈ `{connect_attempt, connect_success, connect_refused, mode_check_prefix, mode_check_behavioural, disconnect, session_error}`, `related_entity_type='ibkr_account'`, `related_entity_id=ibkr_account_id`. Add a thin filtered view `/ibkr/connection/audit?limit=20` that queries `system_events` with the category filter.
  3. Mass-update `IbkrSyncRunRecord` + every snapshot record dataclass to require non-empty `ibkr_account_id` per the invariant pattern V1.1 uses everywhere (`__post_init__` check).
  4. New tests:
     - `test_ibkr_account_id_migration.py` — assert columns added + index added + downgrade restores `account_ref`.
     - `test_ibkr_connection_audit_via_system_events.py` — append-only behaviour, list_recent ordering filtered by category.

### 2.6 `GET /ibkr/connection/status` route

- **Brief asks:** route returns `{connected, account_id, account_mode, verified_at, error}`.
- **HEAD:** `/ibkr/account/mode` exists but only returns `{status, mode, display_label, expected_environment, help_nl, safe_for_orders, blocks_orders}`. No `connected` boolean. No `verified_at`. No `account_id`.
- **Action:** **GAP**. Claude AI should:
  1. Extend `/ibkr/account/mode` to additionally return `account_id` (masked or full — owner call) + `verified_at` (timestamp of the most recent successful sync run from `ibkr_sync_runs`) + `connected` (boolean derived from "most recent sync run within the last N minutes"). Avoid adding a parallel `/ibkr/connection/status` route — the V1 surface is already locked at `/ibkr/account/mode`.
  2. Pin the new fields in `test_ibkr_status_endpoint.py`.
  3. The `AccountModeBadge` (§2.1) consumes these new fields.

### 2.7 Test coverage from brief that doesn't exist

- **Brief asks:** specific test files: `test_ibkr_gateway.py`, `test_ibkr_gateway_decimal.py`, `test_ibkr_sync_routes_no_inmemory.py`, `test_ibkr_connection_status_route.py`, `AccountModeBadge.test.tsx`, Playwright smoke.
- **HEAD:** none of these exist. `test_ibkr_status_endpoint.py` exists but doesn't cover the new fields.
- **Action:** **GAP**. Ship each test file alongside the matching production change in §2.1–§2.6. **Skip `test_ibkr_gateway*.py`** — see §3.4.

---

## 3. Items where the brief CONFLICTS with V1/V1.1 locks

### 3.1 `ib_insync` dependency

- **Brief asks:** add `ib_insync>=0.9.86` to the worker.
- **HEAD:** `apps/api/pyproject.toml` declares `ibapi==9.81.1.post1`. V1 + V1.1 shipped 60+ source files against `ibapi` (`IbapiOrderSubmissionClient`, `IbkrIbapiSyncClient`, `IbkrIbapiClientFacade`, etc.). Adding `ib_insync` would create a second broker boundary that has to be kept in sync with the first.
- **Action:** **CONFLICT — do NOT add `ib_insync`.** The brief was written before the V1 broker-boundary work crystallised on `ibapi`. Claude AI should reuse the existing `ibapi` clients in `apps/api` for any new connection-status / mode-detection code, not introduce a parallel library.

### 3.2 Per-submission mode verification field

- **Brief asks:** add `account_mode_at_event` to the audit log schema "reserved for future action-draft task; not implemented yet."
- **HEAD:** V1 Slice 7 (Task 162) already ships `asset_action_draft_events` with full state-machine event logging, and Slice 32 (Task 187) widened the locked order types to include CONDITIONAL. The action-draft path is end-to-end live, not "future".
- **Action:** **OBSOLETE**. The brief item is for a code path that already exists. If the field is missing on `asset_action_draft_events`, it's a real gap; **otherwise skip.** Claude AI should: read `asset_action_draft_events` schema, confirm `account_mode_at_event` exists or is implicit (via `provider_account_mode` on related tables), report back, and only add a column if genuinely absent.

### 3.3 "Three in-memory STORE constructions" / line numbers

- **Brief asks:** "Delete the module-level `STORE = InMemoryIbkrSyncStore()` (line 113) entirely". Brief later: "The three in-memory STORE constructions in `apps/api/.../ibkr_sync.py` are deleted."
- **HEAD:** there is **one** `STORE = InMemoryIbkrSyncStore()` at line **59** (not 113). The class itself is at line 50.
- **Action:** **CONFLICT in mechanics, GAP in intent**. Claude AI should silently adapt line/count numbers but keep the intent — see §2.2.

### 3.4 IBKR gateway in `apps/worker`

- **Brief asks:** new module `apps/worker/src/portfolio_outlook_worker/ibkr_gateway.py` with `IbkrGateway.connect/disconnect/fetch_positions/etc.`. Worker owns the IBKR session.
- **HEAD:** V1 + V1.1 chose `apps/api` as the IBKR session owner. `IbkrIbapiSyncClient` + `IbapiOrderSubmissionClient` live in `apps/api`. The scheduler that fires the morning chain lives in `apps/api`. Moving IBKR ownership to `apps/worker` now would require relocating the morning chain, the order submission factory, and the audit-pad reconciliation — a multi-slice refactor.
- **Action:** **CONFLICT — do NOT relocate IBKR to the worker.** The V1/V1.1 architecture decision is settled. If the owner wants IBKR work split between API (synchronous request handling) and worker (long-running broker session), that's a V1.2 architectural slice that needs its own scope discussion. **Claude AI should ship §2.x against the existing `apps/api` IBKR clients.**

### 3.5 "No new readiness-contract fields"

- **Brief asks:** "No new readiness-contract fields. `analysis_ready`, `suggestions_allowed`, `action_drafts_allowed` etc. are not touched in this task."
- **HEAD:** V1 Slice 22 (Task 177) shipped the `release_readiness` scorecard with 15 blocker codes; V1.1 Slice 34 (Task 189, just merged) added 5 more for the §22 surface. The readiness contract is the load-bearing operator surface.
- **Action:** **OBSOLETE constraint**. Claude AI should ignore the "no new readiness fields" guidance — that lock was V1-stage. The current scorecard is the right place to thread any new IBKR-connection blockers. **However: don't add readiness fields opportunistically.** If §2.2's fail-closed contract surfaces a new gate (e.g. `ibkr_connection_unavailable`), add it as a new V1.1 / V1.2 blocker code through the established pattern.

---

## 4. What Claude AI should do — consolidated action list

When the owner authorises the work, Claude AI should ship the gaps in this order. Each numbered group is a separate PR.

### PR 1 — Mode-display polish + `/ibkr/account/mode` extension (S, ~150 LoC)

- Extend `GET /ibkr/account/mode` to include `account_id`, `verified_at`, `connected` (per §2.6).
- Replace the `AccountModeBadge` stub with the polling component (per §2.1).
- Update `test_ibkr_status_endpoint.py` + add `AccountModeBadge.test.tsx`.
- Verify the badge mounts correctly on `/portefeuille` and renders all three states.
- No schema change. No new routes. No `apps/worker` changes.

### PR 2 — `InMemoryIbkrSyncStore` legacy purge + fail-closed contract (M, ~400 LoC)

- Per §2.2: replace `STORE` reads in all 7 `status_routes.py` route handlers + `ibkr_sync.run_sync` with durable repo reads.
- Delete `class InMemoryIbkrSyncStore` + the module-level `STORE`.
- Update existing `test_ibkr_sync_endpoints.py` to use a real (sqlite in-memory) or fake repository.
- Add `test_ibkr_sync_routes_no_inmemory.py` with the fail-closed-503 assertions.
- Confirm the V1 acceptance test (`test_v1_acceptance.py`) still passes — it must, because the morning chain already uses the durable path.

### PR 3 — Portefeuille grid wire-up + Dockerfile monorepo fixes (M, ~400 LoC)

- Audit `apps/web/app/portefeuille/page.tsx` end-to-end and ship whatever's missing from §2.3.
- Add the disconnected banner + empty-state Dutch message.
- Playwright smoke covering both states.
- Fix the three Dockerfiles per §2.4. Verify `docker compose up --build` end-to-end.
- **No** `psycopg[binary]` addition without investigating the existing driver story first.

### PR 4 — `ibkr_account_id` schema rollout (M–L, ~500 LoC) — **NEEDS OWNER DECISION FIRST**

- Per §2.5: decide between rename (`account_ref` → `ibkr_account_id`) vs additive (keep both during transition).
- Migration `0045_ibkr_account_id_rollout` (forward + downgrade).
- Update every IBKR snapshot record + the `IbkrSyncRunRecord` dataclass.
- Reject the brief's separate `ibkr_connection_audit` table — reuse `system_events` per §2.5.
- Ship the `/ibkr/connection/audit?limit=20` filtered view as a thin `system_events` query.
- Backfill rows with `settings.ibkr_account_id` where the column is being made NOT NULL.

### PR 5 — Doc + lock cleanup (XS, ~50 LoC)

- **Do NOT** add a fresh `## Task 126 product locks` section to `locked-decisions.md` — the locks are already in `## Task 127 decision lock` + `## IBKR account mode and user approval lock`.
- Move the original "paper-only-V1" line to a `## Retired locks` section at the bottom with date + reason.
- Update `current-state.md` + `task-history.md` per the existing project-tracking pattern.

### Explicit NO-OPs for Claude AI

Even if the brief asks for them, Claude AI should **NOT**:

1. Add `ib_insync` to any pyproject (§3.1).
2. Relocate IBKR session ownership from `apps/api` to `apps/worker` (§3.4).
3. Create a new `ibkr_connection_audit` table (§2.5 — reuse `system_events`).
4. Add a new `## Task 126 product locks` section to `locked-decisions.md` (§5).
5. Hard-delete `account_ref` columns without a backfill step (§2.5).
6. Mass-rename any existing route from `/ibkr/account/mode` to `/ibkr/connection/status` — keep URL stability (§2.6).
7. Touch the V1.1 readiness scorecard contract unless adding a clearly-scoped new blocker code (§3.5).

---

## 5. Open questions for the owner before any PR ships

1. **Framing**: does this Task 126 brief replace the V1.2 scope discussion, or is it the V1.1.x runtime cleanup that lands before V1.2 starts? Recommended: name it "V1.1 runtime hardening" and explicitly position it as a bridge between V1.1-feature-complete and V1.2-scope-discussion.
2. **`apps/worker` future**: is the worker shell going to stay thin (V1.1 baseline) or is V1.2 the slice that activates it (e.g. long-running broker session, queue worker for AI calls)? This decision shapes PR 4 because the `ibkr_account_id` rollout should NOT precede a clear answer.
3. **Driver choice**: what Postgres driver is the V1.1 storage layer using in production today? The brief says add `psycopg[binary]>=3.2` but the current pyproject doesn't list it by name. Claude AI should investigate before adding.
4. **PR sequencing**: ship the five PRs in series (safer, slower) or parallel where independent (PR 1 + PR 5 can be standalone)?

---

## 6. Summary one-liner

The Task 126 brief is mostly **already done** (paper-only retirement, top-strip mount, snapshot tables) or **conflicts with V1 locks** (ib_insync, worker-owned IBKR). The genuinely outstanding gaps are: AccountModeBadge stub, InMemoryIbkrSyncStore legacy purge, Portefeuille grid wire-up, Dockerfile monorepo fixes, `/ibkr/account/mode` field extension, and the `account_ref` → `ibkr_account_id` schema rollout. Five small-to-medium PRs cover all real gaps; PR 4 needs an owner decision before code starts.
