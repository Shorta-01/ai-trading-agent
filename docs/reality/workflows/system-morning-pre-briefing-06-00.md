# System Morning Pre-Briefing — 06:00 Brussels

**Scope.** System-tick workflow narrating the 06:00 Brussels `pre_briefing` cron fire from the system's perspective — APScheduler trigger → `_on_pre_briefing` handler → `run_orchestrator(run_type="pre_briefing")` → single-flight lock + connectivity + mode detection → **2 sub-steps run** (market-data refresh + calibration) → **3 sub-steps deliberately skip** (forecasting / DP composition / daily briefing — those wait for 07:00 `morning_briefing`) → `worker_run_audit` row written. This is the lightest of the three morning fires; the heavy work happens at 07:00.

**Sibling functionality reality**: T-011 `docs/reality/workflows/morning-chain-orchestration.md` (full coverage of all 3 morning fires); T-014 `docs/reality/workflows/market-data-pipeline.md` (the market-data sub-step); T-016 `docs/reality/workflows/forecast-calibration-and-prediction-diary.md` (the calibration sub-step). **Component reality**: T-007 `docs/reality/components/worker-orchestration-and-scheduling.md`.

## 0. TL;DR — what the system does at 06:00

| Step | Site | Outcome at 06:00 fire |
|------|------|------------------------|
| APScheduler fires | `scheduler.py:141-149` | `cron hour=6, minute=0 Europe/Brussels` |
| Handler invoked | `scheduler.py:201-202` | `_on_pre_briefing → self._run("pre_briefing")` |
| Orchestrator entered | `orchestrator.py:run_orchestrator(run_type="pre_briefing")` | single-flight lock acquired |
| Connectivity check | `orchestrator.py:gateway.is_connected()` | fail → `mode_detected="skipped_disconnected"` |
| Cold-start detection | `orchestrator.py:268-282` | position_count + watchlist_count → `mode_detected` |
| **Market-data sub-step** | `orchestrator.py:312-330` | gated `mode=normal AND run_type in (pre_briefing, morning_briefing)` |
| Forecasting | gated, SKIPS | `run_type != "morning_briefing"` — does NOT fire |
| DP composition | gated, SKIPS | same — does NOT fire |
| **Calibration sub-step** | `orchestrator.py:372-383` | gated `mode=normal AND run_type=="pre_briefing"` — **fires only on 06:00** |
| Daily briefing | downstream of orchestrator, SKIPS | only on `morning_briefing` |
| Audit row | `worker_run_audit` table | `run_type="pre_briefing"`, payload includes `market_data` + `calibration` slots only |

**Net result of the 06:00 fire**:
- Fresh EODHD EOD prices + FX rates in `market_data_latest_snapshots` (input for 07:00).
- Scored calibration metrics in `forecast_calibration` (input for 07:00 predictor-weight decisions).
- Zero new forecasts, zero new Decision Packages, zero new action drafts produced at 06:00.

## 1. The cron trigger — `scheduler.py:141-149`

```python
self._scheduler.add_job(
    self._on_pre_briefing,
    "cron",
    hour=6,
    minute=0,
    timezone=self._scheduler_settings.timezone,
    id=_PRE_BRIEFING_JOB_ID,  # = "pre_briefing" (scheduler.py:50)
    replace_existing=True,
)
```

- **`hour=6, minute=0`** — fixed by code; the `SCHEDULER_DAILY_BRIEFING_CRON` config default is `"30 6 * * *"` (per T-011 §1) but the in-code APScheduler job pins `06:00` exactly. Operator overriding `SCHEDULER_DAILY_BRIEFING_CRON` would NOT shift this fire — the config string is informational, not consumed by the cron registration. §9.1.
- **`timezone="Europe/Brussels"`** (locked at `apps/worker/src/portfolio_outlook_worker/config.py:64` default). DST-aware. On the DST switch days, the fire honours Brussels wall-clock 06:00, not UTC.
- **`replace_existing=True`** — restarting the worker re-registers the job idempotently.

The handler at `:201-202`:

```python
def _on_pre_briefing(self) -> None:
    self._run("pre_briefing")
```

Trivial wrapper. The real work is in `self._run(run_type)` which calls `run_orchestrator(run_type="pre_briefing")`.

## 2. The orchestrator entry — `run_orchestrator(run_type="pre_briefing")`

Per T-011 §2-§4, the orchestrator does the same Steps 1-2 regardless of `run_type`:

