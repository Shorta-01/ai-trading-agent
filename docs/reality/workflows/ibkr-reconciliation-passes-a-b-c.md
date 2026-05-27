# IBKR Reconciliation — Periodic Backstop (Passes A / B / C)

**Scope.** End-to-end trace of one reconciler tick — APScheduler trigger (intended) → single-flight lock → IBKR connection gate → strict `Pass A → Pass B → Pass C` ordering → 4 append-only audit tables → API read surface (6 GET routes + 1 POST acknowledge). The reconciler is the **backstop** beneath the event-stream sync — it detects and heals divergence between the system's local state and IBKR truth (intent §1, doctrine §6).

**Intent**: `docs/intent/reconciliation.md` (locked 2026-05-26). **Decision**: `docs/decisions/0010-reconciliation-architecture.md`. **Component reality**: T-007 `docs/reality/components/worker-actions-and-reconciliation.md` §§8-12. **Sibling workflow**: T-019 `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (the sweep that creates the in-flight state Pass B watches).

## 0. TL;DR

| Step | Site | Outcome |
|------|------|---------|
| Tick fires (intended) | not wired in `scheduler.py` (Phase 1c) | `IbkrReconciler.tick()` invoked |
| Single-flight lock | `reconciler.py:185` | `try_acquire()` — fail → `mode_detected="skipped_locked"` |
| Open audit row | `reconciler.py:210` | `reconciliation_run_audit` row inserted with `completed_at=NULL` |
| Connection gate | `reconciler.py:225` | `gateway.is_connected()` — false → `mode_detected="skipped_disconnected"` |
| Pass A — orphaned executions | `reconciler.py:249` → `pass_a_orphaned_executions.py:125` | Fills IBKR has that we missed |
| Pass B — stale in-flight | `reconciler.py:260` → `pass_b_stale_in_flight.py:129` | Drafts we think are in-flight that IBKR reports terminal |
| Pass C — 24h timeout | `reconciler.py:269` → `pass_c_timeout_recovery.py:73` | `awaiting_reply_timeout` drafts older than 24h → `requires_manual_review` |
| Close audit row | `reconciler.py:327` | `complete_run` flips `completed_at` + per-pass counts |

**Locked failure modes** (the `ReconcilerMode` Literal at `reconciler.py:62-67`): `completed | skipped_locked | skipped_disconnected | error`. **The orchestrator never raises through to APScheduler** — every outcome lands in `IbkrReconcilerResult` + the audit row.

## 1. Trigger model — intent vs reality

### 1.1 Intent (locked, `docs/intent/reconciliation.md` §1)

**Periodic baseline:**
- Every **15 minutes during market hours** (any configured exchange in its primary session).
- Every **hour outside market hours** (positions can still drift via dividends, corporate actions, manual broker activity).

**Five event triggers:**
1. **07:00 before the morning chain** — **mandatory; blocks the morning chain** until complete. If reconciliation fails to finish, the morning chain does not run, the dashboard shows the previous day's state, and the system-health line turns red.
2. **After every order fill** — re-verify post-fill state.
3. **After IBKR session reconnect** — anything could have changed during the disconnect.
4. **On user demand** — button per `docs/intent/settings-and-credentials.md` Category 5.

### 1.2 Reality

`IbkrReconciler.tick()` (`reconciler.py:181-202`) is a no-arg method designed to be invoked by an APScheduler job ("Wired into APScheduler as a no-arg `tick()` invocation" — `reconciler.py:142`). **It is NOT actually wired into APScheduler.** `apps/worker/src/portfolio_outlook_worker/scheduler.py:141-165` registers three jobs (`_on_pre_briefing` at 06:00, `_on_hourly` at 7-21, `_heartbeat` interval) — none of them call `IbkrReconciler.tick()` or any wrapper around it.

Grep verification — `IbkrReconciler` is only referenced inside its own module + the `__init__.py` re-export + unit tests:

```
$ grep -rn "IbkrReconciler" apps/worker/src/ | grep -v test
apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/__init__.py:41:    IbkrReconciler,
apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py:139:class IbkrReconciler:
```

**Operationally**: there is no production scheduling layer for reconciliation. The class is unit-tested (`apps/worker/tests/test_reconciler_orchestrator.py`) but never instantiated in a runtime entry point. None of the five event triggers are wired either:

| Intent trigger | Reality |
|----------------|---------|
| 15min market-hours cadence | not wired |
| 1h off-hours cadence | not wired |
| 07:00 morning-chain block | not wired — `pre_briefing` runs unconditionally (T-011) |
| After order fill | not wired |
| After IBKR reconnect | not wired |
| On user demand | not wired — no manual-trigger API route exists (§5) |

This is the single largest intent-vs-reality gap in the reality audit so far. See §9.1.

## 2. The orchestrator — `IbkrReconciler.tick()`

### 2.1 Class

`IbkrReconciler` (`reconciler.py:139-346`). Constructor injects the gateway adapter, the lock, two IBKR fetchers (executions + order-status), and **seven storage repositories** + a `now_provider` clock (`:148-179`).

### 2.2 Top-level `tick()` (`reconciler.py:181-202`)

```text
started = now()
run_id = run_id_factory()                       # _default_run_id_factory: f"recon-{uuid4().hex[:16]}"
if not lock.try_acquire():                      # :185
    return _empty_run_result(mode="skipped_locked")
