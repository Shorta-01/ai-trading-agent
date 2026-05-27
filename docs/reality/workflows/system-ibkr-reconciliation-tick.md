# System IBKR Reconciliation Tick — Same Wiring Gap, Different Tick

**Scope.** System-tick workflow narrating the intended reconciliation tick — `IbkrReconciler.tick()` would be invoked by APScheduler per intent §1's hybrid cadence (15min during market hours + 1h off-hours + 5 event triggers), acquire the single-flight lock, run the strict Pass A → B → C ordering, and write a `reconciliation_run_audit` row. **Same wiring gap as T-034**: the tick is not invoked in production. The 3-pass back-stop architecture (T-020 §3-§5) exists end-to-end but is never invoked outside tests. Closes Track 1a Reality Workflows (T-025…T-035).

**Sibling functionality reality**: T-020 `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (full coverage of the 3 passes + 4 audit tables + intent vs reality). **Parallel system-tick sibling**: T-034 `docs/reality/workflows/system-ibkr-submission-sweep.md` (the submission sweep with the identical wiring gap).

## 0. TL;DR — what the system SHOULD do vs what it ACTUALLY does

| Step | Intended (per intent + docstring) | Reality |
|------|-----------------------------------|---------|
| APScheduler fires `IbkrReconciler.tick` per 15min/1h cadence | Wires the tick into a cron / interval job | **Not wired.** Worker `scheduler.py:130-175` registers 3 jobs; none touch `IbkrReconciler`. |
| `tick()` enters single-flight lock | Lock attempt (T-020 §2.3); failure → `mode="skipped_locked"` | Code path exists; never invoked. |
| Connectivity gate (`is_connected()`) | Per T-020 §2.4 — short-circuit if IBKR gateway unreachable | Code path exists; never invoked. |
| Open `reconciliation_run_audit` row | Insert with `completed_at=NULL` (T-020 §2.4 step 1) | Code path exists; never invoked. |
| Run Pass A (orphaned executions) | Detect IBKR fills the worker missed (T-020 §3) | Code path exists; never invoked. |
| Run Pass B (stale in-flight) | Detect drafts the worker thinks are in-flight that IBKR doesn't (T-020 §4) | Code path exists; never invoked. |
| Run Pass C (24h timeout escalation) | Escalate stale `awaiting_reply_timeout` drafts to `requires_manual_review` (T-020 §5) | Code path exists; never invoked. |
| `complete_run` audit-row finalisation | Flip `completed_at` + per-pass counts + final mode | Code path exists; never invoked. |
| 5 intent-§1 event triggers (07:00 block, after-fill, after-reconnect, on-demand, periodic) | All 5 should invoke the tick | All 5 are missing — no event surface, no on-demand route. |

**Net result in production**: divergences between local state and IBKR truth accumulate undetected. T-027 §5 already documented one operational consequence: `pending_cancellation` drafts that need the reconciler's Pass B to ever reach `cancelled` stay stuck forever because Pass B never runs.

## 1. The intended trigger — `IbkrReconciler.tick()`

**File**: `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py:139-202`.

The class declaration at `:139-146`:

```python
class IbkrReconciler:
    """One reconciler tick — Pass A → Pass B → Pass C with audit + lock.

    Wired into APScheduler as a no-arg ``tick()`` invocation. The
    orchestrator handles single-flight via the injected ``lock``
    protocol; failing to acquire returns
    ``IbkrReconcilerResult(mode_detected="skipped_locked")``.
    """
```

Same aspirational docstring claim as `SubmissionSweep` (T-034 §1). T-020 §10.4 originally documented this; T-035 re-surfaces from the tick-perspective angle.

The public entry at `:181-202`:

```python
def tick(self) -> IbkrReconcilerResult:
    started = self._now_provider()
    run_id = self._run_id_factory()

    if not self._lock.try_acquire():
        return _empty_run_result(
            run_id=run_id,
            account_id=self._ibkr_account_id,
            started_at=started,
            completed_at=self._now_provider(),
            mode="skipped_locked",
        )

    try:
        return self._run_locked(run_id=run_id, started=started)
    finally:
        try:
            self._lock.release()
        except Exception:  # noqa: BLE001 — boundary
            logger.exception("reconciler lock release failed")
