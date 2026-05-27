# System Morning Briefing — 07:00 Brussels

**Scope.** System-tick workflow narrating the 07:00 Brussels morning_briefing fire from the system's perspective — APScheduler fires the same `_on_hourly` handler that runs every hour 7-21, but the orchestrator's `_relabel_morning_briefing` helper flips the `run_type` to `"morning_briefing"` when `brussels_now_hour == 7`. **All 5 sub-steps fire** at 07:00 (market-data refresh + forecasting + DP composition + daily briefing + AI explanation downstream) — the heaviest fire of the day, and **the only fire that costs Anthropic Claude tokens**. The doc also documents a dual-scheduler doctrine drift: a parallel API-side morning chain (`apps/api/src/portfolio_outlook_api/morning_chain.py`) runs independently with its own APScheduler.

**Sibling functionality reality**: T-011 `docs/reality/workflows/morning-chain-orchestration.md` (full coverage of all 3 fires); T-015 `docs/reality/workflows/forecast-generation-and-labelling.md` (forecasting sub-step); T-017 `docs/reality/workflows/decision-package-composition.md` (DP composition sub-step); T-023 `docs/reality/workflows/ai-explanation-and-budget.md` (LLM explanation downstream of orchestrator). **System-tick sibling**: T-031 `docs/reality/workflows/system-morning-pre-briefing-06-00.md`.

## 0. TL;DR — what the system does at 07:00

| Step | Site | Outcome at 07:00 fire |
|------|------|------------------------|
| APScheduler fires | `scheduler.py:151-158` | `cron hour="7-21", minute=0 Europe/Brussels` |
| Handler invoked | `scheduler.py:204` | `_on_hourly → self._run("hourly_delta")` |
| Orchestrator entered | `orchestrator.py:run_orchestrator(run_type="hourly_delta")` | single-flight lock acquired |
| **Relabel hour=7 → morning_briefing** | `orchestrator.py:167-180` | `_relabel_morning_briefing(run_type, brussels_now_hour=7)` |
| Connectivity check | `orchestrator.py:gateway.is_connected()` | fail → `mode_detected="skipped_disconnected"` |
| Mode detection | `orchestrator.py:268-282` | position + watchlist counts |
| **Market-data sub-step** | `orchestrator.py:312-330` | RUNS (gate: `run_type in (pre_briefing, morning_briefing)`) |
| **Forecasting sub-step** | `orchestrator.py:332-347` | RUNS (gate: `run_type == "morning_briefing"`) — **only morning_briefing** |
| **DP composition sub-step** | `orchestrator.py:348-370` | RUNS (gate: same) — **only morning_briefing** |
| Calibration SKIPS | `orchestrator.py:372-383` | only on pre_briefing (T-031 §3.4) |
| **Daily briefing + AI explanation** | downstream of orchestrator (T-011 §9) | RUNS — **the only LLM-cost fire of the day (T-023)** |
| Audit row | `worker_run_audit` table | `run_type="morning_briefing"`, payload includes `market_data` + `forecast` + `decision_package` slots (3 populated; `calibration` empty) |

**Net result of the 07:00 fire**:
- New `forecast_predictions` rows for the asset universe (T-015 §3).
- New `decision_packages` rows for each asset (T-017 §5).
- New `decision_package_explanations` rows (LLM Anthropic Claude calls — T-023 §5).
- New daily briefing surface for the dashboard.
- Action drafts composed for actionable labels (Kopen / Verminderen / Verkopen — T-018, T-026).

**Plus**: the dashboard the user wakes up to at 07:30 reflects this fire's output.

## 1. The cron trigger — `scheduler.py:151-158`

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

**One cron job, multiple fires per day**: 07:00, 08:00, 09:00, ..., 21:00 — 15 fires total. The same `_on_hourly` handler runs each time. The handler at `scheduler.py:204`:

```python
def _on_hourly(self) -> None:
    self._run("hourly_delta")
```

Always invokes with `run_type="hourly_delta"`. The differentiation between 07:00 (morning_briefing) and 08:00-21:00 (hourly_delta) happens **inside the orchestrator**, not at the scheduler.

## 2. The `_relabel_morning_briefing` clever — `orchestrator.py:167-180`

```python
def _relabel_morning_briefing(
    run_type: RunType, brussels_now_hour: int
) -> RunType:
    """The 07:00 hourly fire gets relabelled in the audit row.

    Task 127 product lock §2: the cron job is one ``hourly`` trigger;
    the 07:00 instance is the morning briefing. Encoding this in the
    orchestrator (not in two separate cron jobs) keeps the trigger
    surface narrow.
    """

    if run_type == "hourly_delta" and brussels_now_hour == 7:
        return "morning_briefing"
    return run_type
```