try:
    return self._run_locked(run_id, started)
finally:
    lock.release()                              # :198 — release failure logged, never re-raised
```

The `try / finally` guarantees the lock is released on any path, including the in-pass exception path. Lock-release failures are logged via `logger.exception` (`:199-202`) but do not propagate.

### 2.3 The lock — shared with the submission sweep

`SingleFlightLockProtocol` (declared in `apps/worker/src/portfolio_outlook_worker/single_flight_lock.py:33`). Production uses `PostgresAdvisoryLock` with the `ORCHESTRATOR_LOCK_KEY` constant (`single_flight_lock.py:30`).

**The reconciler shares the SAME lock with the submission sweep** (T-019 §1) — `ORCHESTRATOR_LOCK_KEY` is one global advisory key. Consequence: at most one of {sweep, reconciler, morning chain} runs at a time across the entire worker fleet. The first to `try_acquire()` runs; others get `mode="skipped_locked"` for that tick.

### 2.4 The `_run_locked` body (`reconciler.py:204-346`)

Step-by-step:

1. **Insert the open run-audit row** (`:210-223`). `reconciliation_run_audit` row with `completed_at=None`, `mode_detected="completed"` (tentative — finalised below). The row exists from the moment the lock is held so that a crash in-flight is still visible. `pass_*_count` fields are 0 at this point.

2. **Connection gate** (`:225-242`). `if not self._gateway.is_connected()`: write `complete_run(mode="skipped_disconnected")` and return. Pass A + Pass B both require IBKR connectivity (Pass A fetches executions, Pass B fetches order statuses); the gate short-circuits before any IBKR call.

3. **Strict pass invocations** inside a `try / except Exception`  (`:248-319`):
   - `pass_a = run_pass_a_orphaned_executions(...)` — `:249-259`
   - `pass_b = run_pass_b_stale_in_flight(...)` — `:260-268`
   - `pass_c = run_pass_c_timeout_recovery(...)` — `:269-276`

   **The pass order is hard-coded** — Pass A runs before Pass B before Pass C. The pass functions themselves never raise through (each catches per-row failures and counts them as divergences); the `try / except Exception` at the orchestrator level is a defence-in-depth fallback.

4. **Fatal-exception path** (`:277-319`). If any pass somehow does raise through, the orchestrator captures:
   - `error_details = {"class": type(exc).__name__, "message": str(exc), "pass_a_completed": pass_a is not None, ...}`
   - Counts already-collected divergences from completed passes.
   - `complete_run(mode_detected="error", error_details_json=error_details)`.
   - Returns an `IbkrReconcilerResult(mode="error", ...)` with whatever passes did complete.

5. **Success path** (`:321-346`). Sum divergences, `complete_run(mode_detected="completed", divergences_found=total)`, return the full `IbkrReconcilerResult`.

### 2.5 Run-ID factory

`_default_run_id_factory` (`reconciler.py:366-367`) returns `f"recon-{uuid4().hex[:16]}"` — 16 hex characters of a UUID4. The reconciler does NOT use a sequence number; collision risk is `2^-64` per tick, ample for the cadence intent.

## 3. Pass A — Orphaned executions

**Module**: `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_a_orphaned_executions.py` (418 lines).
**Entry**: `run_pass_a_orphaned_executions(...)` at `:125`.
**Detects**: fills that IBKR has but the worker missed (e.g., callback dropped, worker crashed mid-fill, network glitch during the lifecycle handler's window).

### 3.1 Algorithm (`:145-218`)

```text
observed = fetcher.fetch_recent_executions(account_id=...)        # :145

