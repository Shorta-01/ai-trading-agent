# System Hourly Delta Runs — 08:00 through 21:00

**Scope.** System-tick workflow narrating the 14 `hourly_delta` fires that run every hour from 08:00 to 21:00 Brussels time. The dominant finding: **the name "hourly delta" suggests intra-day data refresh + delta computation; reality is 14 essentially-empty fires per day** that only acquire the single-flight lock, run connectivity + mode detection, handle cold-start if needed, and write an empty-payload audit row. **All 4 substantive sub-step gates in the orchestrator explicitly exclude `run_type="hourly_delta"`**.

**Sibling system-tick workflows**: T-031 `docs/reality/workflows/system-morning-pre-briefing-06-00.md` (06:00 sibling), T-032 `docs/reality/workflows/system-morning-briefing-07-00.md` (07:00 sibling — the relabel that makes 07:00 special). **Functionality reality**: T-011 `docs/reality/workflows/morning-chain-orchestration.md` §11 outcome matrix.

## 0. TL;DR — what happens 14 times a day at 08:00, 09:00, ..., 21:00

| Step | Site | Outcome |
|------|------|---------|
| APScheduler fires | `scheduler.py:151-158` | same `_on_hourly` cron as 07:00 |
| Handler invoked | `scheduler.py:204-205` | `_on_hourly → self._run("hourly_delta")` |
| Orchestrator entered | `orchestrator.py:run_orchestrator(run_type="hourly_delta")` | single-flight lock attempt |
| **Relabel check fails** | `orchestrator.py:178` | `brussels_now_hour != 7` → stays `"hourly_delta"` |
| Connectivity probe | `orchestrator.py:gateway.is_connected()` | fail → `mode_detected="skipped_disconnected"` + empty audit row + return |
| Cold-start detection | `orchestrator.py:268-282` | position + watchlist counts → `cold_start | normal` |
| Optional seed_runner | `orchestrator.py:286-294` | fires only if `mode_detected=="cold_start"` |
| Watchlist confirmation override | `orchestrator.py:303-310` | flips to `awaiting_watchlist_confirmation` if unconfirmed |
| Market-data sub-step | gate at `:321` | **SKIPS** (`run_type not in {pre_briefing, morning_briefing}`) |
| Forecasting sub-step | gate at `:337` | **SKIPS** (`run_type != "morning_briefing"`) |
| DP composition sub-step | gate at `:358` | **SKIPS** (`run_type != "morning_briefing"`) |
| Calibration sub-step | gate at `:377` | **SKIPS** (`run_type != "pre_briefing"`) |
| Daily briefing + AI explanation | downstream of orchestrator | **SKIPS** (gated `run_type=="morning_briefing"` per T-011 §9) |
| Audit row | `worker_run_audit` table | `run_type="hourly_delta"`, `audit_payload = {}` (all slots empty) |

**Net work per hourly_delta fire**: write one `worker_run_audit` row + (rarely) run the seed_runner. **Zero new forecasts, zero new DPs, zero new action drafts, zero market-data refresh, zero LLM cost.** 14 fires per day, ~5,110 fires per year.

## 1. The cron trigger — same job as 07:00

Per T-032 §1, the worker scheduler registers a SINGLE hourly cron job:

```python
self._scheduler.add_job(
    self._on_hourly,
    "cron",
    hour="7-21",
    minute=0,
    timezone=self._scheduler_settings.timezone,
    id=_HOURLY_JOB_ID,
    replace_existing=True,
)
```

15 fires per day total: one at 07:00 (relabelled to `morning_briefing` per T-032 §2) + 14 at 08:00-21:00 (stay as `hourly_delta`).

The same `_on_hourly` handler runs each time:
```python
def _on_hourly(self) -> None:
    self._run("hourly_delta")
```

**`run_type="hourly_delta"` is hard-coded.** The differentiation between 07:00 and 08:00-21:00 happens inside the orchestrator's `_relabel_morning_briefing` (T-032 §2), which only acts when `brussels_now_hour == 7`.

## 2. The relabel skip — why 08:00-21:00 stay as `hourly_delta`

`orchestrator.py:167-180`:

```python
def _relabel_morning_briefing(
    run_type: RunType, brussels_now_hour: int
) -> RunType:
    if run_type == "hourly_delta" and brussels_now_hour == 7:
        return "morning_briefing"
    return run_type
```

