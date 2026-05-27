# Reality — workflow: morning-chain orchestration

**Scope.** End-to-end trace of the worker's morning chain — the 06:00 Brussels pre-briefing fire and the 07:00 Brussels morning-briefing fire (relabelled from the first hourly-delta cron) — from APScheduler trigger to Decision Package persistence.

This doc is a **synthesis** of three T-007 reality docs and one T-006 surface; every claim is cross-referenced rather than re-cited from source. For per-module detail, follow the links.

Source-of-truth reality docs (read these first if you need module-level detail):

- `docs/reality/components/worker-orchestration-and-scheduling.md` — scheduler, lock, orchestrator, IBKR gateway, starter watchlist, storage readiness.
- `docs/reality/components/worker-forecasting-and-decision-package.md` — universe resolver, calibration, forecasting step, historical bootstrap, label translator, market-data step, EODHD, Decision Package composer + orchestration.
- `docs/reality/components/worker-actions-and-reconciliation.md` — what runs **outside** the morning chain (submission sweep, reconciler) — explicit out-of-scope.
- `docs/reality/components/api-infrastructure-and-ai.md` §11 — the Anthropic Claude provider + monthly EUR budget cap that the explanation step calls into.

## 0. TL;DR — what happens each morning

At 06:30 CET/CEST (Brussels) two scheduled fires happen in sequence:

1. **06:00 — pre_briefing**: market-data sync (yesterday's EODHD EOD + FX) → calibration step (evaluate yesterday's expired forecasts against realised closes).
2. **07:00 — morning_briefing** (the first hourly_delta cron, relabelled): market-data sync again → forecasting step (run historical bootstrap per asset in the union of confirmed watchlist + held positions) → Decision Package composition → AI explanation (Anthropic Claude, gated by monthly EUR cap) → daily briefing.

The action-draft composer is a pure-function library that the API calls when the user actions a Decision Package. **Action drafts are not part of the morning chain.** Likewise, IBKR submission sweep and the three reconciliation passes are wired into APScheduler **separately** (per `worker-actions-and-reconciliation.md` §§6, 8) and tick on their own cadence.

The whole chain is single-flight-locked (Postgres `pg_advisory_lock`) so two worker processes never collide. Every fire writes one `ScheduledRunAuditEntry` row.

## 1. Triggers — APScheduler

Per `worker-orchestration-and-scheduling.md` §4, the V1 daily-briefing scheduler registers exactly three APScheduler jobs:

| Job | Trigger | Schedule (Europe/Brussels) | job_id | Target callable |
|---|---|---|---|---|
| **Pre-briefing** | `cron` | `hour=6, minute=0` | `"pre_briefing"` | `_on_pre_briefing` → `run_orchestrator(run_type="pre_briefing")` |
| **Hourly delta** | `cron` | `hour="7-21", minute=0` | `"hourly"` | `_on_hourly` → `run_orchestrator(run_type="hourly_delta")` |
| Heartbeat | `interval` | `seconds=60` (default) | `"heartbeat"` | `_heartbeat` (state upsert only) |

The cron timezone `Europe/Brussels` is locked at `apps/worker/src/portfolio_outlook_worker/config.py:64` (default `"Europe/Brussels"`). The `SCHEDULER_DAILY_BRIEFING_CRON` config default is `"30 6 * * *"` but the in-code job definition pins `hour=6, minute=0` for pre_briefing and `hour="7-21", minute=0` for hourly_delta (see `scheduler.py:141-149` + `:150-158` cited via `worker-orchestration-and-scheduling.md` §4).

**Run-type relabel at 07:00**: `worker-orchestration-and-scheduling.md` §6 step 3 documents that the orchestrator relabels `run_type="hourly_delta"` → `"morning_briefing"` when `brussels_hour_provider()` returns `7`. The hourly_delta cron at 07:00 therefore becomes the morning_briefing fire; subsequent hourly fires (08:00-21:00) stay `hourly_delta`.

