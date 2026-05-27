# System IBKR Submission Sweep — Wired In Docstring, Not in Production

**Scope.** System-tick workflow narrating the intended submission sweep — `SubmissionSweep.tick()` would be invoked by APScheduler, pull the FIFO-ordered `user_approved` action drafts, re-evaluate the 12 Tier-1 safety gates per draft, and submit at most one per tick via `place_order(contract, order)`. The class is fully implemented (~470 LOC, T-019 covers it end-to-end) and has a public `tick()` method whose docstring claims it's "Wired into APScheduler as a no-arg `tick()` invocation". **But it is not actually wired.** The worker scheduler registers 3 jobs (pre_briefing + hourly + heartbeat); none of them invoke `SubmissionSweep.tick`. User-approved drafts pile up indefinitely.

**Sibling functionality reality**: T-019 `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (end-to-end submission internals — 12 Tier-1 gates, Tier-2 account-ID re-read, single `place_order` call, IBKR callback fan-out, 3 audit tables). **System-tick siblings**: T-031 + T-032 + T-033 (the morning-chain ticks that share the same single-flight lock).

## 0. TL;DR — what the system SHOULD do vs what it ACTUALLY does

| Step | Intended (per `tick()` docstring) | Reality |
|------|-----------------------------------|---------|
| APScheduler fires `SubmissionSweep.tick` | Wires the sweep into a cron / interval job | **Not wired.** Worker `scheduler.py:141-165` registers 3 jobs (pre_briefing, hourly, heartbeat); none of them touch `SubmissionSweep`. |
| `tick()` enters single-flight lock | Lock attempt; failure → `mode="skipped_locked"` | The code path exists but is never invoked. |
| Market-hours gate | `BrusselsBusinessHoursMarket.is_open(...)` (T-019 §1.2) | Code path exists; never invoked. |
| Queue poll | FIFO list `user_approved` drafts | Code path exists; never invoked. |
| 12-gate per-draft evaluation | (T-019 §3 — 12 Tier-1 gates) | Code path exists; never invoked. |
| Tier-2 account-ID re-read | (T-019 §4) | Code path exists; never invoked. |
| `place_order` for first eligible draft | (T-019 §4 — single authority) | Code path exists; never invoked. |
| One-per-tick `break` | (T-019 §4.1 — at `submission_sweep.py:337`) | Code path exists; never invoked. |

**Net result in production**: a user approves a draft (T-026 JA ritual) → status flips to `user_approved` → the draft sits in storage. The dashboard shows "Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd." (per T-026 §6 — out-of-date banner). The banner text turns out to be **accidentally truthful**: the submission infrastructure exists but is not invoked. The order never reaches IBKR.

## 1. The intended trigger — `SubmissionSweep.tick()`

**File**: `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:178-339`.

The class declaration at `:178-184`:

```python
class SubmissionSweep:
    """One sweep tick — pull → gate → (optionally) submit.

    Wired into APScheduler as a no-arg ``tick()`` invocation. The
    sweep handles single-flight via the injected ``lock`` protocol;
    failing to acquire returns ``SubmissionSweepResult(mode="skipped_locked")``.
    """
```

The docstring asserts "Wired into APScheduler". **This is aspirational, not descriptive** — same pattern T-020 §10.4 documented for `IbkrReconciler` and T-027 §5.1 documented for the cancel route.

The public entry at `:217`:

```python
def tick(self) -> SubmissionSweepResult:
    started = self._now_provider()
    if not self._lock.try_acquire():
        return SubmissionSweepResult(
            mode="skipped_locked",
            ...
        )
    try:
        return self._run_locked(started=started)
    finally:
        try:
            self._lock.release()
        except Exception:  # noqa: BLE001
            logger.exception("submission sweep lock release failed")