for execution in observed:                                         # :152
    if executions_repo.get_by_exec_id(execution.ibkr_exec_id) is not None:  # :153
        already_recorded += 1                                       # idempotent — Pass A already saw this
        continue
    if unmatched_repo.get_by_exec_id(execution.ibkr_exec_id) is not None:   # :157
        already_recorded += 1                                       # flagged on previous tick — don't double-record
        continue
    draft_id = submission_audit_repo.get_action_draft_id_for_perm_id(execution.ibkr_perm_id)
    if draft_id is None:                                            # :166
        _record_unmatched_execution(...)                            # :167 — no local draft for this perm_id
        unmatched_recorded += 1
        continue
    draft = action_draft_repo.get_by_id(draft_id)
    if draft is None:                                               # :179
        _record_unmatched_execution(...)                            # :183 — orphan, draft deleted
        unmatched_recorded += 1
        continue
    healed = _apply_missing_execution(execution, draft, ...)        # :194 — heal flow
    if healed:
        missing_applied += 1
```

### 3.2 Two outcome flows

**Flow A1 — `unmatched_execution`** (`:226-272`). When the fill cannot be matched to a local draft:
- Insert `unmatched_execution_audit` row (`:235-248`) with `resolution_status="unresolved"`. UNIQUE constraint on `ibkr_exec_id` makes this idempotent — re-running the same tick produces zero new rows.
- Insert `reconciliation_audit` row (`:250-271`) with `pass_name="orphaned_execution"`, `divergence_type="unmatched_execution"`, `action_draft_id=None`, `notes_dutch="Niet-gekoppelde IBKR-uitvoering gedetecteerd; geen actie ondernomen op een Action Draft."`.
- **No state-machine transition is written** — Pass A does not heal a draft that doesn't exist.

**Flow A2 — `missing_execution_applied`** (`:275-376`). When the fill matches a local draft but the execution row is missing locally:
- Insert `ibkr_executions` row (`:289-303`) with the fill details.
- If the draft is still non-terminal, `action_draft_repo.apply_lifecycle_transition(...)` widens the draft into the appropriate post-fill state (e.g., `filled` for a full fill).
- Insert `reconciliation_audit` row with `divergence_type="missing_execution_applied"` (`:311`). Captures `before_status / after_status` so the audit trail shows exactly what changed.

### 3.3 Divergence types written

From the CHECK constraint at `0053_reconciliation_audit_and_manual_review.py:101-111` and `metadata.py:2950-2959`:

| Pass A divergence_type | Meaning |
|------------------------|---------|
| `unmatched_execution` | IBKR fill cannot be linked to any local draft |
| `missing_execution_applied` | IBKR fill linked + missing execution row inserted + draft healed |

### 3.4 Idempotency

Pass A is idempotent on the `ibkr_exec_id` axis: re-runs see the row already in `ibkr_executions` (UNIQUE) or `unmatched_execution_audit` (UNIQUE) and short-circuit. Re-runs cannot double-heal a draft because `apply_lifecycle_transition` checks the current status.

### 3.5 Result

`PassAOrphanedExecutionsResult` (`:105-117`): `executions_observed, executions_already_recorded, missing_execution_applied, unmatched_execution_recorded, divergences_found, healed_draft_ids, unmatched_exec_ids`.

## 4. Pass B — Stale in-flight

**Module**: `pass_b_stale_in_flight.py` (443 lines).
**Entry**: `run_pass_b_stale_in_flight(...)` at `:129`.
**Detects**: drafts the worker thinks are in-flight (states `submitted`, `accepted`, `working`, `partially_filled`, `pending_cancellation`) that IBKR no longer reports as in-flight — typically because the lifecycle callback never arrived.

### 4.1 Active-draft scan (`:146`)

```text
drafts = action_draft_repo.list_active_for_account(ibkr_account_id=account_id)
```

`list_active_for_account` filters drafts to the **in-flight states** (`storage` layer — the union of non-terminal post-submission statuses).

### 4.2 Per-draft algorithm (`:156-323`)

For each in-flight draft:

1. **Resolve the latest `ibkr_perm_id`** for the draft via `_resolve_perm_id_for_draft` walking `ibkr_submission_audit` (`:161-164`). A draft may have a `rejected_at_send` followed by a successful retry — Pass B follows the latest `placed` perm_id.
2. **Skip if no perm_id** (`:165-167`) — the draft was never successfully placed; let Pass C handle it via the `awaiting_reply_timeout` path.
3. **`status = fetcher.fetch_order_status(perm_id, account_id)`** (`:170-173`). Network errors are caught (`:174-181`) and the draft is skipped (counted as `skipped`).
4. **`status.found_in_ibkr=False`** (`:185-196`) — IBKR has never heard of this perm_id. Write `terminal_divergence_logged` reconciliation_audit row + count as divergent. No state change.
5. **Unknown raw status** (`:198-213`) — IBKR returned a status string we don't know how to map. Write `terminal_divergence_logged` + count as divergent. No state change (intentionally conservative).
6. **`mapped not in _IBKR_TERMINAL_STATUSES`** (`:215-218`) — IBKR agrees the draft is in-flight. Count as `in_sync`.
7. **`mapped == draft.status`** (`:220-225`) — both sides already agree. Count as `in_sync`.
8. **Healing path** (`:227-322`) — IBKR reports a terminal state and we don't have it locally:
   - `action_draft_repo.apply_lifecycle_transition(action_draft_id, new_status=mapped, transitioned_at=event_at)` (`:229-233`).
   - If transition fails: write `terminal_divergence_transition_failed` row + count as divergent. (Doctrine: never silently lose state.)
   - On success: write `reconciliation_audit` row with `pass_name="stale_in_flight"`, `divergence_type=_corrected_divergence_for(updated.status)`.

### 4.3 Divergence types written

The `_corrected_divergence_for` map writes one of:

| Pass B divergence_type | Meaning |
|------------------------|---------|
| `status_corrected_to_filled` | IBKR reports filled, local was non-terminal |
| `status_corrected_to_partially_filled` | IBKR reports partial fill |
| `status_corrected_to_cancelled` | IBKR reports cancelled |
| `status_corrected_to_rejected` | IBKR reports rejected |
| `terminal_state_divergence_logged` | IBKR-side state could not be applied / unknown raw status / not found in IBKR |

### 4.4 No time-based thresholds in code

The intent doc's classification table (`docs/intent/reconciliation.md` §4) reads:

| Pass | B threshold | C threshold | D threshold | E threshold |
|------|-------------|-------------|-------------|-------------|
| B    | n/a         | < 5min stale → C | 5–30min → D | > 30min → E |

**These thresholds are NOT implemented.** Pass B does not consult an age field — it queries IBKR live for every in-flight draft on every tick and compares results. Every divergence Pass B detects gets the same `status_corrected_*` divergence_type regardless of how long the draft was stale. The B/C/D/E tier strings (`tier_b`, `tier_c`, etc.) do not appear anywhere in the reconciliation modules.

### 4.5 Result

`PassBStaleInFlightResult`: `drafts_evaluated, drafts_skipped_no_perm_id, drafts_skipped_fetch_failed, drafts_in_sync, drafts_healed, drafts_with_divergence, divergences_found, healed_draft_ids, divergent_draft_ids`.

## 5. Pass C — 24h timeout escalation

**Module**: `pass_c_timeout_recovery.py` (179 lines).
**Entry**: `run_pass_c_timeout_recovery(...)` at `:73`.
**Detects**: drafts in `awaiting_reply_timeout` that have been there longer than `TIMEOUT_CUTOFF = timedelta(hours=24)` (`:46`). Escalates them to `requires_manual_review`.

### 5.1 The 24h cut-off

Module-level constant `TIMEOUT_CUTOFF = timedelta(hours=24)` at `pass_c_timeout_recovery.py:46`. The comment at `:45` reads `# Task 135 product lock §4 — 24h cut-off, not configurable.` The cut-off is **hard** — there is no partial-credit "almost 24h" mode (docstring `:22-25`).