At 08:00, 09:00, ..., 21:00, `brussels_now_hour != 7`, so the function returns `run_type` unchanged: still `"hourly_delta"`. **The label sticks for the rest of the orchestrator body.**

The 4 sub-step gates downstream test exact-equality:
- Market-data (`:321`): `run_type in ("pre_briefing", "morning_briefing")` → `False` for hourly_delta.
- Forecasting (`:337`): `run_type == "morning_briefing"` → `False`.
- DP composition (`:358`): `run_type == "morning_briefing"` → `False`.
- Calibration (`:377`): `run_type == "pre_briefing"` → `False`.

**Every gate fails.** No sub-step fires.

## 3. The 4 gate exclusions — verbatim

Each gate's `run_type` check at line-precise citations:

### 3.1 Market-data gate (`orchestrator.py:312-330`)

The comment at `:313-316` is explicit about hourly_delta:

```python
# 6. Task 129 market-data fetch.
# Only on normal fires that are also pre_briefing or
# morning_briefing. Hourly delta fires never re-fetch — EOD
# prices don't change intraday. The runner returns a small
# dict folded into the audit row.
```

> "Hourly delta fires never re-fetch — EOD prices don't change intraday."

This is the architectural intent: T-014 §3 documented that EODHD provides end-of-day data only; intra-day refreshes wouldn't yield new prices. **Technically correct for EOD data; misleading given the "delta" name**.

§9.1 — the system has a separate path for live mid-prices (IBKR on-demand quotes per T-014 §6), but that's not invoked during hourly_delta either.

### 3.2 Forecasting gate (`orchestrator.py:332-347`)

```python
forecast_details: dict[str, object] | None = None
if (
    forecasting_runner is not None
    and mode_detected == "normal"
    and run_type == "morning_briefing"   # ← excludes hourly_delta
    and ibkr_account_id is not None
):
    ...
```

T-015 §1 documented that forecasting only runs once per day at 07:00. The locked design is "fresh forecasts at start-of-day, then act on them all day". §9.2 — the design implies the user's view of "today's predictions" is static from 07:00 to 21:00; no intra-day re-forecasting.

### 3.3 DP composition gate (`orchestrator.py:348-370`)

```python
decision_package_details: dict[str, object] | None = None
if (
    decision_package_runner is not None
    and forecast_details is not None
    and "error" not in forecast_details
    and mode_detected == "normal"
    and run_type == "morning_briefing"   # ← excludes hourly_delta
    and ibkr_account_id is not None
):
    ...
```

Same exclusion. DP composition only runs after a fresh forecasting step, only at 07:00. §9.3 — at 14:00 when the user opens the app, they see the same DPs composed at 07:00 (~7 hours stale by then).

### 3.4 Calibration gate (`orchestrator.py:372-383`)

```python
calibration_details: dict[str, object] | None = None
if (
    calibration_runner is not None
    and mode_detected == "normal"
    and run_type == "pre_briefing"       # ← excludes hourly_delta (and morning_briefing!)
):
    ...
```

Calibration only runs at 06:00 pre_briefing (T-031 §3.4). Neither morning_briefing nor hourly_delta runs it.

## 4. What hourly_delta DOES do — heartbeat + cold-start

Despite the empty sub-step matrix, hourly_delta fires aren't pure no-ops. The orchestrator body runs Steps 1-5 regardless of `run_type`:

### 4.1 Step 1 — Lock acquisition

`SingleFlightLockProtocol.try_acquire()` (T-019 §2.3 + T-020 §2.3 + T-031 §2). Shared lock with submission sweep + reconciler. If contention → `skipped_locked` (no audit row written per T-020 §10.1). §9.4.

### 4.2 Step 2 — Connectivity probe

`gateway.is_connected()`. If False → audit row with `mode_detected="skipped_disconnected"` + empty payload + return.

### 4.3 Step 3 — Cold-start detection (`orchestrator.py:268-282`)

```python
if ibkr_account_id is None:
    mode_detected = "cold_start"
else:
    position_count = snapshot_counts.position_snapshot_count_for_account(ibkr_account_id)
    watchlist_count = snapshot_counts.watchlist_item_count_for_account(ibkr_account_id)
    if position_count == 0 and watchlist_count == 0:
        mode_detected = "cold_start"
    else:
        mode_detected = "normal"
```

The same SQL counts run on every fire — 14× per day for hourly_delta + 1× pre_briefing + 1× morning_briefing = 16 queries per day per account just to ask "is this account new?". §9.5.