## 2. Step 0 — per-fire setup (`scheduler.py` → `run_orchestrator`)

Per `worker-orchestration-and-scheduling.md` §4 + §6:

1. APScheduler invokes the fire wrapper `_run()` (`scheduler.py:207-237`).
2. `_run` opens `StorageConnectionProvider.checked_connection(require_writable=True)` (`scheduler.py:217`). If storage is disabled the fire logs + exits early without invoking the orchestrator.
3. Inside the checked connection: builds `_PositionSnapshotCounts(connection)` + `PostgresAdvisoryLock(connection)` + calls `run_orchestrator(... lock=lock, ...)` (`scheduler.py:221-235`).
4. The orchestrator owns the single-flight lock + audit-row writes from this point forward.

## 3. Step 1 — single-flight lock

Per `worker-orchestration-and-scheduling.md` §5, the orchestrator's **first action** (`orchestrator.py:212`) is `if not lock.try_acquire()`. On failure: writes `mode_detected="skipped_locked"`, `outcome="completed"` audit row and returns immediately (no lock held → no release needed).

Lock semantics:

- Postgres session-scoped (`pg_try_advisory_lock(0x504F5F4F5243484F)`).
- Two worker processes on the same DB serialise their fires.
- The orchestrator + the lock share **one** SQLAlchemy `Connection` for the duration of one fire.

## 4. Step 2 — connectivity + mode detection

Per `worker-orchestration-and-scheduling.md` §6 control flow:

1. **Run-type relabel** at the top: if `brussels_hour_provider() == 7` and current `run_type == "hourly_delta"`, relabel to `"morning_briefing"` (`orchestrator.py:237-240`).
2. **Gateway probe** (`orchestrator.py:242-266`): if `gateway.is_connected()` is `False` → `mode_detected="disconnected"`, `outcome="completed"`, write audit, **return**. Any subsequent step is skipped.
3. **Cold-start detection** (`orchestrator.py:268-282`): `ibkr_account_id is None` → `"cold_start"`. Else read `position_count` + `watchlist_count` from `_PositionSnapshotCounts`; both zero → `"cold_start"`, else `"normal"`.
4. **Starter-seed trigger** (`orchestrator.py:283-294`): if `mode_detected == "cold_start"` and a `seed_runner` is wired, calls `seed_runner.seed(ibkr_account_id)`. (Production wiring of the seed runner is not yet present per `worker-orchestration-and-scheduling.md` §9 — flagged as a follow-up integration.)
5. **Confirmation-state override** (`orchestrator.py:296-310`): if confirmation state is `"unconfirmed"` and `mode_detected != "cold_start"`, override to `"awaiting_watchlist_confirmation"`.

### The 6 `mode_detected` literal values

Per `worker-orchestration-and-scheduling.md` §6:

| Literal | File:line declaration | When emitted |
|---|---|---|
| `"cold_start"` | `orchestrator.py:52` | `ibkr_account_id` is `None` OR position + watchlist counts both zero |
| `"normal"` | `orchestrator.py:53` | Account known and either positions or watchlist non-empty |
| `"disconnected"` | `orchestrator.py:54` | `gateway.is_connected()` returns False (or top-level exception) |
| `"skipped_locked"` | `orchestrator.py:55` | Single-flight lock already held |
| `"skipped_disabled"` | `orchestrator.py:56` | Declared but **never written** by `run_orchestrator` |
| `"awaiting_watchlist_confirmation"` | `orchestrator.py:58` | Task 128 — confirmation state is `"unconfirmed"` |

The morning chain's **productive** modes are `"normal"` and (in the cold-start week) `"cold_start"`. The other four are skip/error paths.

## 5. Step 3 — market-data step (`market_data_step.py`)

**Gate** (`orchestrator.py:312-330`): fires only when `market_data_runner is not None` AND `mode_detected == "normal"` AND `run_type in ("pre_briefing", "morning_briefing")` AND `ibkr_account_id is not None`. Hourly_delta runs at 08:00–21:00 skip this step entirely — EOD prices don't change intraday (see `worker-forecasting-and-decision-package.md` §7).