### 5.2 Algorithm (`:84-161`)

```text
timeouts = action_draft_repo.list_by_status(account_id, "awaiting_reply_timeout")   # :84
now = now_provider()

for draft in timeouts:
    if draft.terminal_state_at is None:                              # :94
        missing_ts += 1
        continue
    # Tz-agnostic subtraction (SQLite pysqlite drops tzinfo on round-trip).
    age = now_naive - terminal_state_at_naive                         # :101-107
    if age < TIMEOUT_CUTOFF:                                          # :108
        within_cutoff += 1
        continue
    # Escalation:
    updated = action_draft_repo.apply_lifecycle_transition(
        action_draft_id=draft.action_draft_id,
        new_status="requires_manual_review",                          # :116
        transitioned_at=now,
    )
    manual_review_repo.append(ManualReviewQueueEntry(                 # :126-139
        flagged_at=now,
        action_draft_id=draft.action_draft_id,
        reason="timeout_24h_no_data",
        details_dutch=(
            "Action Draft is langer dan 24 uur in awaiting_reply_timeout "
            "zonder dat IBKR een uitvoering, status-update of annulering "
            "heeft teruggemeld. Handmatige beoordeling vereist."
        ),
        resolution_status="pending",
    ))
    reconciliation_audit_repo.append(ReconciliationAuditEntry(        # :140-159
        pass_name="timeout_recovery",
        divergence_type="timeout_flagged_manual_review",
        before_status=before_status,                                  # was "awaiting_reply_timeout"
        after_status=updated.status,                                  # now "requires_manual_review"
        ibkr_evidence_json={
            "awaited_since": terminal_state_at.isoformat(),
            "elapsed_seconds": int(age.total_seconds()),
            "cutoff_seconds": int(TIMEOUT_CUTOFF.total_seconds()),
        },
        notes_dutch=(
            "Timeout van 24 uur overschreden zonder IBKR-data; "
            "doorgezet naar handmatige beoordeling."
        ),
    ))
```