1. **Single-flight lock** (T-011 §3) — `ORCHESTRATOR_LOCK_KEY` advisory lock. Same lock shared with submission sweep + reconciler ticks (T-019 §2.3 + T-020 §2.3). Failing to acquire → return early; no audit row written for `skipped_locked`-on-acquire path (T-020 §10.1 documented this audit gap; applies here too). §9.2.
2. **Connectivity probe** — `gateway.is_connected()`. Failure → `mode_detected="skipped_disconnected"`; audit row written but no further work.
3. **Cold-start detection** (`orchestrator.py:268-282`) — counts positions + watchlist items; sets `mode_detected` to `cold_start` or `normal` (per T-012 §1).

The `mode_detected` outcome drives the rest of the tick. Per T-011 §4, the 6 literal values are: `cold_start | normal | awaiting_watchlist_confirmation | skipped_disconnected | skipped_locked | error`. (Plus `skipped_disabled` declared but never written per T-007.)

## 3. The sub-step gates — what runs at 06:00

The `run_orchestrator` body has 5 sub-steps after mode detection. Each has its own gate. For `run_type="pre_briefing"`:

### 3.1 Market-data step — RUNS (`orchestrator.py:312-330`)

```python
if (
    market_data_runner is not None
    and mode_detected == "normal"
    and run_type in ("pre_briefing", "morning_briefing")
    and ibkr_account_id is not None
):
    try:
        market_data_details = market_data_runner.run()
    except Exception:
        logger.exception("market_data_runner failed")
        market_data_details = {"error": "market_data_runner_exception"}
```

**Fires on pre_briefing AND morning_briefing** — both 06:00 and 07:00 refresh market data. T-014 §3 documented why: research-side EODHD EOD data needs to be present by both fires (the 06:00 calibration needs yesterday's close to score; the 07:00 forecasting needs today's freshest close). Hourly_delta fires (08:00-21:00) SKIP this step — EOD prices don't change intraday.

**Exception swallowing**: a market-data failure does NOT abort the fire. The error string lands in `market_data_details`; the rest of the chain proceeds (in this case, the calibration step) using whatever market data was already in storage. §9.3.

### 3.2 Forecasting step — SKIPS

Per T-011 §6, the forecasting gate at `orchestrator.py:332-359` (referenced; not re-cited here) requires `run_type in ("morning_briefing", "hourly_delta")`. Pre_briefing falls outside; no forecasts are generated at 06:00.

### 3.3 Decision Package composition — SKIPS

Same pattern — DP composition runs after forecasting, only on `morning_briefing` or `hourly_delta`. No DPs composed at 06:00.

### 3.4 Calibration step — RUNS (and ONLY at pre_briefing) — `orchestrator.py:372-383`

```python
calibration_details: dict[str, object] | None = None
if (
    calibration_runner is not None
    and mode_detected == "normal"
    and run_type == "pre_briefing"
):
    try:
        calibration_details = calibration_runner.run()
    except Exception:  # noqa: BLE001 — boundary
        logger.exception("calibration_runner failed")
        calibration_details = {"error": "calibration_runner_exception"}
```

**This is the UNIQUE work of the 06:00 fire.** Morning_briefing skips this; hourly_delta skips this. Only pre_briefing scores yesterday's expired forecasts against realised closes (T-016 §3).

The calibration step:
- Reads `forecast_predictions` from yesterday whose horizon has expired (T-016 §1).
- Joins them against `market_data_latest_snapshots.close_price` for the expiration date.
- Computes per-prediction `hit_status` (4 outcomes: hit / miss / partial / inconclusive — T-016 §2).
- Writes `forecast_calibration` rows (T-016 §3) capturing per-predictor accuracy + per-asset bias.

The output feeds **predictor-feedback weight updates** that the 07:00 forecasting step consumes for the ensemble weighting (T-024 §6 — bounded by `DEFAULT_WEIGHT_CLIP_LOW=0.05` / `DEFAULT_WEIGHT_CLIP_HIGH=0.40`).

**Exception swallowing**: same as market-data. Calibration failure does NOT abort; the error string lands in `calibration_details`; predictor weights stay at whatever value the previous successful calibration set. §9.3.

### 3.5 Daily briefing + AI explanation — SKIPS

Per T-011 §9, the daily briefing + AI explanation orchestrator runs downstream of the worker chain, gated on `run_type="morning_briefing"`. Pre_briefing does NOT trigger an AI explanation call. The cost of the 06:00 fire is therefore **bounded** — no LLM cost (Anthropic Claude calls per T-023 §4 — explanation provider) and no daily-briefing composition cost.

## 4. The audit row — `worker_run_audit`

After all gated sub-steps complete (`orchestrator.py:385-...`), the orchestrator builds a single audit-row payload:

```python
duration = _duration_ms(started, now_provider())
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

For a successful pre_briefing fire on `mode_detected="normal"`, the payload has exactly 2 slots: `market_data` + `calibration`. The other slots (`forecast`, `decision_package`) are absent because the gates didn't fire.

The row also captures (per T-011 §10):
- `run_id` (UUID per fire)
- `started_at` / `completed_at` / `duration_ms`
- `run_type = "pre_briefing"`
- `mode_detected`
- `ibkr_account_id` (or NULL if unconfigured)
- `error_details_json` (NULL on success; populated on top-level exception)

**The audit row is THE source of truth for "did 06:00 fire today and what happened?"** — no separate log surface, no metrics endpoint. An operator inspecting yesterday's 06:00 fire reads one row from `worker_run_audit`.

## 5. The outcome ↔ mode matrix for 06:00

Per T-011 §11, the matrix of `mode_detected` × `run_type`. Specifically for `run_type="pre_briefing"`:

| `mode_detected` | What runs at 06:00 |
|------------------|---------------------|
| `normal` | Market-data refresh + calibration. Both sub-steps fire if their runners are wired. |
| `cold_start` | Nothing — sub-step gates all require `mode_detected="normal"`. Cold-start handler (T-012 §2) may invoke the seed_runner if wired (T-012 §2.2 documented this wiring is partial). |
| `awaiting_watchlist_confirmation` | Nothing substantive — the chain enters this mode after detecting unconfirmed watchlist (T-012 §1.3) and short-circuits before the sub-steps. |
| `skipped_disconnected` | Nothing — IBKR gateway not reachable. Audit row written; no sub-steps fire. |
| `skipped_locked` | Nothing — another tick holds the orchestrator lock. **No audit row written** per the lock-fail-fast path (T-020 §10.1 audit gap). §9.2. |
| `error` | Best-effort completion — top-level exception caught; audit row written with `error_details_json`. |

**Only `mode_detected="normal"` does meaningful work at 06:00.** The other 5 modes produce either a marker audit row or no audit row at all.

## 6. Why pre_briefing exists — the 1-hour buffer architecture

The architectural rationale for splitting 06:00 + 07:00 into two separate fires:

1. **Input freshness**: market data must be present before the forecasting step at 07:00 can compute new predictions. By fetching at 06:00, the system has a 1-hour buffer to retry if EODHD is slow (T-014 §5 documented retry behavior).
2. **Calibration freshness**: predictor weights for 07:00's ensemble depend on yesterday's actual outcomes vs predictions. By scoring at 06:00, the calibration values are stored in `forecast_calibration` and ready for 07:00's ensemble decision (T-024 §6 — inverse-Brier auto-weight computation reads these).
3. **Fault isolation**: if market-data fails at 06:00, the 07:00 forecasting can still run (using stale market data, with the freshness gate per T-014 §4 marking outputs accordingly). If calibration fails at 06:00, 07:00's ensemble uses last-known weights. Neither failure cascades to block user-visible 07:00 briefing.
4. **Cost separation**: the LLM explanation cost (T-023) only fires at 07:00. The 06:00 fire is **zero-LLM-cost** by design.

§9.4 — the architecture works, but the resilience is **untested in production** for the lock-shared scenario: if a long-running 06:00 calibration somehow holds the lock past 07:00, the 07:00 fire would `skipped_locked` with no audit row, and the user would see "yesterday's briefing" on the dashboard at 07:00 with no system signal that anything went wrong. The audit gap is the silence; the user gap is the staleness.

## 7. Failure paths for the 06:00 fire

1. **APScheduler missed the fire** (worker crashed at 05:59, restarted at 06:01) — APScheduler re-registers the job on startup (`replace_existing=True`); the next fire would be tomorrow at 06:00. The system has no "catch-up" fire for missed cron windows. §9.5.
2. **Lock contention** — another tick (submission sweep / reconciler) holds the lock at 06:00. Pre_briefing returns `skipped_locked`; NO audit row (per T-020 §10.1 gap). The 07:00 fire would also be at risk if the lock is still held.
3. **`gateway.is_connected()` returns False** — IBKR gateway unreachable. Audit row written with `mode_detected="skipped_disconnected"`; both sub-steps skip; downstream 07:00 inherits the disconnection state (likely also fails connectivity).
4. **Market-data exception** — `market_data_runner.run()` raises. Exception caught; `market_data_details = {"error": "..."}`. Calibration still runs but reads stale data.
5. **Calibration exception** — same pattern; `calibration_details = {"error": "..."}`. Audit row records both attempts.
6. **Top-level exception** — caught at the orchestrator's outermost try-except (per T-011 §13); audit row written with `error_details_json`.
7. **`cold_start` mode at 06:00 with seed_runner not wired** — sub-steps all skip (per §5); cold-start handler tries to invoke seed_runner but per T-012 §2.2 the wiring is partial. Audit row records `mode_detected="cold_start"` with empty payload. The user wakes up to a system that detected first-time setup but didn't seed the starter watchlist.

## 8. Phase 1c surface (10 findings specific to the 06:00 tick)

1. **Cron config string `SCHEDULER_DAILY_BRIEFING_CRON="30 6 * * *"` is informational only** (§1) — the in-code APScheduler job pins `06:00` exactly. Operator overriding the config string does NOT change the fire time. Config-vs-reality drift; T-007 originating finding.
2. **`skipped_locked` produces no audit row** (§2.1, §5) — same gap T-020 §10.1 documented for the reconciler. Operators cannot reconstruct the lock-contention timeline from `worker_run_audit`.
3. **Both market-data and calibration exceptions are swallowed silently** (§3.1, §3.4) — `logger.exception` writes to logs; nothing surfaces to the user-facing system-health line (per intent §2 + doctrine §10). User wakes up to stale calibration values with no visible signal.
4. **Long-running calibration could hold the lock past 07:00** (§6) — no per-tick deadline. The orchestrator's `_run_locked` body has no timeout; if calibration loops over many predictors × assets (per T-024 §1.1), runtime is unbounded.
5. **No catch-up fire for missed 06:00** (§7.1) — a worker crash at 05:59 + restart at 06:01 results in NO 06:00 fire today. Calibration scores are 24 hours stale; 07:00 uses last-day's weights.
6. **Cold-start handler with unwired seed_runner produces a silent gap** (§7.7) — T-012 §2.2 documented partial wiring. At 06:00 on day 1, the cold-start audit row is written but no seed appears.
7. **`mode_detected="awaiting_watchlist_confirmation"` short-circuits before sub-steps** (§5) — calibration does NOT run while the user is unconfirmed. Day-1 calibration backlog accumulates until the user confirms.
8. **The 1-hour buffer is untested for hot-restart scenarios** (§6) — if the worker is restarted at 06:30 (after pre_briefing but before morning_briefing), the in-progress calibration state may be lost; the 07:00 fire would inherit either partial or no calibration data. No documented test.
9. **No metrics endpoint for tick health** (§4) — the only signal is the `worker_run_audit` row. No Prometheus / Datadog / structured-log scrape surface. Operators must SQL-query the audit table to monitor.
10. **Single-flight lock is shared with submission sweep + reconciler** (§2.1) — per T-019 §2.3 + T-020 §2.3. At 06:00 (typically before market open), submission sweep + reconciler are typically idle, so contention is rare. But there's no formal scheduling policy that prevents lock collisions.

## 9. Out of scope (re-confirmed)

- **Full morning chain** (T-011 — merged sibling; T-031 narrows to 06:00 only).
- **Calibration deep dive** (T-016 — merged sibling).
- **Market-data deep dive** (T-014 — merged sibling).
- **07:00 morning_briefing fire** (T-032 — next task).
- **Hourly_delta fires** (T-033 — future task).
- **Predictor backtest scheduling** (T-024 — separate cadence).
- **Reconciliation tick** (T-020 + T-035 future).

## 10. References

- `apps/worker/src/portfolio_outlook_worker/scheduler.py:50` (`_PRE_BRIEFING_JOB_ID`)
- `apps/worker/src/portfolio_outlook_worker/scheduler.py:141-149` (cron registration)
- `apps/worker/src/portfolio_outlook_worker/scheduler.py:201-202` (`_on_pre_briefing` handler)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:50` (`RunType` Literal)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:268-282` (cold-start detection)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:312-330` (market-data gate)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:372-383` (calibration gate)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:385+` (audit payload assembly)
- `docs/reality/workflows/morning-chain-orchestration.md` (T-011 — full 3-fire functionality)
- `docs/reality/workflows/forecast-calibration-and-prediction-diary.md` (T-016 — calibration sub-step)
- `docs/reality/workflows/market-data-pipeline.md` (T-014 — market-data sub-step)
- `docs/reality/components/worker-orchestration-and-scheduling.md` (T-007)
- `docs/reality/workflows/cold-start-seeding-and-watchlist-confirmation.md` (T-012)
- `docs/reality/workflows/ibkr-order-submission-lifecycle.md` (T-019 — shared lock)
- `docs/reality/workflows/ibkr-reconciliation-passes-a-b-c.md` (T-020 — shared lock + audit gap)
- `docs/reality/workflows/predictor-backtest-and-leaderboard.md` (T-024 — calibration → weight feedback)
- `docs/reality/workflows/ai-explanation-and-budget.md` (T-023 — zero-LLM-cost at 06:00)