Per `worker-forecasting-and-decision-package.md` §7:

- Entry: `fetch_market_data_for_account(*, ibkr_account_id, asset_universe, snapshot_repo, fx_rate_repo, eodhd_client, target_date, now_provider, base_currency="EUR")` (`market_data_step.py:92-103`).
- Storage writes:
  - `MarketDataEodSnapshotEntry` rows into `market_data_eod_snapshot` table (`market_data_step.py:166-185`). Idempotent on `(ibkr_conid, as_of_date, provider)` (`:129-135`).
  - `FxRateRecord` upserts into `fx_rates` table (`market_data_step.py:245-254`). Idempotent on `(base, quote, as_of_date, provider)` (`:209-216`).
- Provider: EODHD only — `fetch_eod` (`market_data_step.py:138-143`) + `fetch_fx` (`:219-222`). No fundamentals / splits / dividends despite ADR 0003's "All-In-One" intent.
- Returns `MarketDataFetchResult(snapshots_attempted, snapshots_succeeded, snapshots_failed, fx_rates_attempted, fx_rates_succeeded, fx_rates_failed)` via `.as_audit_dict()`.
- **Never raises** (per `market_data_step.py:13-15`): every failed fetch is logged + counted, not propagated.

The orchestrator folds the result dict into the audit payload under key `"market_data"` (`orchestrator.py:388-395`). On exception, sets `market_data_details = {"error": "market_data_runner_exception"}` (`orchestrator.py:328-330`).

## 6. Step 4 — forecasting step (`forecasting_step.py`)

**Gate** (`orchestrator.py:332-346`): fires only when `forecasting_runner is not None` AND `mode_detected == "normal"` AND `run_type == "morning_briefing"` AND `ibkr_account_id is not None`. **Pre_briefing skips this step.** Forecasts are written exactly once per morning, at 07:00.

Per `worker-forecasting-and-decision-package.md` §4:

- Entry: `run_forecasting_step(*, ibkr_account_id, watchlist_provider, position_provider, close_provider, forecast_repo, scheduled_run_id, now_provider, rng_seed, history_window_days=252, horizon_days=20, num_resamples=10_000, block_size=5, override_conids=None)` (`forecasting_step.py:124-140`).
- **Single-predictor reality**: only `historical_bootstrap_v1` is wired. ADR 0003 locks seven predictors + weighted-average ensemble (`docs/decisions/0003-forecast-engine-architecture.md:25-27`) — the gap is documented in `worker-forecasting-and-decision-package.md` §1.
- Per-asset flow (one `_forecast_single_asset` call per resolved-universe `conid`):
  1. Load closes from `close_provider`.
  2. Stale check (3-day threshold) → `"stale_market_data"` block reason.
  3. History check (< 200 closes) → `"insufficient_history"`.
  4. Run `compute_historical_bootstrap_forecast(...)` (`forecasting_step.py:278-285`).
  5. Excessive volatility (> 1.00 annualised) → `"excessive_volatility"`.
  6. Compute freshness + confidence + label (see step 6b below).
  7. Persist `ForecastEntry(forecast_run_id=f"fcst_{uuid4().hex}", ..., method="historical_bootstrap_v1", forecast_valid_until=now + horizon_days*1.4)` via `forecast_repo.append(entry)` (`:341-366`).
- Blocked rows are still persisted as a placeholder `ForecastEntry` with `label="Geblokkeerd"`, `confidence_level="Laag"`, zero quantiles (`forecasting_step.py:385-438`).
- Returns `ForecastingStepResult(total_attempted, succeeded, blocked_by_reason, per_conid, wall_clock_ms, persistence_failures)`.

The orchestrator folds the result dict into the audit payload under key `"forecast"`. On exception, sets `forecast_details = {"error": "forecasting_runner_exception"}` (`orchestrator.py:344-346`).

### 6a. Asset universe resolver