### 5.3 Divergence types written

| Pass C divergence_type | Meaning |
|------------------------|---------|
| `timeout_flagged_manual_review` | Draft in `awaiting_reply_timeout` for ≥ 24h → escalated to `requires_manual_review` |

### 5.4 Interaction with Pass A

The Pass C docstring (`:18-20`) is explicit: "Pass C runs after Pass A. If Pass A produced an execution-driven heal on the same draft earlier in the tick, the draft is no longer in `awaiting_reply_timeout` and Pass C skips it automatically." This is a key invariant of the strict A → B → C ordering.

### 5.5 Result

`PassCTimeoutRecoveryResult`: `timeouts_evaluated, escalated_to_manual_review, skipped_within_cutoff, skipped_missing_terminal_at, divergences_found, escalated_draft_ids`.

## 6. The four audit tables

All four are created in migration `packages/storage/alembic/versions/0053_reconciliation_audit_and_manual_review.py` and modelled in `packages/storage/src/ai_trading_agent_storage/metadata.py`. Append-only by doctrine.

### 6.1 `reconciliation_run_audit` (one row per tick)

Created at migration `:228-277`. Table metadata at `metadata.py:3067`. Repository `SqlAlchemyReconciliationRunAuditRepository` at `sql_repositories.py:6425`.

- **Primary key**: `id` (auto-increment).
- **UNIQUE constraint**: `reconciliation_run_id`.
- **Idempotency**: per run-id (the `_default_run_id_factory` UUID prefix).
- **Mutability**: ONE column is mutable — `completed_at` flips from `NULL` to a timestamp via `complete_run` (`sql_repositories.py:6468`); the row is otherwise append-only. Mode flips from `"completed"` (tentative) to the final mode at the same call.
- **Columns**: `reconciliation_run_id, started_at, completed_at, account_id, pass_a_orphaned_count, pass_b_stale_count, pass_c_timeout_count, divergences_found, mode_detected, error_details_json`.

### 6.2 `reconciliation_audit` (one row per divergence)

Created at migration `:72-123`. Table metadata at `metadata.py:2924`. Repository `SqlAlchemyReconciliationAuditRepository` at `sql_repositories.py:6101`.