```

Same `try/finally` lock discipline as the reconciler (T-020 §2.4). Sound implementation; just no caller.

## 2. The wiring gap — grep proof

`grep -rn "SubmissionSweep\b" apps/worker/src/portfolio_outlook_worker/ | grep -v test_`:

```
apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:178: class SubmissionSweep:
apps/worker/src/portfolio_outlook_worker/ibkr_submission/__init__.py:44:     SubmissionSweep,
apps/worker/src/portfolio_outlook_worker/ibkr_submission/__init__.py:78:     "SubmissionSweep",
```

**Outside the module + its `__init__.py` re-export, `SubmissionSweep` does not appear anywhere in production worker code.** No factory builds it, no scheduler registers it, no entrypoint invokes it.

The worker scheduler at `apps/worker/src/portfolio_outlook_worker/scheduler.py:130-175` registers:
1. `_on_pre_briefing` (cron 06:00 — T-031).
2. `_on_hourly` (cron 7-21 → relabel to morning_briefing or hourly_delta — T-032 + T-033).
3. `_heartbeat` (interval).

None of these handlers instantiate or invoke `SubmissionSweep`. The wiring gap is identical in shape to the reconciler tick (T-020 §10.1) and the API-side scheduler (T-032 §5 — that scheduler runs its own morning chain but doesn't touch submission).

§9.1 — the dominant finding of T-034 — re-confirms T-020 §10.2 ("Same gap for `SubmissionSweep.tick()`").

## 3. The 5-stage tick body (per `submission_sweep.py:217-339`) — what would run if wired

Per T-019 §2-§4, the `tick()` body has 5 distinct stages. Documented here as a system-tick spec (not exhaustive — T-019 covers internals).

### 3.1 Stage 1 — Lock acquisition (`:219`)

```python
if not self._lock.try_acquire():
    return SubmissionSweepResult(mode="skipped_locked", ...)
```

Shared `ORCHESTRATOR_LOCK_KEY` advisory lock (T-019 §2.3) — same lock used by the morning chain (T-031 §2.3 + T-032) and the reconciler (T-020 §2.3).

**Lock contention model**: at a hypothetical APScheduler interval of every 60 seconds, the sweep would attempt to acquire the lock 60 times per hour. At 07:00 the morning chain holds the lock for the duration of the full 5-step morning_briefing fire. Sweep ticks during this window would all `skipped_locked` (per T-020 §10.1, with no audit row). The user-visible delay would be the morning_briefing duration. §9.4.

### 3.2 Stage 2 — Market-hours gate (`:241-248`)

```python
if not self._market_hours.is_open(exchange="UNKNOWN", now=started):
    return SubmissionSweepResult(mode="skipped_market_closed", ...)