Called at `orchestrator.py:238`:
```python
run_type = _relabel_morning_briefing(
    run_type, brussels_hour_provider() if brussels_hour_provider else now_provider().hour
)
```

**Architectural choice**: one cron job for all 15 hourly fires, then conditional relabelling. The rationale from the docstring: "keeps the trigger surface narrow". Trade-off:
- **Pro**: single APScheduler job; one fewer registration; failure modes uniform.
- **Con**: the "morning_briefing" identity is implicit in the wall-clock time, not in the cron schedule. An operator overriding the orchestrator's `brussels_hour_provider` for tests (or in a hot-restart scenario where the wall clock skews) could accidentally produce two `morning_briefing` records OR zero.

§9.1 — the relabel discipline depends on `brussels_now_hour == 7` being reliable. If the worker's clock is off, the relabel doesn't fire and 07:00 gets recorded as `hourly_delta`. The audit row would still capture the work done, but the `run_type` field would mislabel it — affecting any analytics that filter on `run_type="morning_briefing"`.

## 3. The sub-step gates — what runs at 07:00

The orchestrator has 5 gated sub-steps after mode detection (per T-011 §6-§9 + T-031 §3 enumeration). For `run_type="morning_briefing"`:

### 3.1 Market-data step — RUNS (same gate as 06:00)

`orchestrator.py:312-330` — gate: `run_type in ("pre_briefing", "morning_briefing")`. Fires.

At 07:00, the market-data refresh re-fetches EOD prices + FX rates. The 06:00 fire already refreshed; the 07:00 fire re-refreshes for the freshest snapshot. T-014 §3 documented why both fires refresh: research-side EODHD EOD data should be present by both ticks.

### 3.2 Forecasting step — RUNS (morning_briefing ONLY) — `orchestrator.py:332-347`

```python
forecast_details: dict[str, object] | None = None
if (
    forecasting_runner is not None
    and mode_detected == "normal"
    and run_type == "morning_briefing"
    and ibkr_account_id is not None
):
    try:
        forecast_details = forecasting_runner.run()
    except Exception:
        logger.exception("forecasting_runner failed")
        forecast_details = {"error": "forecasting_runner_exception"}
```

**Gate is exact-equality to `"morning_briefing"`.** Even at 07:00, if `_relabel_morning_briefing` failed (e.g., clock off, hour != 7), the gate would NOT fire. Per T-015 §1, the forecasting step produces new `forecast_predictions` rows for the asset universe — the engine that drives the whole 07:00 fire.

