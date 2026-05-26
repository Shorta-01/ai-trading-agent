# Reality — worker actions and reconciliation

**Scope.** The worker's action-draft + IBKR submission + reconciliation surface: the action-draft composer, the supersede check, the five-module `ibkr_submission/` cluster (lifecycle handler, order builder, safety re-check, submission sweep, submitter), and the four-module `ibkr_reconciliation/` cluster (orchestrator + three passes).

Sibling docs cover the rest of the worker:

- `docs/reality/components/worker-orchestration-and-scheduling.md` — entry point, settings, scheduler, single-flight lock, IBKR gateway, storage readiness, starter watchlist.
- `docs/reality/components/worker-forecasting-and-decision-package.md` — universe resolver, calibration, forecasting step, historical bootstrap, label translator, market-data step, EODHD provider, decision-package composer + orchestration.

## In-scope modules

All paths under `apps/worker/src/portfolio_outlook_worker/`.

| Module | Role |
|---|---|
| `action_draft/composer.py` (525 lines) | pure function — `compose_action_draft_from_decision_package` + `compose_action_draft_user_supplied` |
| `action_draft/supersede_check.py` (146 lines) | flag (not mutate) pending drafts when a newer Decision Package arrives |
| `ibkr_submission/lifecycle_handler.py` (532 lines) | IBKR `Trade.*Event` callbacks — write state transitions + execution audit rows |
| `ibkr_submission/order_builder.py` (146 lines) | `ActionDraftRecord` → `ibapi.Order` translation; the worker-side Decimal→float boundary |
| `ibkr_submission/safety_recheck.py` (392 lines) | the locked Tier-1 pre-`place_order` gates (12 in order) |
| `ibkr_submission/submission_sweep.py` (475 lines) | APScheduler tick driver — locked one-`place_order`-per-tick |
| `ibkr_submission/submitter.py` (369 lines) | **the single `place_order(...)` authority in the worker** |
| `ibkr_reconciliation/reconciler.py` (378 lines) | orchestrator + run-audit + lock + connection gate |
| `ibkr_reconciliation/pass_a_orphaned_executions.py` (418 lines) | IBKR-side executions with no local match |
| `ibkr_reconciliation/pass_b_stale_in_flight.py` (443 lines) | in-flight drafts that may have terminalised at IBKR |
| `ibkr_reconciliation/pass_c_timeout_recovery.py` (180 lines) | `awaiting_reply_timeout` drafts past the 24 h cutoff |

## 1. Action-draft composer (`action_draft/composer.py`)

### Entry points

- `compose_action_draft_from_decision_package(...)` (`composer.py:91-266`).
- `compose_action_draft_user_supplied(...)` (`composer.py:269-394`) — Volglijst quick-action path when no Decision Package exists (`:288-298`).

### Sizing — confidence-tier percentage caps, no Kelly

The composer does **not** use Kelly fractions. Sizing is cash-aware percentage-of-portfolio:

| Constant | Value | File:line |
|---|---|---|
| `_BUY_TARGET_PCT_BY_CONFIDENCE["Hoog"]` | `Decimal("0.08")` (8% of portfolio) | `composer.py:50-56` |
| `_BUY_TARGET_PCT_BY_CONFIDENCE["Gemiddeld"]` | `Decimal("0.04")` (4% of portfolio) | `composer.py:50-56` |
| `_SELL_VERMINDEREN_FRACTION` | `Decimal("0.25")` (25% of held quantity) | `composer.py:57` |
| Verkopen behaviour | Exits the entire held position | `composer.py:463-464` |
| `_LIMIT_PRICE_BIAS_BPS` | `Decimal("0.002")` (2 bps) | `composer.py:43` |
| `_QUANTITY_QUANTUM` | `Decimal("1")` (whole shares only) | `composer.py:44` |
| `_PRICE_QUANTUM` | `Decimal("0.00000001")` | `composer.py:45` |
| `_NOTIONAL_QUANTUM` | `Decimal("0.00000001")` | `composer.py:46` |

`"Laag"` confidence is intentionally absent from `_BUY_TARGET_PCT_BY_CONFIDENCE` — filtered upstream by Decision Package gates (`composer.py:53-55`).

Limit-price bias (`composer.py:397-411`): BUY = close × (1 − 0.002); SELL = close × (1 + 0.002).

Cash-aware sizing math (`composer.py:164-176`):

```
usable_cash_eur = max(0, available_funds_eur − approved_drafts_notional_eur − user_buffer_eur)
portfolio_total = portfolio_total_eur or available_funds_eur   # if not supplied
```

BUY helper `_compute_buy_quantity` (`composer.py:427-455`): `target_at_pct_eur = portfolio_total × target_pct`; `target_eur = min(target_at_pct_eur, usable_cash_eur)`; convert via FX; floor on share count.

SELL helper `_compute_sell_quantity` (`composer.py:458-470`).

### Output record `ActionDraftEntry`

Built at `composer.py:234-266` (decision-package path) and `composer.py:362-394` (user-supplied path). Key fields:

- `action_draft_id = f"adraft_{uuid4().hex}"` (`composer.py:212`).
- `decision_package_id` / `forecast_run_id` — both `None` in user-supplied path (`:236-237, :364-365`).
- `created_by="user"` (`:239, :367`).
- `ibkr_account_id`, `conid`, `symbol` (`"UNKNOWN"` fallback at `:230-232`), `exchange`, `currency_local`.
- `side` ∈ `{BUY, SELL}` (`:146, :300-301`).
- `quantity`, `order_type="LMT"` (`:247, :375`), `limit_price_local`, `time_in_force="DAY"` (`:249, :377`).
- `notional_local`, `notional_eur` (`:206-209, :338-341`).
- `fx_rate_at_creation`, `usable_cash_eur_at_creation`, `held_quantity_at_creation`.
- **`status="proposed"`** at composition (`:255, :383`) — **NOT** `user_approved`, **NOT** `pending`. The user must explicitly approve, which is a separate UI-driven transition (see §13).
- `superseded_by_decision_package_id=None`.
- `audit_trail_hash` — SHA-256 over canonical JSON (`:214-228, :346-360`); algorithm in `_compute_audit_trail_hash` (`:479-525`). `created_at` is excluded from the hash so it stays reproducible in tests (`:495-501`).
- `previous_draft_hash` — chain link.
- **`safe_for_submission=False`** at composition — hard-False per doctrine at `composer.py:21-24`: "Task 134 (real submission) is the only code path allowed to flip it conditionally" (`:265, :393`).

### Storage / dry-run

The composer is a **pure function** — it returns an `ActionDraftEntry` but does NOT itself write to storage. The caller persists into `action_drafts`. There is **no `run_dry_run_safety_checks` call** in the worker composer or anywhere under `apps/worker/src/portfolio_outlook_worker/` — that helper lives in the `portfolio` package and is invoked by the API path. The worker composer relies on the IBKR sweep's safety re-check (see §5) as the Tier-1 pre-`place_order` guard.

### Draftable labels

`_DRAFTABLE_LABELS = frozenset({"Kopen", "Verminderen", "Verkopen"})` (`composer.py:88`). `Houden` / `Bekijken` raise `UnsupportedDecisionPackageLabelError` (`:79-85`).

Exceptions: `InsufficientCashError` (`:60-72`), `NoPositionToSellError` (`:75-76`).

## 2. Supersede check (`action_draft/supersede_check.py`)

"Flag, never modify" doctrine (`supersede_check.py:1-15`). When a newer Decision Package arrives for the same `(ibkr_account_id, conid)` that already has a pending draft (`proposed` or `edited`), the draft is **not** mutated — only its `superseded_by_decision_package_id` flag is set so the UI renders the "Advies gewijzigd" badge (`:4-10`).

### Entry point

`mark_superseded_drafts(...)` (`supersede_check.py:65-145`).

### Algorithm

Loop Decision Packages × pending drafts (`supersede_check.py:93-138`):

- If `draft.decision_package_id == package.decision_package_id` → skip (same package) (`:109-113`).
- If `draft.superseded_by_decision_package_id == package.decision_package_id` → skip (idempotent re-mark) (`:114-119`).
- Else call `action_draft_repo.mark_superseded(action_draft_id, by_decision_package_id, marked_at)` (`:120-127`).

### Storage

- Reads: `action_draft_repo.list_pending_for_conid(ibkr_account_id, conid)` (`:95-98`, Protocol `:36-38`).
- Writes: `action_draft_repo.mark_superseded(...)` (`:121-125`, Protocol `:40-46`). Sets a **flag**, not a state transition. `ActionDraftStateTransitionError` is caught and counted as "skipped" (`:128-132`).

### Result

`SupersedeCheckResult(marked_count, skipped_count, error_count, marked_draft_ids)` (`:49-62`).

## 3. Order builder (`ibkr_submission/order_builder.py`)

Module docstring (`order_builder.py:1-15`): "The only place in the codebase where Decimal crosses to float."

### Entry point

`build_ib_order(*, draft, tick, conid=None)` (`order_builder.py:74-145`).

### Validation (`order_builder.py:94-107`)

`quantity > 0`, `limit_price_local > 0`, `order_type == "LMT"`, `time_in_force == "DAY"`, `side ∈ {BUY, SELL}`.

### Tick-size alignment