Called as the first step inside `run_forecasting_step` (`forecasting_step.py:143-148`). Per `worker-forecasting-and-decision-package.md` §2:

- **Not** a `universe_set` selector (no `SP500 / EU600 / ALL_5K`).
- Resolves the union of (confirmed watchlist for `ibkr_account_id`) + (held positions with `quantity > 0`).
- Optional `override_conids` env channel (`FORECAST_OVERRIDE_CONIDS`) bypasses both providers.
- Output: tuple of `ConidWithContext(conid, symbol, source, held_quantity, user_holds_position)` where `source ∈ {"watchlist", "position", "both", "override"}`.

### 6b. Label translator + confidence

Per `worker-forecasting-and-decision-package.md` §6:

- **6 locked Dutch labels** (not 8): `Kopen`, `Verminderen`, `Verkopen`, `Houden`, `Bekijken`, `Geblokkeerd`.
- Threshold table: Kopen requires `prob_positive ≥ 0.65 AND p50_log_return > 0 AND prob_loss_gt_5pct ≤ 0.15`. Verkopen requires `prob_positive ≤ 0.25 AND prob_loss_gt_5pct ≥ 0.40 AND user_holds`. Etc.
- Block reasons trump label rules (`label_translator.py:75-92`): `data_stale`, `data_unavailable`, `insufficient_history`, `implausible_volatility`.
- Confidence (`label_translator.py:121-142`): `Hoog` requires ≥252 closes + zero gaps + vol ≤ 0.30; `Gemiddeld` requires ≥200 closes + gaps ≤ 2; else `Laag`. **Note: `gaps_in_last_60_days=0` is hard-coded at `forecasting_step.py:331`** — the gap-aware path never fires today.

## 7. Step 5 — Decision Package composition (`decision_package/orchestration.py`)

**Gate** (`orchestrator.py:348-370`): fires only when `decision_package_runner is not None` AND `forecast_details is not None` AND `"error" not in forecast_details` AND `mode_detected == "normal"` AND `run_type == "morning_briefing"` AND `ibkr_account_id is not None`. **Gated on forecasting success** — a forecasting-step failure aborts DP composition for the same run.

Per `worker-forecasting-and-decision-package.md` §11:

- Entry: `compose_and_persist_for_run(*, ibkr_account_id, scheduled_run_id, forecast_source, context_provider, decision_package_repo, now_provider)` (`orchestration.py:93-101`).
- Per-asset iteration (`:119-188`):
  1. Skip `Geblokkeerd` forecasts (`:120-122`).
  2. Fetch market snapshot, FX rate (only if non-EUR), asset listing, current position from `context_provider`.
  3. Fetch previous Decision Package via `decision_package_repo.get_latest_for_account_conid(...)` — chain anchor for `previous_package_hash`.
  4. Call `compose_decision_package(...)` (the pure-function composer in `decision_package/composer.py`).
  5. Persist via `decision_package_repo.append(package)`.
- The composer (`composer.py`, 572 lines) is documented in `worker-forecasting-and-decision-package.md` §9 — Decimal-end-to-end, deterministic Dutch explanation template (no AI), SHA-256 content-addressed hash (excluding `composed_at` + `decision_package_id`), hash chain via `previous_package_hash`.
- Returns `DecisionPackageCompositionResult(forecasts_seen, composed, skipped_geblokkeerd, missing_context, composition_errors, persisted_ids)`.

The orchestrator folds the result under audit key `"decision_package"`. On exception, sets `{"error": "decision_package_runner_exception"}` (`orchestrator.py:366-370`).

## 8. Step 6 — Calibration step (`calibration_step.py`)

**Gate** (`orchestrator.py:372-383`): fires only when `calibration_runner is not None` AND `mode_detected == "normal"` AND `run_type == "pre_briefing"`. **Morning_briefing skips this step** — calibration only runs at 06:00. (The pre_briefing fire is precisely for this and for the market-data refresh.)

Per `worker-forecasting-and-decision-package.md` §3:

- Entry: `run_calibration_step(*, forecast_repo, diary_repo, realized_close_provider, now_provider, max_to_evaluate=100)` (`calibration_step.py:74-81`).
- For each forecast whose `forecast_valid_until` is in the past AND `expired_at` is NULL:
  1. Look up realised close on the target date.
  2. Compute `realized_log_return = ln(close / current_price)` quantised to 10 dp.
  3. Decide `hit_status` from the locked p10/p90 band (4 cases: `realized_above_p90`, `realized_below_p10`, `realized_within_p10_p90`, `realized_outside_band`).
  4. Append `CalibrationDiaryEntry` row.
  5. Mark forecast row `expired_at` to prevent re-evaluation.
- Returns `CalibrationStepResult(forecasts_evaluated, diary_rows_written, per_forecast)`.

The orchestrator folds the result under audit key `"calibration"`.

## 9. Step 7 — daily briefing + AI explanation (downstream of the orchestrator)

**Important**: per `worker-orchestration-and-scheduling.md` §6.5, the orchestrator **stops after Decision Package composition**. The daily briefing + AI explanation are NOT invoked from `run_orchestrator`.

Per `api-infrastructure-and-ai.md` §11:

- The Anthropic Claude explanation provider (`apps/api/src/portfolio_outlook_api/anthropic_explanation_provider.py`) is called by **`ai_explanation_sync.generate_explanation`** in the API tier, not the worker.
- The morning-chain Decision Package rows persisted by Step 5 above sit in the DB; the API's daily-briefing endpoint at `POST /briefings/daily/compute` (T-005 + T-006) drives the explanation step on demand.
- Budget cap: `claude_ai_budget_monthly_eur` default `Decimal("50")`; pre-call `assert_budget_available` + post-call `persist_call_cost`.

**This split is a Phase 1c observation**: the morning-chain doctrine implies daily briefings + AI explanations are part of the 07:00 sequence, but the actual wiring requires an external API trigger. A future Phase 4 task could wire `daily_briefing_runner` and `ai_explanation_runner` into the orchestrator's gate list following the pattern of `market_data_runner` / `forecasting_runner` / `decision_package_runner`.

## 10. Step 8 — audit-row write + lock release

Per `worker-orchestration-and-scheduling.md` §6 control flow steps 12–14:

1. **Audit-payload assembly** (`orchestrator.py:385-413`): folds the four runner result dicts under keys `"market_data"`, `"forecast"`, `"decision_package"`, `"calibration"` into a single `error_details_json` payload (despite the name, this is also used for the success-path detail). Writes one `ScheduledRunAuditEntry` via `_safe_append(audit_repo, ...)` with:
   - `run_id = f"srun_{uuid4().hex}"`
   - `run_type` (pre_briefing / morning_briefing / hourly_delta)
   - `mode_detected` (one of the 6 literals)
   - `outcome = "completed"` (or `"error"` — see step 13)
   - `duration_ms` (monotonic-clock measured)
   - `next_scheduled_at` (optional)
2. **Top-level exception handler** (`orchestrator.py:421-446`): if anything in the body raised, writes a separate `ScheduledRunAuditEntry` with `mode_detected="disconnected"`, `outcome="error"`, `error_details_json={"reason": "orchestrator_exception", "message": str(exc)}`.
3. **Lock release** in `finally` (`orchestrator.py:447-448`): `lock.release()` runs whether the body succeeded or raised. The `skipped_locked` early-return at step 2 bypasses this (no lock held).

`_safe_append` (`orchestrator.py:455-469`) catches all storage exceptions and logs — **never re-raises**. Per the docstring: "the only honest move is to log the failure and move on. APScheduler's next fire will try again."

## 11. Outcome ↔ mode matrix

Per `worker-orchestration-and-scheduling.md` §6 outcome table:

| `mode_detected` | `outcome` | File:line | Productive? |
|---|---|---|---|
| `skipped_locked` | `completed` | `orchestrator.py:213-233` | no |
| `disconnected` (gateway down) | `completed` | `orchestrator.py:244-266` | no |
| `cold_start` | `completed` | `orchestrator.py:400-413` | yes (with seed_runner wired) |
| `awaiting_watchlist_confirmation` | `completed` | `orchestrator.py:400-413` | no (waiting on user) |
| `normal` | `completed` | `orchestrator.py:400-413` | **yes — full morning chain** |
| `disconnected` (top-level exception) | `error` | `orchestrator.py:424-446` | no |

Only `"normal"` + `run_type == "morning_briefing"` runs the full 5-step chain. `"normal"` + `"pre_briefing"` runs the 2-step pre-chain (market-data + calibration). All other combinations skip steps 3-7 entirely.

## 12. Side effects (audit rows written per fire)

Per `worker-forecasting-and-decision-package.md` + `api-infrastructure-and-ai.md`, a successful normal-mode `morning_briefing` fire writes:

| Table | Repository | Rows | Where |
|---|---|---|---|
| `scheduled_run_audit` | `SqlAlchemyScheduledRunAuditRepository` | exactly 1 per fire | `orchestrator.py:400-413` |
| `market_data_eod_snapshot` | `SqlAlchemyMarketDataEodSnapshotRepository` | one per resolved-universe asset (idempotent) | `market_data_step.py:166-185` |
| `fx_rates` | `SqlAlchemyFxRateRepository` | one per `(non-EUR-currency → EUR)` (idempotent) | `market_data_step.py:245-254` |
| `forecasts` (or whatever the actual table name is per T-003) | `SqlAlchemyForecastRepository` | one per resolved-universe asset (incl. `Geblokkeerd` placeholders) | `forecasting_step.py:341-366, :385-438` |
| `decision_packages` | `SqlAlchemyDecisionPackageRepository` | one per non-`Geblokkeerd` forecast | `decision_package/orchestration.py:179-181` |

A `pre_briefing` fire additionally writes:

| Table | Repository | Rows | Where |
|---|---|---|---|
| `calibration_diary` | `SqlAlchemyCalibrationDiaryRepository` | one per evaluated expired forecast (cap = 100) | `calibration_step.py:145-154` |

Plus per-forecast `forecast_repo.mark_expired(forecast_run_id, expired_at)` writes (`calibration_step.py:155-157`).

`ClaudeAiBudgetUsageRecord` rows (Anthropic spend tracking, per `api-infrastructure-and-ai.md` §11e) are written by the API tier when the daily-briefing endpoint is later invoked — **not** by the worker's morning-chain fire.

## 13. Failure paths

The orchestrator's "never raises" contract (`orchestrator.py:203-204`) means every failure lands in an audit row, not a process crash:

| Failure | Surface | Audit row |
|---|---|---|
| Storage disabled at fire time | scheduler `_run` logs + exits early; orchestrator not invoked | none written (no orchestrator audit row) |
| `StorageConnectionError` on connection acquisition | scheduler logs `StorageConnectionError` | none written |
| Lock held by another worker | orchestrator early-return | `mode_detected="skipped_locked"`, `outcome="completed"` |
| Gateway disconnected | orchestrator early-return after gateway probe | `mode_detected="disconnected"`, `outcome="completed"` |
| Per-step runner raised | per-step `try/except` folds `{"error": "<name>_exception"}` into audit payload | `mode_detected="normal"` (preserved), `outcome="completed"`, error nested in `error_details_json` |
| Top-level exception | bare `except Exception` (`orchestrator.py:421-446`) | `mode_detected="disconnected"`, `outcome="error"` |
| `_safe_append` storage write failure | logged inside `_safe_append`; no re-raise | audit row **dropped**, fire completes successfully (APScheduler's next fire will try again) |

The "audit-row dropped" path is the only morning-chain failure mode that produces zero observable signal — by design (`orchestrator.py:459-464`). The next fire will produce its own audit row, so the gap is bounded to one fire (1 hour for hourly_delta, 24 hours for pre_briefing/morning_briefing).

## 14. Explicit out-of-scope — what the morning chain does NOT do

Per `worker-actions-and-reconciliation.md` §§6, 8 + `worker-orchestration-and-scheduling.md` §6.5:

- **Action draft composition** — pure-function library; called by the API tier (`apps/api/.../action_draft.py`) when the user actions a Decision Package via `POST /action-drafts/compute`. The orchestrator never calls the action-draft composer.
- **IBKR order submission** — the submission sweep (`apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py`) registers its **own** APScheduler job and ticks independently. FIFO by `user_approved_at`, one `place_order` per tick (per `worker-actions-and-reconciliation.md` §6).
- **IBKR reconciliation** — the reconciler (`apps/worker/.../ibkr_reconciliation/reconciler.py`) registers its **own** APScheduler job and runs the 3-pass sequence per tick (per `worker-actions-and-reconciliation.md` §8).
- **AI explanation generation** — runs in the API tier on-demand, not in the worker's morning fire (see §9 above).
- **Cold-start starter-watchlist seed** — wired into the orchestrator's `seed_runner` slot in spec (`orchestrator.py:283-294`) but **not yet wired into the production seed_runner** per `worker-orchestration-and-scheduling.md` §9.

## 15. Cross-cutting observations + Phase 1c surface

- **The orchestrator stops after Decision Package composition.** Daily briefing + AI explanation require external API triggers. Phase 1c surface: should the morning chain reach all the way through to a persisted daily briefing, or is the current split (worker → DP, API → briefing+explanation) the desired contract?
- **The 7-predictor ensemble doesn't exist.** ADR 0003 locks seven predictors; the worker ships one (`historical_bootstrap_v1`). Phase 1c surface: T-046 gap analysis carries this forward.
- **The 6-vs-8-label vocabulary**: `worker-forecasting-and-decision-package.md` §6 locks 6 Dutch labels (`Kopen / Verminderen / Verkopen / Houden / Bekijken / Geblokkeerd`). The `Sterk dalend … Sterk stijgend` 8-bucket vocabulary the original brainstorm assumed does not exist in code.
- **`gaps_in_last_60_days=0`** is hard-coded at `forecasting_step.py:331` — the confidence deriver's gap-aware path cannot fire today. Phase 4 candidate.
- **Audit row gap on storage write failure** — the orchestrator's "never raises" contract trades off observability against process robustness. Phase 1c surface: should `_safe_append` storage failures be retried, queued, or surfaced via a separate system_event?
- **Single-flight lock + APScheduler timing**: the heartbeat job (60 s interval) holds the connection while the cron jobs hold the advisory lock. Two cron fires can never run concurrently, but a long-running fire can starve the heartbeat. Phase 4 surface: should the heartbeat use a separate short-lived connection?
- **Brussels timezone is locked**: all three jobs run on `Europe/Brussels` regardless of operator location. DST transitions move the chain one hour earlier/later in UTC twice a year — observable in the `scheduled_run_audit.run_at` UTC timestamps.

## 16. References

- `docs/reality/components/worker-orchestration-and-scheduling.md` — orchestrator + scheduler + lock + IBKR gateway + storage readiness + starter watchlist (T-007).
- `docs/reality/components/worker-forecasting-and-decision-package.md` — universe resolver + calibration + forecasting + bootstrap + label translator + market-data + EODHD + DP composer + Dutch template + DP orchestration (T-007).
- `docs/reality/components/worker-actions-and-reconciliation.md` — explicit out-of-scope for this workflow (action drafts + submission sweep + reconciliation) (T-007).
- `docs/reality/components/api-infrastructure-and-ai.md` §11 — Anthropic Claude explanation surface called by the API tier downstream of the morning chain (T-006).
- `docs/decisions/0003-forecast-engine-architecture.md` — locked forecast-engine intent.
- `docs/ai-policy.md` — locked AI-as-Case-C policy (intent for §9).