- **Primary key**: `id` (auto-increment).
- **No UNIQUE on a domain key** — idempotency is delegated to each pass's gating logic (Pass A: `executions_repo.get_by_exec_id` + `unmatched_repo.get_by_exec_id`; Pass B: `action_draft_repo.list_active_for_account` re-runs are safe because the transition is gated by current status; Pass C: re-runs see the draft already in `requires_manual_review` so `list_by_status("awaiting_reply_timeout")` returns empty).
- **CHECK constraint on `divergence_type`** (migration `:101-111`): one of `missing_execution_applied | status_corrected_to_filled | status_corrected_to_cancelled | status_corrected_to_rejected | status_corrected_to_partially_filled | timeout_recovered_to_terminal | timeout_flagged_manual_review | unmatched_execution | terminal_state_divergence_logged`. (Nine locked values. Note that the code currently writes 8 of them; `timeout_recovered_to_terminal` is in the constraint but unused.)
- **Columns**: `reconciliation_run_id, action_draft_id, event_at, pass_name, divergence_type, before_status, after_status, ibkr_evidence_json, notes_dutch`.

### 6.3 `unmatched_execution_audit` (one row per orphan)

Created at migration `:126-175`. Table metadata at `metadata.py:2972`. Repository `SqlAlchemyUnmatchedExecutionAuditRepository` at `sql_repositories.py:6239`.

- **Primary key**: `id` (auto-increment).
- **UNIQUE constraint**: `ibkr_exec_id`.
- **Idempotency**: per `ibkr_exec_id`. Pass A explicitly checks `unmatched_repo.get_by_exec_id` before writing (`pass_a_orphaned_executions.py:157`).
- **Columns**: `event_at, ibkr_perm_id, ibkr_exec_id, account_id, conid, side, fill_price_local, fill_quantity, fill_time, raw_execution_json, resolution_status`.
- **`resolution_status` lifecycle**: starts at `"unresolved"`; the acknowledgement API (§7.5) flips it to `"acknowledged"`.

### 6.4 `manual_review_queue` (one row per Pass C escalation)

Created at migration `:178-225`. Table metadata at `metadata.py:3023`. Repository `SqlAlchemyManualReviewQueueRepository` at `sql_repositories.py:6320`.

- **Primary key**: `id` (auto-increment).
- **Idempotency**: the storage repo's `append` is the only writer; Pass C is the only caller; Pass C's `list_by_status("awaiting_reply_timeout")` guarantees a draft can only be escalated once per terminal-state-at value.
- **Columns**: `flagged_at, action_draft_id, reason, details_dutch, resolution_status, acknowledged_at, acknowledgement_note`.
- **`resolution_status` lifecycle**: starts at `"pending"`; the API ack route (§7.4) flips it via `queue_repo.acknowledge`.

## 7. API surface — read + acknowledge

**Module**: `apps/api/src/portfolio_outlook_api/reconciliation.py` (505 lines). Seven routes total — six read + one acknowledge.

### 7.1 `GET /reconciliation/status` (`reconciliation.py:295`)

Returns the dashboard widget payload: `{ibkr_account_id, latest_run, drafts_healed_last_24h, pending_manual_review_count, unresolved_unmatched_count}`. Joins all four audit repos.

### 7.2 `GET /reconciliation/runs` (`reconciliation.py:350`)

Returns the recent tick history (`limit ≤ 200`, newest-first). Powers the admin "Reconciliation runs" screen.

### 7.3 `GET /reconciliation/audit` (`reconciliation.py:380`)

Returns recent `reconciliation_audit` rows (`limit ≤ 200`, newest-first). Per-divergence audit trail.

### 7.4 `GET /reconciliation/manual-review` (`reconciliation.py:410`)

Returns pending `manual_review_queue` rows for human triage. The dashboard "system-decision" surface reads from here.

### 7.5 `POST /reconciliation/manual-review/{queue_id}/acknowledge` (`reconciliation.py:437`)

The **only mutating route in the reconciliation surface**. Flips a pending queue row to `acknowledged`:

- 404 if `queue_id` not found (`:461-464`).
- Idempotent — re-acknowledging an already-acknowledged row returns the existing row unchanged (docstring `:447-448`).
- Optional `note` query param recorded on the row.
- **Does NOT touch the underlying Action Draft** (docstring `:449-452`) — the user reviewed the row and is closing the queue item; the draft stays in whatever terminal status the reconciler set.

### 7.6 `GET /reconciliation/unmatched-executions` (`reconciliation.py:476`)