Per T-024 §4.2 (re-confirmed for 5th time at T-024 §10.12), the forecasting step currently runs **only `historical_bootstrap_v1`** (1 of intent's locked 7 predictors). The other 6 portfolio predictor modules exist but aren't wired into the worker forecasting step. So at 07:00, only one predictor's predictions land.

**Exception swallowing**: same pattern as T-031 §3.1 — failure does NOT abort the chain. `forecast_details = {"error": "..."}`; the chain proceeds to DP composition (which then has no fresh forecasts to consume).

### 3.3 DP composition step — RUNS (morning_briefing ONLY) — `orchestrator.py:348-370`

Same gate pattern. Per T-017 §3, composes a Decision Package for each asset that has fresh forecasts + 5 composition gates pass. The DP composer reads from the just-written `forecast_predictions` rows from §3.2.

**If forecasting failed** (per §3.2), the DP composer reads zero new predictions → composes zero new DPs → the dashboard shows yesterday's DPs (or none if first run). The cascade is silent — no system-health red light. §9.3 (carry-over from T-031 §9.3).

### 3.4 Calibration step — SKIPS at 07:00 (T-031 §3.4)

`orchestrator.py:372-383` gate requires `run_type == "pre_briefing"`. Morning_briefing skips. Calibration is the unique work of 06:00; 07:00 reads `forecast_calibration` for predictor weights but never writes to it.

### 3.5 Daily briefing + AI explanation — RUNS (downstream)

Per T-011 §9, the daily briefing + AI explanation orchestrator runs downstream of the worker chain, gated on `run_type="morning_briefing"`. This is where the LLM cost lands.

**The LLM cost surface**:
- Per T-023 §1, the explanation provider (`AnthropicExplanationProvider` at `anthropic_explanation_provider.py:182`) fires per Decision Package composed.
- Per T-023 §4, each call decrements the monthly EUR budget (`claude_ai_budget_monthly_eur = €50` default; `assert_budget_available` hard-stops if exhausted).
- Per T-023 §1.2, the actual prompt is a "2-3 sentence Dutch paraphrase" (hard-coded `SYSTEM_PROMPT_NL`), not the intent §1 6-element structured Depth-B explanation.
- Per T-023 §6, an out-of-date banner on the action draft page says "IBKR-verzending wordt in een toekomstige update toegevoegd" — contradicting shipped submission infrastructure.

**07:00 is the ONLY fire that costs Anthropic Claude tokens.** All other ticks (06:00 pre_briefing, 08:00-21:00 hourly_delta, submission sweep, reconciler) are zero-LLM-cost. §9.5 — this concentrates LLM cost into a single daily window. If a single asset's explanation call hits an error path that triggers retries, the cost can spike unpredictably.

### 3.6 Action draft composition — RUNS (downstream, via API)

Per T-018 §2, the worker DP composer can produce action drafts for actionable labels (Kopen / Verminderen / Verkopen). At 07:00 fresh DPs are composed; the action-draft composer reads them and creates fresh `proposed` rows in `asset_action_drafts`. The user at 07:30 sees these new drafts on `/ibkr-acties`.

## 4. The audit row — `worker_run_audit`

Same composition pattern as T-031 §4. For a successful 07:00 morning_briefing fire on `mode_detected="normal"`:

```python
audit_payload = {
    "market_data": {...},
    "forecast": {...},
    "decision_package": {...},
    # NOT "calibration" — that's pre_briefing only
}
```

3 populated slots. The `worker_run_audit` row also captures:
- `run_id` (UUID)
- `started_at` / `completed_at` / `duration_ms`
- `run_type = "morning_briefing"` (after relabel)
- `mode_detected`
- `ibkr_account_id`
- `error_details_json` (NULL on success)

**Note**: the AI explanation cost ISN'T in this audit row. AI calls are tracked separately in `claude_ai_budget_usage` (T-023 §4.1). Cross-referencing the two tables by timestamp is the only way to attribute a 07:00 fire's LLM cost.

## 5. The dual-scheduler doctrine drift

This is the dominant finding of T-032.

### 5.1 The worker scheduler (`apps/worker/src/.../scheduler.py`)

Per T-031 §1 + T-032 §1:
- Worker scheduler registers 3 jobs: `_on_pre_briefing` (06:00 fixed), `_on_hourly` (7-21 fixed), `_heartbeat` (interval).
- Worker uses fixed `hour=6` and `hour="7-21"` literals — not config-driven.
- `SCHEDULER_DAILY_BRIEFING_CRON` config string (default `"30 6 * * *"` = 06:30) is **IGNORED** by the worker.

### 5.2 The API scheduler (`apps/api/src/portfolio_outlook_api/scheduler.py:107-257`)

A **parallel** APScheduler instance lives in the API:
- `run_daily_briefing_job` function (`scheduler.py:107`) wraps `apps/api/src/portfolio_outlook_api/morning_chain.py`'s `run_morning_chain` via `build_scheduler_chain_callable`.
- The API scheduler reads `runtime_settings.scheduler_daily_briefing_cron` (`:236-237`) — the SAME config string the worker ignores.
- `scheduler.add_job(...)` (`:257`) registers the API morning chain at whatever the cron string says (default 06:30).

### 5.3 The parallel morning chain (`apps/api/src/.../morning_chain.py`)

`apps/api/src/portfolio_outlook_api/morning_chain.py:34-49` defines 6 named legs:
- `LEG_MARKET_DATA_SYNC`
- `LEG_FORECAST_SYNC`
- `LEG_SUGGESTION_SYNC`
- `LEG_DECISION_PACKAGE_SYNC`
- `LEG_ACTION_DRAFT_SYNC`
- `LEG_DAILY_BRIEFING_SYNC`

The API morning chain runs ALL 6 legs in sequence (`run_morning_chain` at `:128`). On any leg failure, the chain stops at that point (`MorningChainFailed` raised).

**The API morning chain has its own forecast / DP / action draft writers.** Both chains write to the same storage tables (`forecast_predictions`, `decision_packages`, `asset_action_drafts`). No coordination, no idempotency key shared between them, no documented order.

### 5.4 What happens when both fire on the same day

If the API scheduler is enabled (default behavior depends on env-var config) AND the cron config defaults to 06:30, then the day looks like:

| Time | Fire | Source |
|------|------|--------|
| 06:00 | worker pre_briefing | worker scheduler |
| 06:30 | API morning chain | API scheduler (configurable) |
| 07:00 | worker morning_briefing | worker scheduler |
| 08:00-21:00 | worker hourly_delta × 14 | worker scheduler |

**Both 06:30 and 07:00 attempt to write `forecast_predictions` + `decision_packages` for the same asset universe.** The interaction is unspecified:
- If both succeed, the 07:00 fire overwrites the 06:30 outputs (UPSERT pattern).
- If 06:30 fails partway, the 07:00 fire may see partial state.
- Both fires consume LLM cost; the user's monthly EUR budget can be exhausted faster than intent §4 anticipated.
- The audit trail is split across `worker_run_audit` (worker) AND the API's own `scheduler_runs` table (API).

§9.6 — **most significant finding of T-032**. Phase 1c should either:
- Disable the API scheduler entirely (let the worker be the sole orchestrator), OR
- Document the coordination contract (which writer wins, how the LLM cost is split).

### 5.5 The shared config string

`SCHEDULER_DAILY_BRIEFING_CRON` is read by both schedulers:
- Worker: **silently ignored** (`scheduler.py:141-149` pins `hour=6, minute=0` literal).
- API: **honored** (`scheduler.py:236-237` reads `runtime_settings.scheduler_daily_briefing_cron`).

T-031 §1 originated this drift; T-032 surfaces it as a Phase 1c blocker because it directly affects two parallel morning chains. Operators changing the config string believe they're shifting "the morning chain" — they're shifting only the API one. The worker keeps firing at 06:00 + 07:00. §9.7.

## 6. The outcome ↔ mode matrix for 07:00

Same as T-031 §5 but with morning_briefing-specific behavior:

| `mode_detected` | What runs at 07:00 |
|------------------|---------------------|
| `normal` | All 5 sub-steps (market-data + forecasting + DP composition + daily briefing + AI explanation downstream). Full chain. |
| `cold_start` | Nothing — sub-step gates all require `mode_detected="normal"`. The user wakes up to the cold-start banner (T-012, T-025); no fresh forecasts. |
| `awaiting_watchlist_confirmation` | Nothing substantive — chain short-circuits. The user wakes up to yesterday's dashboard (or empty if first day). |
| `skipped_disconnected` | Nothing — IBKR gateway not reachable. Audit row written; user wakes up to a dashboard with no fresh data. |
| `skipped_locked` | Nothing — another tick holds the lock. **No audit row** per T-020 §10.1 + T-031 §9.2. The user might see yesterday's briefing at 07:30 with no system signal. |
| `error` | Best-effort completion — top-level exception caught; audit row written with `error_details_json`. |

**Only `mode_detected="normal"` produces a fresh morning briefing.** All 5 other modes leave the user looking at stale or empty state.

## 7. Failure paths for the 07:00 fire

1. **Cron missed (worker crashed at 06:59, restarted at 07:01)** — APScheduler doesn't fire a catch-up; the day's morning briefing is lost. **Worse than T-031 §7.1** because users actively expect this fire — they wake up at 07:30 and see yesterday's data with no system explanation.
2. **`_relabel_morning_briefing` doesn't fire (clock skew)** — 07:00 fire gets recorded as `hourly_delta`. The forecasting + DP + AI explanation gates all check `run_type == "morning_briefing"` exactly; they would SKIP. The audit row would show `hourly_delta` but the user would have no fresh briefing. §9.1.
3. **Forecasting exception** — `forecast_details = {"error": "..."}`; DP composer reads zero new forecasts; dashboard shows yesterday's DPs.
4. **DP composer exception** — `decision_package_details = {"error": "..."}`; daily briefing reads zero new DPs; AI explanation skipped (nothing to explain); user wakes up to yesterday's briefing.
5. **AI explanation budget exhausted** — `ClaudeAiBudgetExceededError` from `assert_budget_available` (T-023 §4.2). DPs are composed but explanations are blank or have placeholder text (per T-023 §10.9 — the locked "AI-uitleg budget bereikt voor deze maand" Dutch fallback is NOT actually rendered anywhere). User sees DPs without LLM paraphrase.
6. **API parallel chain at 06:30 wrote partial state** — at 07:00, the worker DP composer may see a half-written `decision_packages` row and either crash or overwrite. No defined coordination. §5.4.
7. **Both fires consume LLM cost** — monthly budget exhausted by mid-month if both fires call Anthropic. §5.4.

## 8. Phase 1c surface (12 findings)

1. **`_relabel_morning_briefing` depends on wall-clock reliability** — clock skew or `brussels_hour_provider` override breaks the morning_briefing identity. Forecasting + DP + AI explanation all gate on exact-equality.
2. **No catch-up fire for missed 07:00** — worker crash + restart = lost morning briefing for the day. Worse than 06:00 because users actively expect this fire.
3. **Forecasting / DP exceptions cascade silently** — failure produces empty payload slots; user sees stale data with no system-health signal.
4. **Only 1 of 7 predictors wired** (ADR-0003 6th re-confirmation via T-024) — at 07:00, the entire ensemble decision rests on `historical_bootstrap_v1`.
5. **AI explanation cost lives outside the audit payload** — cross-referencing `worker_run_audit` + `claude_ai_budget_usage` by timestamp is the only attribution path.
6. **Dual-scheduler doctrine drift — DOMINANT FINDING** (§5.1-§5.5) — worker fires the morning chain at fixed 07:00 (Brussels); API has its own parallel scheduler at config-driven cron (default 06:30). Both write to the same storage tables. No coordination contract. No idempotency key shared.
7. **`SCHEDULER_DAILY_BRIEFING_CRON` is read by both schedulers but only honored by API** — operators changing the config believe they're shifting "the morning chain" but only shift the API one.
8. **API morning chain has 6 named legs** vs worker's 5 sub-steps — different decomposition of the same conceptual flow.
9. **Both chains consume LLM cost** — if both enabled, monthly EUR budget exhausts ~2× faster than intent §4 anticipates.
10. **No race-condition handling at storage layer** — `decision_packages` UPSERT pattern means last-writer-wins; the 07:00 fire silently overwrites the 06:30 fire's outputs (or vice versa).
11. **`mode_detected="awaiting_watchlist_confirmation"` short-circuits** — day-1 user wakes up to yesterday's dashboard (or empty) with no fresh briefing; T-025 cold-start completion required to unblock.
12. **AI explanation budget-exhaustion has no Dutch fallback rendered** (T-023 §10.9 carry-over) — if at 07:00 the budget is exhausted, DPs render with empty/placeholder explanation. User has no signal.

## 9. Out of scope (re-confirmed)

- **Calibration sub-step** (T-016 — merged sibling; pre_briefing only).
- **DP composer mechanics** (T-017 — merged sibling).
- **Forecasting deep dive** (T-015 — merged sibling).
- **AI explanation deep dive** (T-023 — merged sibling).
- **06:00 pre_briefing fire** (T-031 — merged sibling).
- **08:00-21:00 hourly_delta fires** (T-033 — future task).
- **API morning chain leg-by-leg deep dive** — T-032 surfaces the existence + drift; deep documentation of the API chain is future work.

## 10. References

- `apps/worker/src/portfolio_outlook_worker/scheduler.py:151-158` (cron registration), `:204` (`_on_hourly` handler)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:167-180` (`_relabel_morning_briefing`)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:238` (relabel call site)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:312-330` (market-data gate — runs both 06:00 + 07:00)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:332-347` (forecasting gate — 07:00 only)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:348-370` (DP composition gate — 07:00 only)
- `apps/api/src/portfolio_outlook_api/morning_chain.py:1-365` (PARALLEL API morning chain with 6 legs)
- `apps/api/src/portfolio_outlook_api/morning_chain.py:128` (`run_morning_chain`)
- `apps/api/src/portfolio_outlook_api/morning_chain.py:176` (`build_scheduler_chain_callable`)
- `apps/api/src/portfolio_outlook_api/scheduler.py:107` (`run_daily_briefing_job`)
- `apps/api/src/portfolio_outlook_api/scheduler.py:236-257` (API APScheduler registration consuming `scheduler_daily_briefing_cron`)
- `apps/api/src/portfolio_outlook_api/status_routes.py:3067` (`POST /scheduler/runs/morning-chain` manual trigger)
- `docs/reality/workflows/morning-chain-orchestration.md` (T-011)
- `docs/reality/workflows/forecast-generation-and-labelling.md` (T-015)
- `docs/reality/workflows/decision-package-composition.md` (T-017)
- `docs/reality/workflows/ai-explanation-and-budget.md` (T-023)
- `docs/reality/workflows/system-morning-pre-briefing-06-00.md` (T-031)
- `docs/reality/workflows/predictor-backtest-and-leaderboard.md` (T-024 — ADR-0003 1-of-7 predictors)