### 4.4 Step 4 — Seed runner (`orchestrator.py:286-294`)

**This is the one substantive thing hourly_delta can do**: if a user starts using the system at 14:00 and `mode_detected="cold_start"`, the 14:00 hourly_delta fire triggers the seed_runner. Per T-012 §2.2, the seed_runner is partially wired in production; if wired, the 12-row starter watchlist gets seeded.

§9.6 — hourly_delta is the "user just signed up at an awkward time" path. The 07:00 fire would have seeded if the user was registered by then; the 06:00 fire would have detected cold_start but skipped the seed (T-031 §5). Hourly_delta covers the gap.

### 4.5 Step 5 — Watchlist confirmation override (`orchestrator.py:303-310`)

If the seed has been written and the user hasn't typed BEVESTIG yet (T-025), `mode_detected` is overridden to `"awaiting_watchlist_confirmation"`. Subsequent ticks see this state and stay in the holding pattern until the user confirms.

### 4.6 The audit row

```python
audit_payload: dict[str, object] = {}
if market_data_details is not None:
    audit_payload["market_data"] = market_data_details
if forecast_details is not None:
    audit_payload["forecast"] = forecast_details
if decision_package_details is not None:
    audit_payload["decision_package"] = decision_package_details
if calibration_details is not None:
    audit_payload["calibration"] = calibration_details
```

For hourly_delta, all 4 `_details` variables stay `None`. **`audit_payload` is `{}`.** The row IS written (with metadata: `run_id`, `started_at`, `completed_at`, `duration_ms`, `run_type="hourly_delta"`, `mode_detected`, `ibkr_account_id`) but the payload column is empty.

## 5. Cost analysis — 14 empty fires per day

Each hourly_delta fire produces a minimum cost:
- 1 `worker_run_audit` row INSERT.
- 2 SQL COUNT queries (cold-start detection).
- 1 connectivity probe (potentially a network round-trip to the IBKR gateway).
- 1 lock acquire/release cycle.

Over a year (~252 trading days × 14 fires/day = 3,528 fires):
- 3,528 audit rows (most with empty payload).
- 7,056 SQL COUNTs.
- 3,528 connectivity probes.

**Storage cost**: minimal in absolute terms but accumulating. The `worker_run_audit` table is rarely queried for hourly_delta rows specifically.

**Operational cost**: each fire briefly holds the shared single-flight lock. Submission sweep + reconciler ticks (T-019 §2.3 + T-020 §2.3 — neither wired to APScheduler per T-020 §10.1, but if/when wired) would contend with these every hour on the hour. §9.7.

## 6. The intent-vs-reality gap — "hourly delta" promises what?

The `RunType` Literal at `orchestrator.py:50`:

```python
RunType = Literal["pre_briefing", "morning_briefing", "hourly_delta"]
```

The name **"hourly delta"** strongly suggests:
- **"Hourly"** — fires every hour.
- **"Delta"** — computes differences from the prior state; i.e., picks up NEW data and computes the difference vs the morning baseline.