```

`BrusselsBusinessHoursMarket` per T-019 §1.2 (coarse Mon-Fri 09:00-22:30 UTC; "Holiday awareness is deliberately out of scope for V1" per the docstring at `:151-152`).

**Holiday gap**: on Belgian banking holidays during weekdays (e.g., Easter Monday, May 1), the gate would return `is_open=True` despite markets being closed. If the sweep WERE wired, it would attempt submissions and fail at the IBKR side. §9.5.

### 3.3 Stage 3 — Queue poll (`:250-263`)

```python
drafts = self._action_draft_repo.list_user_approved_for_sweep(
    ibkr_account_id=...
)
```

FIFO order by `user_approved_at` (per T-019 §4 docstring at `:4-9`). Reads from `asset_action_drafts` WHERE `status="user_approved"`. Empty → `mode="no_drafts"`.

**Account scope**: filtered by `ibkr_account_id`. The sweep is per-account; with a single configured account (T-019 §1), the filter is effectively identity.

§9.6 — the FIFO ordering ensures earlier-approved drafts go first, which matches the user's mental model. But if the user approves 3 drafts at once (e.g., bulk-clicks the approve buttons), they all share the same `user_approved_at` (server clock granularity), and the FIFO order becomes undefined. T-019 didn't document a tiebreaker.

### 3.4 Stage 4 — Per-draft 12-gate evaluation (`:284-291, :367-405`)

The locked 12 Tier-1 gates per T-019 §3.2 (with the `SubmissionBlockReason` enum at `safety_recheck.py:37-51`). For each draft in FIFO order, run all 12 gates. Any failure → record `submission_block_reason`, continue to next draft.

The intent is **"re-check at submit time"** — the same gates that gated approval (T-018 §3) re-run because conditions may have changed (cash drawn down, market regime shift, position size diluted, etc.).

### 3.5 Stage 5 — Submit-or-break (`:284-340`)

For the first draft whose 12 gates ALL pass:
- Tier-2 account-ID re-read (T-019 §4: confirms the configured account ID matches the runtime IBKR session identity).
- `place_order(contract, order)` (T-019 §4, the single submission authority).
- Update draft status to `submitted` + write `ibkr_submission_audit` row.
- **`break` out of the loop** at `submission_sweep.py:337`.

The locked one-per-tick discipline (T-019 §4.1): **at most one `place_order` per tick.** Even if 10 drafts are eligible, only the first FIFO-eligible one gets submitted. The next tick re-evaluates.

**Why one-per-tick**: bounds the per-tick exposure (one mis-classified gate failure can only let one bad order through), allows lock release between submissions (so reconciler + morning chain can interleave), and produces predictable audit timing.

## 4. The `SubmissionSweepResult` audit row

`SubmissionSweepResult` (`submission_sweep.py:79-89`) carries the per-tick outcome. The `mode` Literal (`:57-63`):

```python
SweepMode = Literal[
    "completed",                # one draft submitted or all drafts blocked
    "skipped_locked",            # lock contention
    "skipped_market_closed",     # outside Brussels business hours
    "no_drafts",                 # queue empty
    "error",                     # exception caught
]
```

The 5 modes mirror the 4-mode `ReconcilerMode` of T-020 §2.1 with the addition of `skipped_market_closed`. The sweep + reconciler outcome surfaces are intentionally similar — they're peer ticks under the same lock.

§9.7 — same gap as T-020 §10.1: `skipped_locked` returns BEFORE the audit row is written (`submission_sweep.py:220-223`). Lock-failed sweep ticks leave no observable trace.

## 5. The user-visible consequence — drafts pile up

This is the operational meaning of the wiring gap for the user.

The user's flow (per T-026):
1. Open `/ibkr-acties` "Te keuren" tab.
2. Review a draft proposed by the worker (or composed via "Maak actie" on a DP).
3. Click "Goedkeuren".
4. Type `JA` in `window.prompt`.
5. See "Goedgekeurd" green badge + blue info banner: "Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd."

T-026 §6 documented this banner text as out-of-date because the submission infrastructure exists. **T-034 corrects this**: the banner text is **accidentally truthful** because the submission infrastructure is NOT invoked in production. The user is told "in een toekomstige update toegevoegd"; the system is silently delivering on that promise by doing nothing.

§9.2 — net user experience without the wiring:
- Approved drafts accumulate in `status="user_approved"`.
- No row ever migrates to the "Actief bij IBKR" tab (T-019 + T-026 §1).
- The user might wonder why their orders never fill; checking IBKR's interface would show zero recent orders.
- Calling the broker directly would reveal: the IBKR side has no record of any orders from the system.

§9.3 — there is NO scheduled job that picks up `user_approved` drafts and submits them. The only paths that could fire the sweep are:
- A future APScheduler wiring.
- A manual one-time CLI invocation.
- A test fixture calling `tick()` directly.

In current production, paths 1 + 2 do not exist; path 3 fires only during tests.

## 6. The intended cadence (per T-019 §1.2 inference)

T-019 §1.2 mentioned the sweep is "wired in via the same docstring claim as the reconciler — `# noqa: ARG002 — pending account-aware watchlist` style — but no actual APScheduler registration found". The intended cadence is unstated in code or intent docs. Likely candidates:
- **Every minute** (interval job) — high responsiveness; high lock contention with other ticks.
- **Every 5 minutes** (interval job) — moderate responsiveness; rarely contends with morning chain (which runs at :00 fires).
- **On user-approve event** (event-driven, not cron) — best UX but adds event-bus complexity.

§9.8 — Phase 1c needs to decide both **when** the sweep fires and **how** (cron vs interval vs event). Until then, the gap stays.

## 7. Failure paths (when/if wired)

1. **Lock contention with morning_briefing at 07:00** — `skipped_locked` for ~30-60 seconds while morning chain runs. Audit gap per §4. The user-approved draft from 06:59 would wait for the next sweep tick after 07:00.
2. **Lock contention with reconciler tick (T-020 / T-035)** — same shared lock. If both are ever wired with overlapping schedules, contention will be frequent.
3. **Market-closed at sweep time** — `skipped_market_closed`. The user-approved draft from 21:30 would wait for 09:00 tomorrow.
4. **Holiday during a weekday** (Belgian banking holiday) — `is_open=True` per the coarse market-hours check; the sweep would proceed to attempt submission. IBKR-side failure. §9.5.
5. **12-gate failure** — `submission_block_reason` recorded on the draft; sweep continues to next draft. The user sees the block reason in the UI (per T-019 §3).
6. **Tier-2 account-ID mismatch** (Tier-2 re-read returns a different account than expected) — submission aborted; locked safety property of T-019 §4.
7. **`place_order` raises** — exception caught at the tick level; `mode="error"` + the draft is left in `user_approved` for the next tick.
8. **Connection-lost during `place_order`** — T-019 §4 ghost-order risk; Pass A reconciliation (T-020 §3) is the recovery path. **But Pass A is also not wired** (T-020 §10.1), so the recovery is also missing. §9.9.