```

Identical lock discipline to `SubmissionSweep.tick()` (T-034 §1).

## 2. The wiring gap — grep proof

`grep -rn "IbkrReconciler\b" apps/worker/src/portfolio_outlook_worker/ | grep -v test_ | grep -v ibkr_reconciliation/`:

```
(zero matches)
```

`IbkrReconciler` is referenced ONLY inside its own subpackage (`ibkr_reconciliation/__init__.py` re-exports it at `:41` per T-020 §1.2). **Nothing outside the subpackage instantiates or invokes it.**

The worker scheduler at `scheduler.py:130-175` registers:
1. `_on_pre_briefing` (06:00).
2. `_on_hourly` (7-21).
3. `_heartbeat` (interval).

None of these handlers touch `IbkrReconciler`. The wiring gap is identical to `SubmissionSweep` (T-034 §2).

**§9.1 — the dominant finding of T-035** re-confirms T-020 §10.1 from a new angle: the system has the entire 3-pass back-stop infrastructure (~1300 LOC across 4 modules + 4 audit tables + 7 API routes), but it never runs.

## 3. The 4-mode `ReconcilerMode` Literal

`reconciler.py:62-67`:

```python
ReconcilerMode = Literal[
    "completed",
    "skipped_locked",
    "skipped_disconnected",
    "error",
]
```

The 4 modes (one fewer than `SubmissionSweep.SweepMode` because the reconciler has no `skipped_market_closed` equivalent — reconciliation runs regardless of market hours per intent §1: "Every hour outside market hours" — even at 03:00 the system should still reconcile positions). Per T-020 §2.4-§2.5, the modes map to:

| Mode | When written | What's preserved |
|------|--------------|-------------------|
| `completed` | All 3 passes finished, no fatal exceptions | Full payload + per-pass counts |
| `skipped_locked` | Lock contention | **NO audit row written** (T-020 §10.1 audit gap) |
| `skipped_disconnected` | IBKR gateway not reachable | Open audit row already exists; `complete_run` flips it to `skipped_disconnected` |
| `error` | A pass raised through despite internal `except Exception` | Open audit row → `complete_run` with `error_details_json` + partial pass counts |

## 4. The strict Pass A → B → C ordering — what would run if wired

Per T-020 §2.4 + §3-§5, after acquiring the lock + opening the audit row + the connectivity gate, the orchestrator runs three passes in strict order:

| Pass | Entry | What it does (in 1 line) |
|------|-------|---------------------------|
| **Pass A** | `pass_a_orphaned_executions.py:125` `run_pass_a_orphaned_executions(...)` | Detect IBKR fills the worker missed; insert into `ibkr_executions` + heal draft status, OR record as `unmatched_execution` if no draft. |
| **Pass B** | `pass_b_stale_in_flight.py:129` `run_pass_b_stale_in_flight(...)` | Detect drafts in `{submitted, accepted, working, partially_filled, pending_cancellation}` that IBKR reports as terminal; apply lifecycle transition. |
| **Pass C** | `pass_c_timeout_recovery.py:73` `run_pass_c_timeout_recovery(...)` | Escalate drafts in `awaiting_reply_timeout` for ≥24h to `requires_manual_review`. |

The strict ordering is documented in T-020 §2.4. **Pass C runs after Pass A** (Pass A may heal a draft out of `awaiting_reply_timeout` before Pass C escalates it — see T-020 §5.4).

§9.2 — the **per-pass dependency on the prior pass** means a partial completion (Pass A succeeds but Pass B raises) leaves the system in a half-reconciled state. The orchestrator's outer try-except at `reconciler.py:248-319` catches and records, but the system's local state is still inconsistent until the NEXT tick runs all 3 passes again. Since no next tick fires, half-reconciled states persist.

## 5. The 5 missing event triggers (per intent §1)

`docs/intent/reconciliation.md` §1 specifies the hybrid cadence:

### 5.1 Periodic baseline (both missing)

- **Every 15 minutes during market hours** — not wired.
- **Every hour outside market hours** — not wired.

§9.3 — these two cadences would require either a cron expression like `*/15 9-22 * * 1-5` for market hours + `0 0-9,23 * * *` for off-hours, OR an interval-based scheduler with a market-hours predicate. Neither exists.

### 5.2 Five event triggers (all missing)

Per intent §1:

| # | Trigger | Status |
|---|---------|--------|
| 1 | **07:00 before the morning chain** — mandatory; blocks the morning chain until complete. | T-031 §2 documented: the morning chain runs WITHOUT a reconciliation prerequisite. The intent §1 mandate is unimplemented. |
| 2 | **After every order fill** — re-verify post-fill state | T-019 §6 documented the IBKR callback fan-out for fills. The lifecycle handler writes to `ibkr_executions` + flips draft status. **No code path invokes `IbkrReconciler.tick()` after a fill.** |
| 3 | **After IBKR session reconnect** — anything could have changed during disconnect | No reconnect event surface; the system has no event bus for IBKR-side state-change signals. |
| 4 | **On user demand** — button in settings | No `POST /reconciliation/run` API route exists (T-020 §7.7 already flagged this). |
| 5 | Implicit: **post-cancel** — T-027 §5 documented `pending_cancellation` drafts depend on Pass B to ever reach `cancelled` | Not wired. T-027's "stuck cancel" finding is a direct downstream consequence. |

**Score: 0 of 5 event triggers implemented.** Combined with the 0-of-2 periodic baselines, **0 of 7 intent-§1 trigger paths exist in production**.

## 6. User-visible consequences

The reconciler is the back-stop that detects + heals divergences. With it not wired, the following remain undetected:

1. **`pending_cancellation` drafts stuck forever** — T-027 §5 documented this. The user clicks Annuleer; the API writes `pending_cancellation`; the worker should pick it up (no worker cancel loop per T-019 §4.8); even if it did, Pass B should catch the broker-side termination — but Pass B never runs. The draft stays in `pending_cancellation` indefinitely.
2. **IBKR-side fills that bypass the worker callback path** — possible (per T-019 §4) when connection drops during `place_order`. Pass A is the documented recovery; Pass A never runs.
3. **`awaiting_reply_timeout` drafts** — per T-020 §5, these drafts wait for the IBKR side to confirm an action. After 24h, Pass C would escalate to `requires_manual_review`. Pass C never runs. The drafts stay in `awaiting_reply_timeout` indefinitely; the user has no escalation surface; T-028's "Bevestig" surface has no rows to show because Pass C never produces them.
4. **Cash balance drift** — if dividends pay or fees post out-of-band, local cash diverges from IBKR truth. The intent doc §3 classifies this as tier B/C/D/E drift. None of the tiers are implemented (T-020 §10.3); even the detection layer is absent because the reconciler isn't running.
5. **No 07:00 morning-chain block** — intent §1 trigger #1 mandates a mandatory pre-chain block. T-032 documented the morning chain runs unconditionally; staleness propagates.

§9.4 — the user has **no visible signal** that reconciliation hasn't run. The `<ReconciliationStatusWidget>` on the dashboard (T-008 + T-028 entry point) would show `latest_run = None` if no row exists in `reconciliation_run_audit`. The widget treats this as "no runs yet" which on day 1 is correct but **on day 100 means the system has been silently divergent for 99 days**.

## 7. The audit gap consolidation

T-020 §10 documented 10 reconciliation-specific findings; T-035 doesn't duplicate them. The system-tick-specific findings are narrower:

1. **No APScheduler wiring** (§2) — `IbkrReconciler` never instantiated outside tests.
2. **No 5-event-trigger wiring** (§5.2) — 07:00 block, after-fill, after-reconnect, on-demand, post-cancel all missing.
3. **No periodic cadence** (§5.1) — neither 15min market-hours nor 1h off-hours cron exists.
4. **`skipped_locked` produces no audit row** (T-020 §10.1 carry-over) — even when the tick fires (in tests), lock-contention ticks leave no trace.
5. **Half-reconciled state persistence** (§4 §9.2) — partial completion is harmless WITHIN a tick (the orchestrator records + recovers), but the next tick never fires, so the half-state stays.
6. **`<ReconciliationStatusWidget>` `latest_run=None` ambiguity** (§6 §9.4) — day-1 normal state vs day-100 broken-system state look identical.
7. **Two back-stop ticks compound their wiring gaps** — T-034 (submission sweep) + T-035 (reconciliation) BOTH not wired. The submission gap means user-approved drafts pile up; the reconciliation gap means even if they were somehow submitted, divergences would never be detected.

## 8. Phase 1c surface (10 findings)

1. **No APScheduler wiring — DOMINANT FINDING (parallel to T-034)** — `IbkrReconciler` referenced only by its own subpackage + tests. Combined with T-034: **both back-stop infrastructure ticks are missing scheduling**.
2. **0 of 7 intent-§1 trigger paths implemented** — neither periodic baseline cadence nor any of the 5 event triggers exist.
3. **07:00 morning-chain block is unimplemented** — intent §1 trigger #1 mandates a hard prerequisite; T-032 §3 documents the morning chain runs without it.
4. **No event surface for "after fill" or "after reconnect"** — the system has no event bus; intent §1 triggers #2 + #3 would require building one.
5. **No `POST /reconciliation/run` API route** — T-020 §7.7 originating finding; intent §1 trigger #4 absent.
6. **`pending_cancellation` drafts permanently stuck** — T-027 §5 documented; T-035 re-confirms from the reconciler tick angle.
7. **Day-1 / day-100 indistinguishable** — `<ReconciliationStatusWidget>` `latest_run=None` ambiguity; no telemetry for "should have run by now but hasn't".
8. **Half-reconciled state persists between ticks** — but since ticks don't fire, the "between" is forever.
9. **Two compounding wiring gaps** (T-034 + T-035) — the submission infrastructure can't deliver; the back-stop infrastructure can't recover.
10. **All 10 of T-020's reconciliation-specific findings remain** — T-035 doesn't add or remove from that list; the wiring gap subsumes them.

## 9. Out of scope (re-confirmed)

- **Pass internals** (T-020 — merged sibling).
- **Submission sweep tick** (T-034 — merged sibling; parallel pattern).
- **API reconciliation routes** (T-020 §7 — already documented).
- **4-tier B/C/D/E classification** (T-020 §10.3 — already flagged absent).
- **Worker-side cancel adapter** (T-019 §4.8 — separate gap; cross-referenced via T-027 §5).

## 10. References

- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py:62` (`ReconcilerMode`)
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py:139-146` (class + aspirational docstring)
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/reconciler.py:181-202` (`tick()` entry)
- `apps/worker/src/portfolio_outlook_worker/ibkr_reconciliation/__init__.py:41` (re-export — the only other reference)
- `apps/worker/src/portfolio_outlook_worker/scheduler.py:130-175` (worker scheduler — does NOT register reconciler)
- `docs/intent/reconciliation.md` §1 (hybrid cadence + 5 event triggers)
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (T-020 — full functionality reality doc)
- `docs/reality/workflows/system-ibkr-submission-sweep.md` (T-034 — parallel system-tick sibling)
- `docs/reality/workflows/user-cancel-submitted-order.md` (T-027 — §5 stuck-cancel consequence of this wiring gap)
- `docs/reality/workflows/user-acknowledge-manual-review.md` (T-028 — `manual_review_queue` rows that Pass C should populate)
- `docs/reality/workflows/system-morning-briefing-07-00.md` (T-032 — morning chain that intent §1 says should be blocked on reconciliation)
- `docs/reality/components/web-components-status-and-shared.md` (T-008 — `<ReconciliationStatusWidget>`)

## 11. Closes Track 1a Reality Workflows

T-035 closes the 11-doc Track 1a Reality Workflows sub-track (T-025…T-035):

| Sub-track | Tasks | Status |
|-----------|-------|--------|
| User actions | T-025 (BEVESTIG), T-026 (JA), T-027 (Annuleer), T-028 (Bevestig manual review), T-029 (Cashbuffer), T-030 (DP detail) | 6/6 merged |
| System ticks | T-031 (06:00 pre_briefing), T-032 (07:00 morning_briefing), T-033 (08:00-21:00 hourly_delta), T-034 (submission sweep), T-035 (reconciliation tick) | 5/5 (T-035 in PR) |

With Track 1a complete, the audit moves to Track 1b architecture review (T-036…T-043) + Track 1c gap analysis (T-044…T-049) + the carry-forward functional-review additions (T-011b, T-011c, T-012b, T-016b, T-021b).