A reasonable operator reading this naming would assume:
- Fresh market data fetched hourly (it isn't — §3.1).
- Fresh forecasts computed against new data (they aren't — §3.2).
- Fresh DPs against fresh forecasts (they aren't — §3.3).
- The dashboard updates throughout the day (it doesn't — all output is from 07:00).

**Reality**: at 09:00, 10:00, ..., 21:00, the user's dashboard shows the same 07:00 outputs. The only intra-day mutation is via the user's own actions (approve / dismiss / delete drafts) or via the submission sweep + reconciler ticks (which are themselves not APScheduler-wired per T-020).

§9.8 — **dominant finding**. Phase 1c should either:
- Rename `hourly_delta` to something honest (e.g., `hourly_heartbeat` or `hourly_cold_start_check`).
- OR build the implied behavior: hourly market-data refresh (perhaps via IBKR live quotes per T-014 §6), hourly forecast recompute against fresher prices, intra-day DP composition.

## 7. Failure paths

1. **Lock contention** — submission sweep or reconciler holds the lock at :00. Hourly_delta returns `skipped_locked`; **NO audit row** per T-020 §10.1.
2. **Connectivity probe fails** — IBKR gateway unreachable. Audit row with `mode_detected="skipped_disconnected"` + empty payload. The fire DOES produce a row; observability preserved.
3. **Cold-start SQL fails** — exception caught at the orchestrator's outer try-except (per T-011 §13); `mode_detected="error"` audit row written.
4. **Seed runner exception** — caught at `:289-294`; logged via `logger.exception`; fire continues to write empty audit row. The cold-start handler is best-effort.
5. **Worker crashed at :59** — restart at :01 means the hourly_delta fire is lost. No catch-up (same as T-031 §7.1 + T-032 §7.1). **Loss is minimal** because the fire does nothing substantive anyway. §9.9.

## 8. Phase 1c surface (10 findings)

1. **Name-vs-behavior mismatch — DOMINANT FINDING** (§6) — "hourly delta" implies intra-day refresh + delta computation; reality is 14 empty fires per day. Most operationally misleading naming in the system-tick suite.
2. **All 4 sub-step gates explicitly EXCLUDE hourly_delta** (§3) — by exact-equality check on `run_type`. Adding a new sub-step that DOES want to run hourly would require modifying the gate logic.
3. **Cold-start SQL runs 16× per day per account** (§4.3) — same 2 COUNT queries on every fire. A user with no positions and no watchlist (cold-start) gets these executed 16 times even though the answer doesn't change between fires.
4. **The seed_runner path is hourly_delta's only substantive value** (§4.4) — covers the "user signed up at 14:00" edge case. Without this, cold-start would only fire at 06:00 + 07:00.
5. **Audit rows accumulate ~3,528 empty-payload rows per year** (§5) — storage cost is small but the rows are rarely queried; archiving policy unclear.
6. **Lock contention with submission sweep + reconciler at :00** (§5) — each hourly_delta fire briefly blocks the shared single-flight lock. If submission sweep + reconciler are ever APScheduler-wired (T-020 §10.1 gap), they will frequently contend with hourly_delta.
7. **No catch-up for missed hourly_delta** (§7.5) — restart-after-:59 loses the fire. Loss is minimal (no substantive work) but the audit-row gap is permanent.
8. **`skipped_locked` produces no audit row** (T-020 §10.1 + T-031 §9.2 + T-032 §9.10 carry-over) — hourly_delta inherits this gap; in busy hours, multiple hourly_delta fires might silently no-op with zero observability.
9. **Empty audit payload pattern conflates substantive empty with absent** — `audit_payload = {}` can mean "hourly_delta did nothing as designed" OR "an unexpected failure produced no payload". Operators must check `mode_detected` separately.
10. **Intent §1.3 of `docs/intent/_phase-1-charter.md` (cross-reference) doesn't pin hourly cadence behavior** — the locked decisions don't specify what hourly_delta should do. The current empty behavior is technically intent-compliant because intent says nothing.

## 9. Out of scope (re-confirmed)

- **06:00 pre_briefing fire** (T-031 — merged sibling).
- **07:00 morning_briefing fire** (T-032 — merged sibling).
- **Submission sweep tick** (T-019 — merged sibling; T-034 future system-tick doc).
- **Reconciliation tick** (T-020 — merged sibling; T-035 future system-tick doc).
- **API morning_chain.py parallel scheduler** (T-032 §5 — documented; T-033 cross-references).

## 10. References

- `apps/worker/src/portfolio_outlook_worker/scheduler.py:151-158` (cron registration shared with 07:00)
- `apps/worker/src/portfolio_outlook_worker/scheduler.py:204-205` (`_on_hourly` handler)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:50` (`RunType` Literal — "hourly_delta")
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:167-180` (`_relabel_morning_briefing` — skip for hour != 7)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:313-316` (comment: "Hourly delta fires never re-fetch")
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:321` (market-data gate exclusion)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:337` (forecasting gate exclusion)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:358` (DP composition gate exclusion)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:377` (calibration gate exclusion)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:268-310` (cold-start + watchlist confirmation steps that DO run)
- `docs/reality/workflows/morning-chain-orchestration.md` (T-011 — §11 outcome matrix)
- `docs/reality/workflows/system-morning-pre-briefing-06-00.md` (T-031 — 06:00 sibling)
- `docs/reality/workflows/system-morning-briefing-07-00.md` (T-032 — 07:00 sibling + relabel)
- `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` (T-012 — seed_runner mechanism)
- `docs/reality/workflows/market-data-pipeline.md` (T-014 — EODHD EOD-only + IBKR live quote)
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015 — once-per-day forecasting)