## 8. Phase 1c surface (10 findings)

1. **No APScheduler wiring — DOMINANT FINDING** (§2) — `SubmissionSweep` is referenced only in its own module + tests. The worker scheduler registers no job that invokes `tick()`. **User-approved drafts never reach IBKR.** T-020 §10.1 / §10.2 originating finding re-surfaced.
2. **The "Goedgekeurd. IBKR-verzending wordt in een toekomstige update toegevoegd." banner is accidentally truthful** (§5) — T-026 §10.5 flagged it as out-of-date; T-034 corrects: the infrastructure exists but is uninvoked. The text describes the runtime reality.
3. **Docstring claim "Wired into APScheduler" is aspirational** (§1) — same as T-019 §4.8 ("submitter.py:89 documents it's wired") + T-020 §10.4 (reconciler docstring). Multiple modules' docstrings describe a wiring layer that doesn't exist.
4. **Connection-lost ghost-order recovery also gapped** (§7.8) — T-019 §4 documented the risk; Pass A reconciliation is the documented recovery path; but Pass A is itself not wired (T-020 §10.1). Two missing wirings compound.
5. **No defined intended cadence** (§6) — neither code nor intent doc states "every N minutes" or "on approve event". Phase 1c needs a cadence decision before wiring.
6. **`skipped_locked` produces no audit row** (T-020 §10.1 / T-031 §9.2 / T-032 §9.10 / T-033 §9.8 carry-over) — sweep ticks that lose lock contention leave no observable trace.
7. **Holiday gap in market-hours check** — coarse Mon-Fri 09:00-22:30 UTC fails to skip Belgian banking holidays. (T-019 §1.2 originating finding; re-confirmed.)
8. **FIFO tiebreaker undefined for same-`user_approved_at`** (§3.3) — bulk-approve of 3 drafts produces undefined ordering.
9. **One-per-tick discipline is the right primitive but assumes a cadence** — without a tick schedule, the discipline is meaningless. With a 5-minute cadence and a queue of 10 approved drafts, full drainage takes ~50 minutes.
10. **`SubmissionSweepResult` audit table has no global "queue depth" view** — operators must aggregate by counting `status="user_approved"` rows. No materialized view, no metrics endpoint.

## 9. Out of scope (re-confirmed)

- **Submission lifecycle internals** (T-019 — merged sibling).
- **Reconciliation tick** (T-035 — future sibling; same wiring gap pattern).
- **Action draft approval** (T-026 — merged user-action sibling).
- **Worker-side cancel adapter** (T-019 §4.8 — separate gap, parallel to submission wiring gap).
- **Lock-sharing contention model** (T-031 §2.3 + T-032 §6 — already documented).

## 10. References

- `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:178-339` (the class)
- `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:179-184` (aspirational docstring)
- `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:57-63` (`SweepMode` Literal)
- `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py:337` (the one-per-tick `break`)
- `apps/worker/src/portfolio_outlook_worker/ibkr_submission/__init__.py:44, :78` (re-export — the only other reference)
- `apps/worker/src/portfolio_outlook_worker/scheduler.py:130-175` (worker scheduler — does NOT register submission sweep)
- `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (T-019 — submission internals)
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (T-020 — §10.1 originating finding for both sweep + reconciler wiring gap; Pass A as ghost-order recovery)
- `docs/reality/workflows/user-approve-action-draft.md` (T-026 — §6 banner "accidentally truthful")
- `docs/reality/workflows/system-morning-pre-briefing-06-00.md` (T-031 — lock-sharing)
- `docs/reality/workflows/system-morning-briefing-07-00.md` (T-032 — lock-sharing + dual-scheduler drift)
- `docs/reality/workflows/system-hourly-delta-runs.md` (T-033 — empty-fire sibling pattern)