`round_to_tick_size(...)` (banker's rounding) (`order_builder.py:52-71`). Drift greater than one tick raises `LimitPriceNotOnTickSizeError` (`:41-49, :115-121`).

### Translation to `ibapi.Order`

Lazy `from ib_insync import Contract, Order` (`order_builder.py:123`) — module importable in tests without `ib_insync` installed (rationale `:10-14`).

`Contract(secType="STK", symbol=draft.symbol, exchange=draft.exchange, currency=draft.currency_local)` (`order_builder.py:125-130`); optional `conId` (`:131-132`).

### The Decimal → float boundary

The conversion happens here and nowhere else (`order_builder.py:88-92, :134-141`):

- `totalQuantity=float(draft.quantity)` (`:139`)
- `lmtPrice=float(rounded_limit)` (`:141`)

`Order(action=draft.side, totalQuantity=..., orderType="LMT", lmtPrice=..., tif="DAY", outsideRth=False)` (`:137-144`).

### Bracket orders — NOT implemented in the worker

`build_ib_order` returns a single `(Contract, Order)` tuple (`order_builder.py:79, :145`). **No** parent + take-profit + stop-loss children; **no** `transmit` flag handling. Module docstring (`:32-35`): "Task 134 only ships LMT for stocks + ETFs." The bracket / `transmit` handshake lives in the **API** package at `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py` — not in the worker.

`TickSize` dataclass at `:26-39` (`tick_size_local`, `min_lot_size = Decimal("1")`).

## 4. Safety re-check (`ibkr_submission/safety_recheck.py`)

Pure function — "never mutates any draft, never opens an IBKR socket, never reads from storage directly" (`safety_recheck.py:12-14`).

### Entry point

`evaluate_submission_gates(...)` (`safety_recheck.py:240-370`). Docstring (`:256-258`): "Returns on the first failure; the order matters so the UI surfaces the most-actionable Dutch message."

### Locked `SubmissionBlockReason` enum (`safety_recheck.py:37-51`)

`cash_insufficient`, `mode_mismatch`, `connection_down`, `account_id_mismatch`, `duplicate_in_flight`, `market_closed`, `cooldown`, `daily_limit`, `soft_drawdown`, `hard_drawdown`, `fomo`, `tick_size_invalid`, `unknown`.

### Pre-condition

Draft must be `user_approved`. Gate at `safety_recheck.py:274-279`: if `draft.status != "user_approved"` → `blocked(reason="unknown", gate="draft_status", explanation_nl="Draft is niet in user_approved status.")`.

### Gates checked in locked order (12 gates after the precondition)

| # | Gate name | Block reason | File:line |
|---|---|---|---|
| 1 | `gateway_connected` | `connection_down` | `safety_recheck.py:281-282` |
| 2 | `account_mode_match` | `mode_mismatch` | `:284-293` (paper-account `DU`/`DF` prefix guard) |
| 3 | `account_id_match` | `account_id_mismatch` | `:295-296` |
| 4 | `market_hours` | `market_closed` | `:298-300` (only when provider supplied) |
| 5 | `duplicate_in_flight` | `duplicate_in_flight` | `:302-306` (in-flight set `:384-392`: `{submitted, accepted, working, partially_filled, pending_cancellation}`) |
| 6 | `hard_drawdown_unknown` / `hard_drawdown` | `hard_drawdown` | `:308-315` |
| 7 | `soft_drawdown_unknown` / `soft_drawdown` (BUY only) | `soft_drawdown` | `:316-323` |
| 8 | `daily_limit` | `daily_limit` | `:325-334` (24 h window) |
| 9 | `cooldown` | `cooldown` | `:336-346` (skipped when `cooldown_seconds == 0`) |
| 10 | `cash_snapshot_missing` / `cash_sufficient` (BUY) | `cash_insufficient` | `:348-352` |
| 11 | `position_snapshot_missing` / `position_sufficient` (SELL) | `cash_insufficient` (reused) | `:354-358` |
| 12 | `fomo_price_invalid` / `fomo_drift` | `fomo` | `:360-368` |

### Doctrine A–K gates — implementation map

All 11 user-doctrine A–K gates are implemented here (this file is the single source of truth for the Tier-1 re-check per `safety_recheck.py:4-9`): connection, mode, account-id, market-hours, duplicate-in-flight, hard-drawdown, soft-drawdown, daily-limit, cooldown, cash/position, FOMO.

`tick_size_invalid` is in the block-reason enum (`:49`) and has a Dutch message (`:221-224`), but is **not** exercised inside `evaluate_submission_gates` — it is raised later by `order_builder` (`order_builder.py:41-49, :117-121`) and converted to an audit row in `submitter.py:225-237`.

### `dry_run_passed` re-check — NOT present

A grep for `dry_run_passed` / `run_dry_run_safety_checks` returns zero hits in the worker. This concept is owned by the API + `portfolio` packages, not by `safety_recheck.py`.

### Result

`SubmissionGateResult` frozen dataclass (`safety_recheck.py:131-162`): `ok`, `block_reason`, `explanation_nl`, `failed_gates`. Constructors `ok_result()` and `blocked(...)`.

Inputs: `GatewaySnapshot` (`:59-72`), `RecentSubmissionRecord` (`:74-85`), `DrawdownContext` (`:87-100`), `FomoContext` (`:114-123`), `MarketHoursProviderProtocol` (`:103-111`). Locked Dutch explanations at `:170-228`.

## 5. Submitter (`ibkr_submission/submitter.py`)

### The single `place_order` authority in the worker

Module docstring (`submitter.py:1-18`): "The submitter is the single code path that calls `placeOrder()` in the production runtime."

The call site invoked is the **snake-case** adapter method `place_order(contract, order)`, **not** the raw camel-case `ib_insync.IB.placeOrder`:

```
trade = self._submit_adapter.place_order(contract, order)
```

at **`submitter.py:240`**.

`IbkrSubmitProtocol` (`submitter.py:60-89`) declares the adapter interface:

- `def place_order(self, contract: Any, order: Any) -> SubmittedTrade: ...` (`:85-87`)
- `def cancel_order(self, perm_id: int) -> None: ...` (`:89`)

`ib_insync` is **not** imported in `submitter.py` — imports at `:21-39` are stdlib + `ai_trading_agent_storage` + `order_builder`. The Decimal → float crossing lives in `order_builder.py:139-141`, not here.

**Worker grep audit:** the worker has **one** `place_order(...)` production call site (`submitter.py:240`) and **zero** `cancel_order(...)` production call sites (the adapter method is declared but never invoked — see §7).

**API audit (for cross-reference):** `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py:525` contains `self._app.placeOrder(order_id + offset, contract, order)` — i.e. the **API also has a `placeOrder` call site**, contrary to the doctrine "only the worker has `placeOrder` authority." This was already flagged in `docs/reality/components/api-ibkr-submission-and-watchlists.md` (T-004); recording it again here so the boundary picture is complete in one place. Doctrine clean-up (single owner of order transmission) is Phase 4 territory.

### `IbkrSubmitter.submit(draft)` (`submitter.py:165-297`)

#### Tier-two account-ID re-read (`:173-185`)

`live_account = self._submit_adapter.fetch_managed_account_id()` followed by `if live_account != draft.ibkr_account_id` → record `rejected_at_send` with reason `account_id_mismatch` and Dutch message. Doctrine comment at `:173-176`. (The account-mode `DU`/`DF` prefix check is performed earlier in `safety_recheck`, `:284-293`.)

`account_mode` is sourced from the live adapter via `self._submit_adapter.account_mode: Literal["paper", "live"]` (`submitter.py:72`) and stamped on every audit row (`:274, :314`).

#### Connection-lost paths (`IbkrConnectionLostError`)

Two sites raise:

- During `fetch_tick_size` — `submitter.py:194-206`: writes audit row with `result="connection_lost"`, `reason="connection_down"`, `error_class=type(exc).__name__`.
- During `place_order` — `submitter.py:241-253`: writes audit row with `result="connection_lost"`, `reason="connection_down"`.

After a `connection_lost` audit row, `_record_block_and_mark_draft` (`submitter.py:299-353`) sets a `submission_block_reason` via `action_draft_repo.set_submission_block_reason(...)` (`:336-340`) but does **not** transition the draft status — **the draft stays at `user_approved`** (the success-path `apply_lifecycle_transition` at `:285-289` is the only place that transitions to `submitted`). Doctrine echo at `submitter.py:14-17`. The submitter itself does **not** retry — the sweep retries on the next tick (`:16-17`).

#### Audit chain — `ibkr_submission_audit` table

Writes via `SqlAlchemyIbkrSubmissionAuditRepository.append(IbkrSubmissionAuditEntry(...))`:

- Success: `submitter.py:269-284` with `result="placed"`.
- Block / failure: `submitter.py:309-334` with `result ∈ {"rejected_at_send", "connection_lost"}`.

`IbkrSubmissionAuditEntry` fields (`:270-283`): `action_draft_id`, `submitted_at`, `sent_to_account_id`, `sent_account_mode`, `ibkr_perm_id`, `ibkr_order_id`, `contract_json`, `order_json`, `gateway_session_id`, `result`, `error_class`, `error_message_dutch`.

Locked Dutch failure messages at `submitter.py:122-140`.

#### Idempotency

The submitter does **not** key on `(action_draft_id, attempt_no)`. Each `submit()` call appends one fresh `IbkrSubmissionAuditEntry` row — the table is append-only and surrogate-keyed (`:269-284, :309-334`). The "one-per-tick" guarantee is enforced by the **sweep** (see §6), not by attempt-number arithmetic in the submitter.

Idempotency of state transition: on success the submitter calls `apply_lifecycle_transition(new_status="submitted")` once (`:285-289`). The storage state machine rejects an illegal re-transition — that is the actual safety rail.

#### Success path (`submitter.py:267-297`)

Write audit row → `apply_lifecycle_transition(... new_status="submitted")` → return `SubmissionResult(ok=True, perm_id=trade.perm_id, ...)`.

`SubmissionResult` dataclass at `:100-115`. Errors: `IbkrConnectionLostError` (`:92-93`); `IbkrTickSizeFetchError` (`:96-97`).

## 6. Submission sweep (`ibkr_submission/submission_sweep.py`)

### `SubmissionSweep` class

Class at `submission_sweep.py:178-457`. Constructor at `:186-215`. Public `tick()` no-arg APScheduler entry at `:217-231`. Private `_run_locked` at `:233-346`.

`SweepMode` literal (`:57-63`): `completed | skipped_locked | skipped_market_closed | no_drafts | error`.

### `tick()` body

1. `tick()` records `started`, tries `self._lock.try_acquire()` (`:219`); failure → `mode="skipped_locked"` (`:217-224`).
2. `_run_locked` executes the work; `finally:` releases the lock (`:227-231`).
3. `_run_locked` (`:233-346`):
   - Market-hours short-circuit via `self._market_hours.is_open(exchange="UNKNOWN", now=started)` → if closed, `mode="skipped_market_closed"` (`:241-248`).
   - Queue poll: `drafts = self._action_draft_repo.list_user_approved_for_sweep(ibkr_account_id=...)` (`:250-263`) — FIFO by `user_approved_at` per docstring (`:4-9`). Empty → `mode="no_drafts"` (`:265-270`).
   - Gateway snapshot: `gateway = self._gateway_snapshot_provider.snapshot()` (`:272`).
   - Load guardrails: `self._guardrail_repo.get_or_default(...)` (`:273-275`).
   - Build `recent_submissions` from `ibkr_submission_audit` (`:276-279`, helper `:407-450`).
   - For each draft: `_evaluate_gates` (`:284-291, :367-405`); on block, set `submission_block_reason` and continue; on pass, submit and **break**.

### Locked one-per-tick

Docstring (`submission_sweep.py:314-317`); `break` at `:337` — **at most one `place_order` per tick.**

### Connection probe before submitting

The "connection probe" is the gateway snapshot at `submission_sweep.py:272` combined with the `connection_down` gate at `safety_recheck.py:281-282`. The snapshot adapter is `GatewaySnapshotProviderProtocol` at `submission_sweep.py:97-100`. There is no separate explicit `ping()` — the sweep relies on `GatewaySnapshot.connected` being authoritative for the tick.

### Lock acquisition

`SingleFlightLockProtocol` imported at `submission_sweep.py:50-52`. `lock.try_acquire()` at `:219`; `lock.release()` at `:229`. Production wiring uses Postgres `pg_advisory_lock` per the module docstring (`:5-9`).

### Worker-owned cancel pattern — declared but unused

The sweep does **not** itself loop over `pending_cancellation` drafts and issue `cancel_order`. Grep `cancel_order` under `apps/worker/src/portfolio_outlook_worker/` returns **zero** production call sites (only the Protocol declaration at `submitter.py:89` and test no-ops).

The `cancel_order` capability exists on the adapter Protocol but is currently unused in production. `apps/api/src/portfolio_outlook_api/action_draft.py:792` references the intended pattern ("the worker is intended to issue `ib.cancelOrder()` from a sweep tick"), but the wiring is not yet implemented. The state side of cancellation is handled by `lifecycle_handler.handle_cancellation_request_event` (see §8) which transitions to `pending_cancellation`; the final `cancelled` arrives via the IBKR callback path.

### Block-reason persistence (per gate)

`action_draft_repo.set_submission_block_reason(action_draft_id, reason, set_at)` at `submission_sweep.py:294-299`. Exceptions are caught and logged (`:300-304`).

### Market hours default

`BrusselsBusinessHoursMarket` (`submission_sweep.py:144-170`) — coarse Mon–Fri 09:00–22:30 UTC. "Holiday awareness is deliberately out of scope for V1" (`:151-152`).

### Result

`SubmissionSweepResult` (`submission_sweep.py:79-89`). `BlockedDraftRecord` (`:66-70`). `SubmittedDraftRecord` (`:73-77`).

## 7. Lifecycle handler (`ibkr_submission/lifecycle_handler.py`)

Listens to four IBKR callback families (`lifecycle_handler.py:1-19`): `Trade.statusEvent`, `Trade.fillEvent`, `Trade.commissionReportEvent`, `Trade.cancelledEvent`.

### Class structure

`LifecycleHandler` (`lifecycle_handler.py:188-504`). Event dataclasses: `OrderStatusEvent` (`:46-60`), `FillEvent` (`:63-80`), `CommissionReportEvent` (`:83-97`), `RejectionEvent` (`:100-111`), `CancellationEvent` (`:114-126`).

### Handler entry points

| Handler | File:line | Driven by |
|---|---|---|
| `handle_status_event` | `:204-294` | `OrderStatusEvent` |
| `handle_fill_event` | `:298-362` | `FillEvent` |
| `handle_commission_report_event` | `:366-394` | `CommissionReportEvent` |
| `handle_rejection_event` | `:398-462` | `RejectionEvent` |
| `handle_cancellation_request_event` | `:466-504` | `CancellationEvent` |

### IBKR raw status → draft status mapping

`_RAW_STATUS_MAP` (`lifecycle_handler.py:139-147`):

| IBKR raw | Mapped |
|---|---|
| `Submitted` | `accepted` |
| `PreSubmitted` | `working` |
| `Filled` | `filled` |
| `Cancelled`, `ApiCancelled` | `cancelled` |
| `Inactive`, `Rejected` | `rejected` |

Disambiguator `map_raw_status_to_lifecycle_status(*, ibkr_raw_status, remaining_quantity)` (`lifecycle_handler.py:150-166`) decides `filled` (terminal) vs `partially_filled` (remaining > 0).

### State transitions written

All transitions go through `self._action_draft_repo.apply_lifecycle_transition(action_draft_id, new_status, transitioned_at)`:

| Transition | File:line | Trigger |
|---|---|---|
| `submitted → accepted/working` | `:269-273` | `handle_status_event` |
| `submitted → filled / partially_filled` | `:333-337` (decision at `:312-313`) | `handle_fill_event` |
| `submitted/accepted/working → rejected` | `:434-438` | `handle_rejection_event` |
| `in-flight → pending_cancellation` | `:479-483` | `handle_cancellation_request_event` |
| `IBKR-confirmed cancelled` | via `handle_status_event` mapping | `Cancelled` / `ApiCancelled` from `_RAW_STATUS_MAP` |

Out-of-order rejections (from non-in-flight statuses) are recorded but not re-transitioned (`:406-433`). Idempotent re-delivery: if mapped `next_status == draft.status` → audit row appended, transition skipped (`:244-267`).

### Persistence

- `ibkr_submission_lifecycle` (append-only) via `SqlAlchemyIbkrSubmissionLifecycleRepository.append(IbkrSubmissionLifecycleEntry(...))`. Append sites: status unmapped (`:222-237`), status idempotent (`:247-262`), status applied (`:274-289`), fill (`:342-357`), commission (`:374-389`), rejection out-of-order (`:410-428`), rejection applied (`:439-457`), cancellation request (`:484-499`).
- `ibkr_executions` (append-only, **`UNIQUE` on `ibkr_exec_id`**) via `SqlAlchemyIbkrExecutionsRepository.append(IbkrExecutionEntry(...))`. Append site: `:315-330`. Doctrine on the UNIQUE key at `:66-71`.
- `action_drafts` mutated via `apply_lifecycle_transition` (see above).

### Result

`LifecycleHandlerResult(draft_status_after, lifecycle_row_id, execution_id_written)` (`:174-185`).

## 8. Reconciler orchestrator (`ibkr_reconciliation/reconciler.py`)

### `IbkrReconciler` class

Class at `reconciler.py:139-346`. Constructor at `:148-179`. Public `tick()` no-arg APScheduler entry at `:181-202`. Private `_run_locked` at `:204-346`.

`ReconcilerMode` literal (`:62-67`): `completed | skipped_locked | skipped_disconnected | error`.

### Three-pass dispatch (strict order)

Inside `_run_locked` (`reconciler.py:248-276`):

1. `pass_a = run_pass_a_orphaned_executions(...)` (`:249-259`)
2. `pass_b = run_pass_b_stale_in_flight(...)` (`:260-268`)
3. `pass_c = run_pass_c_timeout_recovery(...)` (`:269-276`)

Wrapped in `try/except Exception` (`:248, :277-319`): on raise, completed-count sums only over passes that finished and the run-audit row is written with `mode_detected="error"` + `error_details_json` (`:285-307`).

### Connection / single-flight gating

- Lock acquisition: `self._lock.try_acquire()` (`reconciler.py:185`); release in `finally` (`:197-202`). Failure → `_empty_run_result(... mode="skipped_locked")` (`:186-192`).
- Gateway connectivity: `if not self._gateway.is_connected()` (`:225`) → run-audit finalised with `mode_detected="skipped_disconnected"` (`:225-242`). Protocol `IbkrReconcilerGatewayProtocol` (`:75-82`).

### Audit-row writes per tick (`reconciliation_run_audit` table)

Exactly **two** operations per tick:

- INSERT (open row, `completed_at=NULL`) at `reconciler.py:210-223`.
- `complete_run(...)` finalisation:
  - Disconnected: `:227-235`.
  - Error: `:292-307`.
  - Completed: `:327-335`.

Each pass writes its own per-divergence rows (see §§9–11); the orchestrator does not duplicate them.

### Run ID factory

`f"recon-{uuid.uuid4().hex[:16]}"` (`reconciler.py:366-367`).

### Locked pass names (`_LOCKED_RECONCILIATION_PASS_NAMES`)

Not declared as a top-level enum here, but the three strings used as `pass_name=` arguments on `ReconciliationAuditEntry` are:

- `"orphaned_execution"` — `pass_a_orphaned_executions.py:255, :310, :347`.
- `"stale_in_flight"` — `pass_b_stale_in_flight.py:260, :334, :368, :403`.
- `"timeout_recovery"` — `pass_c_timeout_recovery.py:145`.

### Result

`IbkrReconcilerResult` (`reconciler.py:90-131`) with derived counts (`:109-131`).

## 9. Pass A — orphaned executions (`pass_a_orphaned_executions.py`)

### What it detects (`:7-21`)

1. **Missing executions** — IBKR-known fills the worker missed (dropped callback / offline worker).
2. **Unmatched executions** — IBKR fills whose `perm_id` doesn't map to any local draft (user placed an order directly in TWS).

### Entry point

`run_pass_a_orphaned_executions(...)` (`pass_a_orphaned_executions.py:125-218`).

Input `IbkrExecutionForReconciliation` (`:65-83`). Protocol `IbkrExecutionFetcherProtocol` (`:86-97`) wraps `ib_insync.IB.reqExecutions(account, since)` (`:89-93`).

### Per-execution flow (`:152-206`)

- Already in `ibkr_executions` (`executions_repo.get_by_exec_id`) → `already_recorded += 1` (`:153-155`).
- Already in `unmatched_execution_audit` (`unmatched_repo.get_by_exec_id`) → `already_recorded += 1` (`:157-161`).
- `draft_id = submission_audit_repo.get_action_draft_id_for_perm_id(execution.ibkr_perm_id)` (`:163-165`).
- `draft_id is None` → `_record_unmatched_execution` (`:166-176`).
- Draft not found → `_record_unmatched_execution` (`:178-192`).
- Else → `_apply_missing_execution` (`:194-205`).

### Heal action — missing execution

`_apply_missing_execution` (`:275-362`):

- Insert in `ibkr_executions` via `executions_repo.append(IbkrExecutionEntry(...))` (`:289-304`). `exchange="RECONCILIATION"` (`:302`); commission = zero — Pass A has no commission yet (`:300-301`).
- Append `ReconciliationAuditEntry` with `divergence_type="missing_execution_applied"` (`:305-325`).
- Compute target status via `_resolve_next_status` (`:365-392`):
  - Terminal statuses `{filled, cancelled, rejected, dismissed, deleted, superseded, requires_manual_review}` are not reversed → returns `None` (`:372-384`).
  - Else sum filled quantity; `filled >= draft.quantity` → `"filled"`, else `"partially_filled"` (`:386-392`).
- Apply via `action_draft_repo.apply_lifecycle_transition(new_status=next_status, transitioned_at=event_at)` (`:337-341`).
- Append a second audit row with `divergence_type=_status_corrected_divergence_for(updated.status)` (`:342-361`); helper at `:395-410` maps to `status_corrected_to_filled` / `_partially_filled` / `_cancelled` / `_rejected`.

### Unmatched-execution write

`_record_unmatched_execution` (`:226-272`):

- `unmatched_repo.append(UnmatchedExecutionAuditEntry(... resolution_status="unresolved"))` (`:235-249`).
- `ReconciliationAuditEntry` with `pass_name="orphaned_execution"`, `divergence_type="unmatched_execution"` (`:250-272`).

### Idempotency notes

UNIQUE on `ibkr_executions.ibkr_exec_id` and on `unmatched_execution_audit.ibkr_exec_id` (`:24-29`). Reconciliation audit is append-only; dashboards de-dupe by `(reconciliation_run_id, action_draft_id)` (`:26-29`).

### Result

`PassAOrphanedExecutionsResult` (`:105-117`).

## 10. Pass B — stale in-flight (`pass_b_stale_in_flight.py`)

### What it detects (`:1-9, :67-68`)

Drafts the worker has as in-flight (`submitted`, `accepted`, `working`, `partially_filled`, `pending_cancellation`) that may have moved to terminal at IBKR.

### Entry point

`run_pass_b_stale_in_flight(...)` (`pass_b_stale_in_flight.py:129-289`).

Input `IbkrOrderStatusForReconciliation` (`:71-87`) carrying `found_in_ibkr: bool` (distinguishes "unknown perm_id" from "known with status"). Protocol `IbkrOrderStatusFetcherProtocol` (`:90-100`) wraps `ib_insync.IB.reqOpenOrders()` (`:93-96`).

### Per-draft flow (`:156-276`)

- Pull active drafts: `action_draft_repo.list_active_for_account(ibkr_account_id)` (`:146-148`).
- Resolve latest "placed" perm_id via `_resolve_perm_id_for_draft` (`:297-315`) — walks `submission_audit_repo.list_for_draft(action_draft_id)` reverse looking for `result == "placed"` (`:311-314`).
- No perm_id → `skipped += 1` (`:165-167`).
- `fetcher.fetch_order_status(ibkr_perm_id, account_id)` (`:169-173`); on raise → log + skip (`:174-181`).
- `not status.found_in_ibkr` → `_log_terminal_divergence_unknown_to_ibkr` (`:185-196`).
- Map IBKR raw via `_IBKR_RAW_TO_DRAFT_STATUS` (`:56-64`): `Submitted→accepted`, `PreSubmitted→working`, `Filled→filled`, `Cancelled→cancelled`, `ApiCancelled→cancelled`, `Inactive→rejected`, `Rejected→rejected`.
- Unknown raw → `_log_terminal_divergence_unknown_status` (`:202-212`).
- `_IBKR_TERMINAL_STATUSES = frozenset({"filled", "cancelled", "rejected"})` (`:68`).
- Non-terminal or already-equal → `in_sync` (`:215-225`).

### Heal action

- `action_draft_repo.apply_lifecycle_transition(new_status=mapped, transitioned_at=event_at)` (`:228-233`).
- Transition failure → `_log_terminal_divergence_transition_failed` (`:234-253`).
- Success → `ReconciliationAuditEntry` with `pass_name="stale_in_flight"`, `divergence_type=_corrected_divergence_for(updated.status)` (`:255-274`; helper `:421-432`).

Pass B does **not** write to `ibkr_executions` (`:13-16`).

### Locked audit-row failure variants

- `_log_terminal_divergence_unknown_to_ibkr` (`:318-348`).
- `_log_terminal_divergence_unknown_status` (`:351-383`).
- `_log_terminal_divergence_transition_failed` (`:386-418`).

All share `divergence_type="terminal_state_divergence_logged"`.

### Result

`PassBStaleInFlightResult` (`:108-121`).

## 11. Pass C — timeout recovery (`pass_c_timeout_recovery.py`)

### What it detects (`:1-9`)

Drafts in `awaiting_reply_timeout` whose `terminal_state_at` is older than 24 h.

### Constants

`TIMEOUT_CUTOFF = timedelta(hours=24)` (`pass_c_timeout_recovery.py:46`) — "not configurable" (`:45`).

### Entry point

`run_pass_c_timeout_recovery(...)` (`pass_c_timeout_recovery.py:73-172`).

### Flow (`:93-161`)

- `timeouts = action_draft_repo.list_by_status(account_id, "awaiting_reply_timeout")` (`:84-86`).
- Skip if `terminal_state_at is None` (`:94-96`).
- Tz-agnostic age calc (`:97-107`) — SQLite `tzinfo` round-trip workaround.
- `age < TIMEOUT_CUTOFF` → `within_cutoff += 1` (`:108-110`).
- Else heal:

### Heal action — escalate to `requires_manual_review`

- Transition via `action_draft_repo.apply_lifecycle_transition(new_status="requires_manual_review", transitioned_at=now)` (`:113-118`).

**Vocabulary note:** the literal in the worker code is **`"requires_manual_review"`** (matches the storage state machine at `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:4910`). The T-007 task spec referenced `"manual_review_required"` — that spelling is **not** in this codebase.

- Append `ManualReviewQueueEntry(flagged_at, action_draft_id, reason="timeout_24h_no_data", details_dutch=..., resolution_status="pending")` (`:126-139`).
- Append `ReconciliationAuditEntry(pass_name="timeout_recovery", divergence_type="timeout_flagged_manual_review", ibkr_evidence_json={awaited_since, elapsed_seconds, cutoff_seconds}, notes_dutch=...)` (`:140-159`).

### Result

`PassCTimeoutRecoveryResult` (`:54-65`).

## 12. Safety boundary verification (`placeOrder` / `cancelOrder` audit)

`grep -rn 'placeOrder\|cancelOrder' apps/api/src apps/worker/src` produces a small set of hits. After excluding docstring mentions:

| Side | File:line | Type | Call? |
|---|---|---|---|
| **API** | `ibkr_ibapi_order_submission_client.py:100` | method definition `def placeOrder(...)` | adapter wrapper, not the IBKR write |
| **API** | `ibkr_ibapi_order_submission_client.py:525` | **`self._app.placeOrder(order_id + offset, contract, order)`** | **the API's IBKR `placeOrder` call site** |
| **Worker** | `submitter.py:240` | **`self._submit_adapter.place_order(contract, order)`** | **the worker's `place_order` call site (snake-case adapter)** |

**Worker count summary:**

- `place_order(...)` production call sites: **1** — `submitter.py:240`.
- `cancel_order(...)` production call sites: **0**.

**Cross-tree count summary:**

- Total `placeOrder` (camelCase, ibapi raw) call sites: **1** — `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py:525`.
- Total worker-side `place_order` (snake_case adapter) call sites: **1** — `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submitter.py:240`.
- Total `cancelOrder` / `cancel_order` call sites across the project: **0**.

**Doctrine note.** The user-stated rule "only the worker has `placeOrder` / `cancelOrder` authority" is not currently true — the API package owns a camelCase `placeOrder` call site (`ibkr_ibapi_order_submission_client.py:525`) while the worker owns a wrapped `place_order` (`submitter.py:240`). Doctrine clean-up (single owner of order transmission) is Phase 4 territory; already surfaced in T-004's reality docs.

## 13. State machine touchpoints (worker side)

All worker transitions go through `SqlAlchemyActionDraftRepository.apply_lifecycle_transition(action_draft_id, new_status, transitioned_at)`, which validates against the `_ACTION_DRAFT_TRANSITIONS` map at `packages/storage/src/ai_trading_agent_storage/sql_repositories.py:4820-4911` (validator helper at `:4914-4922`).

### Worker call sites by file:line + new_status

| File:line | New status written | Trigger |
|---|---|---|
| `ibkr_submission/submitter.py:285-289` | `"submitted"` | success path of `submit()` |
| `ibkr_submission/lifecycle_handler.py:269-273` | mapped from `_RAW_STATUS_MAP` — `"accepted"` / `"working"` / `"filled"` / `"partially_filled"` / `"cancelled"` / `"rejected"` | `handle_status_event` |
| `ibkr_submission/lifecycle_handler.py:333-337` | `"filled"` or `"partially_filled"` | `handle_fill_event` |
| `ibkr_submission/lifecycle_handler.py:434-438` | `"rejected"` | `handle_rejection_event` |
| `ibkr_submission/lifecycle_handler.py:479-483` | `"pending_cancellation"` | `handle_cancellation_request_event` |
| `ibkr_reconciliation/pass_a_orphaned_executions.py:337-341` | `"filled"` or `"partially_filled"` | `_apply_missing_execution` |
| `ibkr_reconciliation/pass_b_stale_in_flight.py:229-233` | `"filled"` / `"cancelled"` / `"rejected"` | heal branch |
| `ibkr_reconciliation/pass_c_timeout_recovery.py:114-118` | `"requires_manual_review"` | escalation |

### Auxiliary writes (do NOT go through the state machine)

- `action_draft/supersede_check.py:121-125` — `action_draft_repo.mark_superseded(action_draft_id, by_decision_package_id, marked_at)`: sets the `superseded_by_decision_package_id` flag.
- `ibkr_submission/submitter.py:336-340` — `set_submission_block_reason(...)` on failure paths (draft stays at `user_approved`).
- `ibkr_submission/submission_sweep.py:295-299` — `set_submission_block_reason(...)` when a gate fails.

### Transition keys the worker writes (union)

`submitted`, `accepted`, `working`, `filled`, `partially_filled`, `cancelled`, `rejected`, `pending_cancellation`, `requires_manual_review`.

The worker never writes `proposed`, `edited`, `user_approved`, `dismissed`, `deleted`, `superseded`, or `awaiting_reply_timeout` — those keys are written by the API / composer / time-based watchdog elsewhere (T-004, T-005). The two-vocabulary island (portfolio enum vs storage `_ACTION_DRAFT_TRANSITIONS` map) documented in T-004 / T-005 is consistent with what the worker writes here.

## 14. Cross-cutting observations

- **`place_order` authority is split across the API and the worker.** API at `ibkr_ibapi_order_submission_client.py:525`; worker at `submitter.py:240`. Doctrine clean-up Phase 4.
- **`cancel_order` is not yet wired anywhere.** Protocol declared (`submitter.py:89`); zero production call sites; the `pending_cancellation → cancelled` resolution path relies on the IBKR callback (`Cancelled` / `ApiCancelled` in `_RAW_STATUS_MAP`).
- **Worker composer mints drafts at status `proposed`.** Not `user_approved`, not `pending`. The user approval is a separate UI-driven state transition (per the state machine in storage).
- **No `run_dry_run_safety_checks` in the worker.** That helper is API + `portfolio` package; the worker's Tier-1 guard is `safety_recheck.evaluate_submission_gates` (12 gates).
- **Reconciliation pass-name strings are scattered, not centralised.** The three `pass_name` literals (`orphaned_execution`, `stale_in_flight`, `timeout_recovery`) are repeated across `pass_a/b/c_*.py`. A constants module would prevent typo drift but is Phase 4.
- **Bracket orders + `transmit` flag handling live only in the API.** Worker `order_builder` ships a single (Contract, Order) for LMT only (`order_builder.py:32-35`).
- **`requires_manual_review` is the correct literal.** The T-007 task spec mentioned `manual_review_required`; the worker (and the storage state machine at `sql_repositories.py:4910`) use `requires_manual_review`. Update the spec, not the code.
- **`ibkr_executions.ibkr_exec_id` is `UNIQUE`** (`lifecycle_handler.py:66-71`). Combined with the append-only `ibkr_submission_audit` table, this is the integrity backstop for the reconciliation passes.