Returns unresolved `unmatched_execution_audit` rows. The triage view for IBKR-side fills with no matching local draft.

### 7.7 Missing routes (intent vs reality)

- **No user-initiated reconciliation trigger route** — intent §6 requires a "user-initiated reconciliation trigger" but the API has no `POST /reconciliation/run` (or equivalent).
- **No threshold-editing routes** — intent §4 says "Thresholds **changes** are audit-logged with `{user, pass, field, from, to, changed_at}`" but no threshold-edit endpoint exists.

## 8. State-machine writes — who writes what

Pass A and Pass B both write `action_draft_repo.apply_lifecycle_transition`; Pass C writes the same on a different transition. The destination statuses, by pass:

| Pass | Source status | Destination status | Transition writer |
|------|---------------|---------------------|-------------------|
| A    | non-terminal in-flight | `filled` / `partially_filled` / `cancelled` / `rejected` | `_apply_missing_execution` (Pass A) |
| B    | `submitted` / `accepted` / `working` / `partially_filled` / `pending_cancellation` | `filled` / `partially_filled` / `cancelled` / `rejected` | inline at `pass_b_stale_in_flight.py:229` |
| C    | `awaiting_reply_timeout` | `requires_manual_review` | inline at `pass_c_timeout_recovery.py:114` |

All three reconciliation transitions are widening transitions on the storage state machine. They map to the `_ACTION_DRAFT_TRANSITIONS` map widened by "Task 135a" (cited at `pass_c_timeout_recovery.py:9-10`). The state-vocabulary unification gap surfaced in T-018 and T-019 is in play: the portfolio enum (`ActionDraftState`) does not contain `awaiting_reply_timeout` or `requires_manual_review` — these are storage-only states.

## 9. Failure modes and the `error` mode

### 9.1 `mode_detected="skipped_locked"`

Another tick of {sweep, reconciler, morning chain} holds the global advisory lock. Behaviour: row is written via `_run_audit_repo.append` with the open status, BUT the lock-acquire-failure path at `reconciler.py:185-192` returns BEFORE `_run_locked` is called — meaning the `_run_audit_repo.append` is NOT reached on this path. **Therefore, `skipped_locked` ticks do NOT produce a `reconciliation_run_audit` row.**

This is a subtle audit gap: the system cannot tell from the audit table whether a tick was skipped (the timeline simply shows no row for that scheduled tick).

### 9.2 `mode_detected="skipped_disconnected"`

IBKR gateway is not connected. The open audit row IS already in the table at this point (`reconciler.py:210-223`); `complete_run` flips it to `mode_detected="skipped_disconnected"` with all pass counts = 0. The full audit trail is preserved.

### 9.3 `mode_detected="error"` — the partial-completion path

If Pass A or Pass B raises through despite their internal `except Exception` boundaries, the orchestrator catches it (`reconciler.py:277`). The `error_details_json` records:

```json
{
  "class": "ExceptionClassName",
  "message": "Exception message text",
  "pass_a_completed": true,
  "pass_b_completed": false,
  "pass_c_completed": false
}
```

Already-completed pass results are still applied — `pass_a_orphaned_count` reflects whatever Pass A managed to write before the failure. Pass C is **not** invoked on this path. The lock is released by the `try/finally`.

### 9.4 Per-row failures inside a pass

Each pass catches per-row exceptions and counts the row as a divergence (logged via `logger.exception`). The pass continues processing the remaining rows. Pass A: `_apply_missing_execution` returns `False` on failure. Pass B: writes `terminal_divergence_transition_failed`. Pass C: logs and continues (no audit row written on per-row failure — see Phase 1c finding §10.5).

## 10. Phase 1c surface

10 findings to be carried forward to Phase 1c gap analysis (Track 1c):

1. **No APScheduler wiring** (§1.2) — `IbkrReconciler.tick()` is not invoked by `scheduler.py`. The class is unit-tested but never instantiated in production. **Five event triggers all missing** (15min market-hours, 1h off-hours, 07:00 morning-chain block, after-fill, after-reconnect, on-demand). Single largest reality gap in the audit so far. **Re-confirmed for T-020.**
2. **Same gap for `SubmissionSweep.tick()`** — T-019 §1.2 noted that the sweep is intended for APScheduler; T-020 cross-confirms that neither sibling tick is wired in. Both share this Phase 1c gap.
3. **4-tier B/C/D/E classification not in code** (§4.4) — intent doc §3 + §4 specify a 4-tier severity classification (`tier_b` low / `tier_c` medium / `tier_d` high / `tier_e` critical) with thresholds. **None of these tier strings appear in any reconciliation module.** Code uses flat divergence-type strings via the migration's CHECK constraint. The intent's threshold table is purely aspirational.
4. **No 07:00 morning-chain mandatory block** (§1.2) — intent §1 says "Mandatory; blocks the morning chain until complete." `pre_briefing` (06:00, T-011) and `morning_briefing` (07:00 — actually invoked from `_on_hourly` at hour 7) run independently of reconciliation status.
5. **No user-initiated reconciliation trigger** (§7.7) — intent §6 requires a "user-initiated reconciliation trigger" button + API route. Neither exists.
6. **No `skipped_locked` audit row** (§9.1) — the lock-fail-fast path returns before writing the `reconciliation_run_audit` row, so ticks that lose the lock are invisible to the audit table. Operators cannot reconstruct scheduling history from the audit.
7. **Legacy `reconciliation_sync.py` doctrine drift** — the API ships **two** reconciliation paths: the new Task 135b 3-pass system (`reconciliation.py` + worker `IbkrReconciler`) and a legacy SUBMITTED→FILLED→RECONCILED orchestrator (`reconciliation_sync.py:1-13`) using the older portfolio state-machine vocabulary. The legacy module is unused by the new 3-pass flow but still importable. Two-vocabulary state-machine island re-confirmed for 6th time.
8. **Pass B has no time-based thresholds** (§4.4) — Pass B writes the same `status_corrected_*` divergence_type regardless of how long a draft was stale. Intent's "< 5min → tier_c, 5–30min → tier_d, > 30min → tier_e" classification is not implemented.
9. **Pass C 24h cut-off is hard-coded, not configurable** (§5.1) — `TIMEOUT_CUTOFF = timedelta(hours=24)` at module level. Intent doc §4 references "configurable in Category 3 of `docs/intent/settings-and-credentials.md`" but the settings surface has no field for this.
10. **Pass C per-row failure writes no audit row** (§9.4) — when `apply_lifecycle_transition` fails inside Pass C, the exception is logged but no `reconciliation_audit` row is written. Compare Pass B which writes `terminal_divergence_transition_failed` on the equivalent failure. Inconsistent audit discipline across passes.

## 11. Out of scope (re-confirmed)

- **Submission lifecycle (T-019)** — the sibling tick that creates the in-flight state Pass B watches.
- **Action-draft composition + approval (T-018)** — produces drafts before they enter the reconciliation envelope.
- **AI explanation (T-023 future)**.
- **Portfolio valuation drift (T-021 future)** — corporate-action handling is intent-classified as D-class but the tier classification is absent.
- **`reconciliation_sync.py` deep dive** — referenced only as doctrine drift; documenting the legacy orchestrator end-to-end belongs to a future Phase 1c cleanup task.

## 12. References

- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py:1-378`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_a_orphaned_executions.py:1-418`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_b_stale_in_flight.py:1-443`
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/pass_c_timeout_recovery.py:1-179`
- `apps/worker/src/portfolio_outlook_worker/single_flight_lock.py:30-73`
- `apps/worker/src/portfolio_outlook_worker/scheduler.py:130-175`
- `apps/api/src/portfolio_outlook_api/reconciliation.py:1-505`
- `apps/api/src/portfolio_outlook_api/reconciliation_sync.py:1-13` (legacy, doctrine drift)
- `packages/storage/alembic/versions/0053_reconciliation_audit_and_manual_review.py:1-280`
- `packages/storage/src/ai_trading_agent_storage/metadata.py:2924-3110`
- `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:6101-6500`
- `packages/portfolio/src/portfolio_outlook_portfolio/broker_reconciliation_guards.py:1-28`
- `packages/domain/src/portfolio_outlook_domain/broker_reconciliation.py:1-419`
- `docs/intent/reconciliation.md` (locked 2026-05-26)
- `docs/decisions/0010-reconciliation-architecture.md`
- `docs/reality/components/worker-actions-and-reconciliation.md` §§8-12 (T-007)
- `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (T-019 sibling)
