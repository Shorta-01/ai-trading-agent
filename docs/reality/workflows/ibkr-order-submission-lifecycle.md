# Reality — workflow: IBKR order submission lifecycle

**Scope.** End-to-end trace from a `status="user_approved"` action-draft → APScheduler submission sweep tick → Tier-1 12-gate safety re-check → order builder (Decimal → float boundary) → Tier-2 account-ID re-read → single `place_order(contract, order)` adapter call → IBKR callback fan-out via lifecycle_handler → state transitions through `submitted → accepted → working → filled / partially_filled / cancelled / rejected` → 3 append-only audit tables.

This is **the most safety-critical workflow in the system**. The `place_order` adapter call site at `submitter.py:240` is the single line of code that converts user approval into a real IBKR order. Every architectural decision in this flow exists to make that line trustworthy.

**Sibling reality docs:**

- `docs/reality/components/worker-actions-and-reconciliation.md` §§3-7 (T-007) — order_builder, safety_recheck, submitter, submission_sweep, lifecycle_handler.
- `docs/reality/components/worker-actions-and-reconciliation.md` §12 (T-007) — `placeOrder` / `cancelOrder` safety boundary audit.
- `docs/reality/components/worker-actions-and-reconciliation.md` §13 (T-007) — state transitions written by the worker.
- `docs/reality/components/api-ibkr-submission-and-watchlists.md` (T-004) — `ibkr_ibapi_order_submission_client.py:525` (API-side `placeOrder` site).
- `docs/reality/workflows/action-draft-composition-and-approval.md` (T-018) — produces the `user_approved` rows this flow consumes.

## 0. TL;DR

Once an action draft reaches `status="user_approved"` (T-018 terminal), the worker's submission sweep takes over. On each APScheduler tick (currently invoked by the sweep's own `tick()` job; T-019 doesn't itself document the cron — see §1.2):

1. Acquire the single-flight lock.
2. Market-hours short-circuit (Mon–Fri 09:00–22:30 UTC; no holiday awareness).
3. Poll FIFO by `user_approved_at`.
4. Snapshot the IBKR gateway (`connected`, `account_id`, `account_mode`).
5. Load drawdown + cash + position guardrails.
6. Build `recent_submissions` history for duplicate-in-flight checks.
7. For each draft: run 12 Tier-1 gates; on first block, record the block reason and continue; on pass, submit and **break**.

The submitter:

8. Re-reads the IBKR managed account ID (**Tier-2 account-ID check**).
9. Fetches tick-size for the asset.
10. Builds the IBKR `Order` + `Contract` via order_builder (**Decimal → float boundary**).
11. Calls `self._submit_adapter.place_order(contract, order)` — **the single line**.
12. On success: writes `ibkr_submission_audit` row + transitions draft to `submitted`.
13. On `IbkrConnectionLostError`: writes `connection_lost` audit row + draft stays at `user_approved` (sweep retries next tick).

Then IBKR callbacks arrive asynchronously via `lifecycle_handler`:

14. `Trade.statusEvent` → `accepted` / `working` / `cancelled` / `rejected`.
15. `Trade.fillEvent` → `filled` / `partially_filled` (with `ibkr_executions` row).
16. `Trade.commissionReportEvent` → commission audit row (no state change).
17. `Trade.cancelledEvent` (user-initiated cancel) → `pending_cancellation`.

Locked one-`place_order`-per-tick (line 337 of submission_sweep.py per T-007 §6) means at most one order/sweep — predictable load, simple failure recovery.

## 1. Submission sweep

Per T-007 `worker-actions-and-reconciliation.md` §6 (`SubmissionSweep` class at `apps/worker/.../ibkr_submission/submission_sweep.py:178-457`).

### 1.1 Locked one-per-tick rule

Docstring at `submission_sweep.py:314-317`; `break` at `:337`. Per T-007 §6: "at most one `place_order` per tick." Multiple `user_approved` drafts wait their turn across consecutive ticks. FIFO ordering by `user_approved_at` (`:250-263`).

The rule is **architecturally important**: it gives the system a single failure-recovery loop. If one submit fails, the next tick retries; if it succeeds, the next draft submits on the following tick. No partial-batch state to reason about.

### 1.2 Trigger

The sweep registers its own APScheduler job (per T-007 §6) — independent of the morning chain's `pre_briefing` + `hourly_delta` + `heartbeat` (T-011 §1). The sweep tick fires at a separate cadence (T-007 §6 documents the registration but not the exact cron; the spec is configured by `runtime_settings.submission_sweep_interval_seconds` or similar — confirmed in the sweep class constructor at T-007 §6).

### 1.3 `tick()` entry (`submission_sweep.py:217-231`)

The no-arg public entry called by APScheduler:

1. Record `started = time.monotonic()`.
2. `lock.try_acquire()` (`:219`). Failure → `mode="skipped_locked"` early-return.
3. Call `_run_locked(...)` (`:227`).
4. `finally: lock.release()` (`:229`).

`SweepMode` literal at `:57-63`: `completed | skipped_locked | skipped_market_closed | no_drafts | error`.

### 1.4 `_run_locked` body (`submission_sweep.py:233-346`)

1. **Market-hours short-circuit** (`:241-248`) — `self._market_hours.is_open(exchange="UNKNOWN", now=started)`. Closed → `mode="skipped_market_closed"`. Default implementation `BrusselsBusinessHoursMarket` (`:144-170`) is coarse Mon–Fri 09:00–22:30 UTC; "Holiday awareness is deliberately out of scope for V1" (`:151-152`).
2. **Queue poll** (`:250-263`) — `self._action_draft_repo.list_user_approved_for_sweep(ibkr_account_id=...)`. Empty → `mode="no_drafts"`.
3. **Gateway snapshot** (`:272`) — `self._gateway_snapshot_provider.snapshot()` returns `GatewaySnapshot(connected, account_id, account_mode)`.
4. **Guardrails** (`:273-275`) — `self._guardrail_repo.get_or_default(...)` — drawdown + cash + position config.
5. **Recent submissions** (`:276-279`) — `_build_recent_submission_records(...)` from `ibkr_submission_audit` for the duplicate-in-flight gate.
6. **Per-draft loop** (`:284-337`):
   - `_evaluate_gates(...)` (`:284-291`) — runs the 12 Tier-1 gates (§2).
   - On block: `set_submission_block_reason(...)` (`:294-299`); continue to next draft.
   - On pass: `_submit_one(...)` (`:337`); **break**.

## 2. Tier-1 — the 12 safety gates

Per T-007 §4 (`apps/worker/.../ibkr_submission/safety_recheck.py:240-370`). **Pure function** — "never mutates any draft, never opens an IBKR socket, never reads from storage directly" (`safety_recheck.py:12-14`).

### 2.1 Locked `SubmissionBlockReason` enum (`safety_recheck.py:37-51`)

```
cash_insufficient, mode_mismatch, connection_down, account_id_mismatch,
duplicate_in_flight, market_closed, cooldown, daily_limit, soft_drawdown,
hard_drawdown, fomo, tick_size_invalid, unknown
```

13 literals total (12 + `unknown` for the pre-condition).

### 2.2 Pre-condition

Gate 0 (not numbered in the spec): `draft.status == "user_approved"`. If not, `blocked(reason="unknown", gate="draft_status", explanation_nl="Draft is niet in user_approved status.")` at `:274-279`. Guards against a race where another route mutates status between sweep poll + gate evaluation.

### 2.3 The 12 gates in locked order

| # | Gate name | Block reason | File:line | Failure trigger |
|---|---|---|---|---|
| 1 | `gateway_connected` | `connection_down` | `:281-282` | `not gateway.connected` |
| 2 | `account_mode_match` | `mode_mismatch` | `:284-293` | paper-account prefix (`DU`/`DF`) doesn't match `account_mode` |
| 3 | `account_id_match` | `account_id_mismatch` | `:295-296` | `gateway.account_id != draft.ibkr_account_id` |
| 4 | `market_hours` | `market_closed` | `:298-300` | market-hours provider says closed (when provided) |
| 5 | `duplicate_in_flight` | `duplicate_in_flight` | `:302-306` | another draft for same `(conid, side)` already in `{submitted, accepted, working, partially_filled, pending_cancellation}` (in-flight set declared `:384-392`) |
| 6 | `hard_drawdown` | `hard_drawdown` | `:308-315` | hard-drawdown context says "blocked"; or unknown → fail-closed |
| 7 | `soft_drawdown` (BUY only) | `soft_drawdown` | `:316-323` | soft-drawdown breached; SELL bypasses this gate |
| 8 | `daily_limit` | `daily_limit` | `:325-334` | 24h rolling order count over the configured limit |
| 9 | `cooldown` | `cooldown` | `:336-346` | last submit for same conid is too recent (skipped when `cooldown_seconds == 0`) |
| 10 | `cash_sufficient` (BUY) | `cash_insufficient` | `:348-352` | available cash < required notional + buffer |
| 11 | `position_sufficient` (SELL) | `cash_insufficient` (reused enum) | `:354-358` | held quantity < requested sell quantity |
| 12 | `fomo_drift` | `fomo` | `:360-368` | last close drifted too far from approved limit price (FOMO chase guard) |

### 2.4 First-failure-wins

Per `:256-258` docstring: "Returns on the first failure; the order matters so the UI surfaces the most-actionable Dutch message."

Result type `SubmissionGateResult(ok: bool, block_reason, explanation_nl, failed_gates)` (`safety_recheck.py:131-162`). On block, `failed_gates: tuple[str, ...]` carries the path that led there for audit.

### 2.5 Doctrine A–K vs Tier-1 12-gate mapping

Per T-007 §4 doctrine, all 11 A–K gates of the dry-run (T-018 §2) are mirrored here at submit time, plus 1 additional (`fomo_drift`). The 12 here are NOT a copy of the 11 from T-018 — they're independently designed for the **moment-of-submission** snapshot, which can drift from the moment-of-approval. Specific differences:

- T-018 gate K (`decision_package_chain_intact`) is dry-run-only; not part of Tier-1.
- T-019 `fomo_drift` is submit-time-only; the price moved between approval + submit.
- T-018 gates C/D (order_type + quantity-whole-shares) are dry-run-only; the persisted draft has already passed them; re-checking at submit is redundant.

The two sets share spirit (paper-mode, account-mode, cash, position, daily-limit, duplicate, drawdown) but the moment-of-evaluation differs.

### 2.6 `tick_size_invalid` not enforced in gate sequence

Per T-007 §4: `tick_size_invalid` is in the `SubmissionBlockReason` enum (`:49`) and has a Dutch message (`:221-224`), but **is NOT exercised inside `evaluate_submission_gates`**. It's raised later by `order_builder` (`:41-49, :117-121`) and converted to a `rejected_at_send` audit row in `submitter.py:225-237`.

## 3. Order builder — the Decimal → float boundary

Per T-007 §3 (`apps/worker/.../ibkr_submission/order_builder.py`, 146 lines). Module docstring (`:1-15`):

> "The only place in the codebase where Decimal crosses to float."

### 3.1 Entry

`build_ib_order(*, draft, tick, conid=None)` at `:74-145`. Validates draft preconditions (`:94-107`):

- `quantity > 0`
- `limit_price_local > 0`
- `order_type == "LMT"`
- `time_in_force == "DAY"`
- `side ∈ {BUY, SELL}`

Raises typed errors on each violation.

### 3.2 Tick-size alignment

`round_to_tick_size(...)` (banker's rounding) at `:52-71`. Drift greater than one tick raises `LimitPriceNotOnTickSizeError` (`:41-49`, raised `:115-121`). The submitter catches this and writes a `rejected_at_send` audit row with reason `tick_size_invalid`.

### 3.3 The single Decimal → float crossing

`order_builder.py:88-92, :134-141`:

```python
totalQuantity=float(draft.quantity)
lmtPrice=float(rounded_limit)
```

Two `float()` calls — **the entire system's Decimal→float boundary**. Everywhere else uses Decimal-as-string per T-002 / T-014 / T-015 / T-016 / T-017. The `ib_insync.Order` API requires `float`, so the crossing is bounded to these two lines.

### 3.4 Bracket orders — NOT implemented in worker

`build_ib_order` returns a single `(Contract, Order)` tuple. **No** parent + take-profit + stop-loss children; **no** `transmit` flag handling. Per T-007 §3 module docstring at `order_builder.py:32-35`: "Task 134 only ships LMT for stocks + ETFs."

The bracket / `transmit` handshake exists separately in the **API package** at `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py:525` — see §4.6 doctrine drift.

## 4. The submitter — the `place_order` site

Per T-007 §5 (`apps/worker/.../ibkr_submission/submitter.py`, 369 lines). The **single `place_order` authority in the worker**.

### 4.1 Module docstring (`submitter.py:1-18`)

> "The submitter is the single code path that calls `placeOrder()` in the production runtime."

### 4.2 The single line

`apps/worker/.../ibkr_submission/submitter.py:240`:

```python
trade = self._submit_adapter.place_order(contract, order)
```

**`place_order`** — snake_case adapter method, not the raw camel-case `ib_insync.IB.placeOrder`. The adapter interface `IbkrSubmitProtocol` (`submitter.py:60-89`) declares:

```python
def place_order(self, contract: Any, order: Any) -> SubmittedTrade: ...
def cancel_order(self, perm_id: int) -> None: ...
```

`ib_insync` is **not** imported in `submitter.py` — imports at `:21-39` are stdlib + storage + `order_builder`. The Decimal → float crossing lives in `order_builder.py:139-141`, not here.

### 4.3 IbkrSubmitter.submit(draft) (`submitter.py:165-297`)

Step-by-step:

1. **Tier-2 account-ID re-read** (`:173-185`):
   ```python
   live_account = self._submit_adapter.fetch_managed_account_id()
   if live_account != draft.ibkr_account_id:
       write rejected_at_send audit; return blocked
   ```
   Doctrine comment at `:173-176`: this guards against a race between approval-time + submit-time where the IBKR session's managed account changed. The check is independent of the gateway snapshot Tier-1 used.

2. **Fetch tick size** (`:194-206`): `tick = self._submit_adapter.fetch_tick_size(contract)`. On `IbkrConnectionLostError` → audit `connection_lost` (see §4.5).

3. **Build the IBKR order** (`:208-237`): `(contract, order) = order_builder.build_ib_order(draft=draft, tick=tick)`. On `LimitPriceNotOnTickSizeError` → audit `rejected_at_send` with reason `tick_size_invalid`.

4. **Call `place_order`** (`:240`): the single line.

5. **On success** (`:267-297`):
   - Write `ibkr_submission_audit` row with `result="placed"` (§5.1).
   - Transition draft via `apply_lifecycle_transition(new_status="submitted")` (§6).
   - Return `SubmissionResult(ok=True, perm_id=trade.perm_id, ...)`.

### 4.4 Tier-2 account-ID re-read in detail

`fetch_managed_account_id` (the adapter call) reads from the **live IBKR session**, not from cached state. The account_id is sourced from the live SDK adapter via `self._submit_adapter.account_mode: Literal["paper", "live"]` (`submitter.py:72`) and stamped on every audit row (`:274, :314`).

Tier-1's `account_id_match` gate (gate 3) reads from the gateway snapshot taken at the top of the sweep tick (`submission_sweep.py:272`). Tier-2 re-reads at the moment of submit. The two-tier check guards against a ~1-2 second race between snapshot + submit.

### 4.5 Connection-lost path

Per T-007 §5 — two `IbkrConnectionLostError` raise sites:

- During `fetch_tick_size` (`submitter.py:194-206`): audit `result="connection_lost"`, reason `connection_down`.
- During `place_order` (`:241-253`): audit `result="connection_lost"`, reason `connection_down`.

After a `connection_lost` audit, `_record_block_and_mark_draft` (`submitter.py:299-353`) calls `action_draft_repo.set_submission_block_reason(...)` (`:336-340`) — but **does NOT transition the draft**. The draft stays at `user_approved`. The sweep retries on the next tick.

This is the **at-most-once delivery** discipline: a connection drop during `place_order` could mean (a) the order was never sent, (b) the order was sent but the ACK was lost. In case (b), IBKR may already have the order. Pass A reconciliation (T-020) is the recovery mechanism — it detects an IBKR execution that has no matching local audit row.

### 4.6 The doctrine drift — API also has `placeOrder`

Per T-007 §12 audit:

| Side | File:line | Call |
|---|---|---|
| **Worker** | `apps/worker/.../ibkr_submission/submitter.py:240` | `self._submit_adapter.place_order(contract, order)` (snake_case adapter) |
| **API** | `apps/api/src/portfolio_outlook_api/ibkr_ibapi_order_submission_client.py:525` | `self._app.placeOrder(order_id + offset, contract, order)` (camelCase ibapi raw) |

The API site is part of `ibkr_ibapi_order_submission_client.py` which implements bracket-order construction (parent + take-profit + stop-loss children) with the `transmit` flag handshake. T-004 `api-ibkr-submission-and-watchlists.md` documents this. **It is reachable from API routes** that the worker submission sweep does not control.

Per T-007 §12 + T-018 cross-cut: this is **the doctrine drift**. The user-stated rule "only the worker has `placeOrder` / `cancelOrder` authority" is not currently true. Phase 1c surface — re-confirmed here.

### 4.7 No retry loop in the submitter

The submitter itself does **not** retry. Per `submitter.py:16-17`: "The sweep retries on the next tick." The retry loop is at a different layer (sweep), not within a single `submit()` call.

### 4.8 `cancel_order` not yet wired

Per T-007 §6: the `cancel_order` adapter method is declared on `IbkrSubmitProtocol` (`submitter.py:89`) but **zero production call sites**. Cancellation in V1 flows through:

1. User clicks "Annuleer" on `<ActiefBijIbkrGrid>` (T-008 §6) → `apiClient.cancelSubmittedActionDraft(id)`.
2. API route sets draft `status = "pending_cancellation"`.
3. **No worker code path picks this up to call `cancel_order`.**

Phase 1c surface — the cancellation UI exists; the worker-side execution does not. T-007 §6 documents this gap.

## 5. Audit chain — 3 append-only tables

Per T-007 §§5, 7 + T-003.

### 5.1 `ibkr_submission_audit`

Repository: `SqlAlchemyIbkrSubmissionAuditRepository.append(IbkrSubmissionAuditEntry(...))`.

Write sites:

- **Success** (`submitter.py:269-284`): `result="placed"`. Fields: `action_draft_id`, `submitted_at`, `sent_to_account_id`, `sent_account_mode`, `ibkr_perm_id`, `ibkr_order_id`, `contract_json`, `order_json`, `gateway_session_id`, `result`, `error_class`, `error_message_dutch`.
- **Block / failure** (`submitter.py:309-334`): `result ∈ {"rejected_at_send", "connection_lost"}`.

Idempotency: append-only; **not keyed on `(action_draft_id, attempt_no)`** — each submit attempt appends one row (per T-007 §5). The "one per tick" guarantee is at the sweep level, not in the audit.

### 5.2 `ibkr_submission_lifecycle`

Repository: `SqlAlchemyIbkrSubmissionLifecycleRepository.append(IbkrSubmissionLifecycleEntry(...))`.

Written by `lifecycle_handler` on each IBKR callback (see §6). Append sites per T-007 §7:

| Event type | Site |
|---|---|
| `status_change` (unmapped) | `lifecycle_handler.py:222-237` |
| `status_change` (idempotent no-op — already in target state) | `:247-262` |
| `status_change` (real transition) | `:274-289` |
| `fill` | `:342-357` |
| `commission_report` | `:374-389` |
| `rejection` (out-of-order from non-in-flight) | `:410-428` |
| `rejection` (applied transition) | `:439-457` |
| `cancellation_request` (user) | `:484-499` |

### 5.3 `ibkr_executions`

Repository: `SqlAlchemyIbkrExecutionsRepository.append(IbkrExecutionEntry(...))`. **UNIQUE on `ibkr_exec_id`** (per T-007 §7 doctrine at `lifecycle_handler.py:66-71`).

Append site: `lifecycle_handler.py:315-330` — written on every fill event. The UNIQUE constraint is the **deduplication anchor** for Pass A reconciliation (T-020) — if IBKR redelivers a fill the worker already processed, the second insert fails harmlessly.

## 6. IBKR callbacks via lifecycle_handler

Per T-007 §7 (`apps/worker/.../ibkr_submission/lifecycle_handler.py`, 532 lines).

### 6.1 The 4 callback families

The handler listens to four `Trade.*Event` callbacks from `ib_insync`:

| Callback | Method | Event dataclass |
|---|---|---|
| `Trade.statusEvent` | `handle_status_event` (`:204-294`) | `OrderStatusEvent` (`:46-60`) |
| `Trade.fillEvent` | `handle_fill_event` (`:298-362`) | `FillEvent` (`:63-80`) |
| `Trade.commissionReportEvent` | `handle_commission_report_event` (`:366-394`) | `CommissionReportEvent` (`:83-97`) |
| `Trade.cancelledEvent` | `handle_rejection_event` + `handle_cancellation_request_event` (`:398-462, :466-504`) | `RejectionEvent` (`:100-111`), `CancellationEvent` (`:114-126`) |

### 6.2 IBKR raw → draft status mapping (`lifecycle_handler.py:139-147`)

```python
_RAW_STATUS_MAP = {
    "Submitted": "accepted",
    "PreSubmitted": "working",
    "Filled": "filled",
    "Cancelled": "cancelled",
    "ApiCancelled": "cancelled",
    "Inactive": "rejected",
    "Rejected": "rejected",
}
```

Plus disambiguator `map_raw_status_to_lifecycle_status(*, ibkr_raw_status, remaining_quantity)` (`:150-166`) which decides `filled` (terminal) vs `partially_filled` (remaining > 0) when raw is `Filled`.

### 6.3 State transitions written

All transitions go through `self._action_draft_repo.apply_lifecycle_transition(action_draft_id, new_status, transitioned_at)`:

| Transition | File:line | Trigger |
|---|---|---|
| `submitted → accepted/working` | `:269-273` | `handle_status_event` |
| `submitted → filled / partially_filled` | `:333-337` (decision at `:312-313`) | `handle_fill_event` |
| `submitted/accepted/working → rejected` | `:434-438` | `handle_rejection_event` |
| `in-flight → pending_cancellation` | `:479-483` | `handle_cancellation_request_event` |
| `Cancelled` / `ApiCancelled` raw → `cancelled` | via `handle_status_event` mapping | IBKR-confirmed cancel |

Out-of-order rejections (from non-in-flight statuses) are recorded but not re-transitioned (`:406-433`). Idempotent re-delivery: if mapped `next_status == draft.status` → audit row appended, transition skipped (`:244-267`).

### 6.4 `LifecycleHandlerResult`

`(draft_status_after, lifecycle_row_id, execution_id_written)` per call (`lifecycle_handler.py:174-185`).

## 7. End-to-end timeline

For one `user_approved` draft on a typical sweep tick:

| t (s) | Tier | Action |
|---|---|---|
| 0 | APScheduler | sweep `tick()` fires |
| ~0.01 | Worker | `lock.try_acquire()` ✓ |
| ~0.02 | Worker | `market_hours.is_open()` ✓ |
| ~0.05 | Worker → DB | `list_user_approved_for_sweep` returns 3 drafts (FIFO order) |
| ~0.06 | Worker | gateway snapshot + guardrails + recent_submissions loaded |
| ~0.10 | Worker | `_evaluate_gates` for first draft → all 12 pass |
| ~0.15 | Worker → IBKR | `fetch_managed_account_id` (Tier-2) ✓ |
| ~0.20 | Worker → IBKR | `fetch_tick_size` (for the conid) |
| ~0.22 | Worker | `order_builder.build_ib_order` (Decimal → float crossing) |
| ~0.25 | Worker → IBKR | `place_order(contract, order)` — **the single line** |
| ~0.50-2.0 | IBKR | network round-trip; returns `Trade` object with `perm_id` |
| ~2.0 | Worker → DB | INSERT `ibkr_submission_audit` row (`result="placed"`) |
| ~2.05 | Worker → DB | UPDATE action_drafts SET status='submitted' (via `apply_lifecycle_transition`) |
| ~2.10 | Worker | `break` — loop ends; second + third drafts wait |
| ~2.10 | Worker | `lock.release()` |
| ~3.0 | IBKR async | `Trade.statusEvent` "Submitted" → mapped `accepted` |
| ~3.05 | Worker → DB | `apply_lifecycle_transition` to `accepted` |
| ~3.06 | Worker → DB | INSERT `ibkr_submission_lifecycle` row (`status_change`) |
| ~10.0 | IBKR async | `Trade.fillEvent` arrives |
| ~10.05 | Worker → DB | `apply_lifecycle_transition` to `filled` (or `partially_filled`) |
| ~10.06 | Worker → DB | INSERT `ibkr_executions` row (UNIQUE on exec_id) |
| ~10.07 | Worker → DB | INSERT `ibkr_submission_lifecycle` row (`fill`) |
| ~15.0 | IBKR async | `Trade.commissionReportEvent` |
| ~15.05 | Worker → DB | INSERT `ibkr_submission_lifecycle` row (`commission_report`); no state change |

The user-facing latency from `Goedkeuren` click → "Actief bij IBKR" tab is roughly:

- **Sweep wait**: 0–N seconds depending on sweep cadence + drafts ahead in FIFO.
- **Tier-2 check + place_order**: 1-2 seconds.
- **IBKR callback**: 1-30 seconds for `accepted`; minutes-to-hours for `filled`.

## 8. Failure paths

| Failure | Stage | Result |
|---|---|---|
| Single-flight lock held by another instance | sweep tick | `mode="skipped_locked"`; retry next tick |
| Market closed | sweep tick | `mode="skipped_market_closed"`; retry next tick (probably tomorrow) |
| No `user_approved` drafts | sweep tick | `mode="no_drafts"`; sweep idles |
| Gateway disconnected | gate 1 (`gateway_connected`) | draft stays `user_approved`; sweep retries next tick |
| Account-mode mismatch | gate 2 | `mode_mismatch` block reason written; draft stays `user_approved` until config fixed |
| Account-ID mismatch (Tier-1) | gate 3 | `account_id_mismatch`; draft stays `user_approved` |
| Account-ID mismatch (Tier-2 — race) | submitter `:173-185` | `rejected_at_send` audit; draft stays `user_approved` |
| Tick-size lookup raises `IbkrConnectionLostError` | submitter `:194-206` | `connection_lost` audit; draft stays `user_approved` |
| Tick-size drift > 1 tick | order_builder `:115-121` | `LimitPriceNotOnTickSizeError`; submitter catches → `rejected_at_send` audit with `tick_size_invalid` reason; draft stays `user_approved` |
| `place_order` raises `IbkrConnectionLostError` | submitter `:241-253` | `connection_lost` audit; draft stays `user_approved`; **possible ghost order at IBKR** — Pass A reconciliation recovers (T-020) |
| IBKR session crashes mid-fill | lifecycle handler | partial fills written; reconciliation Pass B detects stale `submitted` state (T-020) |
| `Trade.rejectionEvent` from non-in-flight state (out-of-order) | `:406-433` | audit row only; no state transition |
| `Trade.fillEvent` with `ibkr_exec_id` we already wrote | UNIQUE constraint | second INSERT silently fails; lifecycle row still written |
| User clicks "Annuleer" | API → draft.status = `pending_cancellation` | **no worker code calls `cancel_order` today** — cancellation depends on IBKR-side timeout or user-driven manual cancel in TWS |

The connection-lost-during-`place_order` path is the **most dangerous**: the system can't distinguish "order sent" from "order never sent". This is why Pass A reconciliation (T-020) exists — it scans IBKR-side executions against the local audit chain and surfaces orphans.

## 9. Cross-cuts + Phase 1c surface

The following observations are inputs for Phase 1c gap analysis:

1. **The `placeOrder` doctrine drift re-confirmed** (§4.6). The API has an independent `placeOrder` call site at `ibkr_ibapi_order_submission_client.py:525` — contradicting the user-stated "worker-only authority" rule. Re-confirmed for the 5th+ time across reality docs (T-004, T-007 §12, T-018 §6, here).
2. **`cancel_order` not wired** (§4.8). UI exists; worker-side execution does not. Drafts stuck in `pending_cancellation` rely on IBKR-side timeout. Phase 1c — re-confirmed from T-007 §6.
3. **Holiday awareness is out of scope for V1** (`submission_sweep.py:151-152`). The Mon–Fri 09:00–22:30 UTC window doesn't skip exchange holidays. A V1 deploy attempting to submit on Christmas would hit IBKR's market-closed rejection rather than the worker's market-hours short-circuit. Phase 4 candidate.
4. **Bracket orders only in the API path** (§3.4). The worker `order_builder` ships LMT-DAY only; bracket orders (parent + take-profit + stop-loss) require the API code path at `ibkr_ibapi_order_submission_client.py:525`. The worker can't currently submit a bracket order.
5. **Tier-1 + Tier-2 + Tier-3 (`fomo_drift`)**. Three layers of last-chance checks. The fomo gate (gate 12) was added specifically because price can drift between approval + submit; it's submit-only (no T-018 equivalent).
6. **Connection-lost during `place_order` produces ghost orders** (§8 last row). At-most-once on the local audit; IBKR may have at-least-once. Pass A reconciliation is the only recovery. Phase 1c: explicit "ghost order detection" surface.
7. **Audit not idempotent on `(action_draft_id, attempt_no)`** (§5.1). A retry from the sweep writes a new audit row. Consumers can count attempts by querying audit history for the draft. Phase 4: make `attempt_no` an explicit field.
8. **`tick_size_invalid` not in the 12 gates** (§2.6). The block reason is enumerated but raised in `order_builder`, not `safety_recheck`. Mixing concerns: gate evaluation vs order construction. Phase 1c — unify or document the split.
9. **Out-of-order callbacks**. The lifecycle handler tolerates rejections from non-in-flight states (`:406-433`) by recording the audit but skipping the transition. This protects against IBKR race conditions where rejections arrive after fills.
10. **No batched submissions**. One-per-tick means N drafts = N ticks. For a user who approves 10 drafts at once, 10 sweep ticks must pass to submit them all. Phase 4 candidate: parallel submission with per-conid serialization.

## 10. Out of scope

- **Action-draft composition + approval** (T-018) — produces the `user_approved` rows this flow consumes.
- **Reconciliation passes A/B/C** (T-020 future) — Pass A detects IBKR-side fills with no matching local audit (ghost orders); Pass B detects stale in-flight; Pass C handles `awaiting_reply_timeout`.
- **AI explanation** (T-023 future).
- **TWS read-only adapter** (T-013) — separate IBKR flow; not the submission lifecycle.
- **Action-draft sync admin route** (T-005) — admin debugging tool.

## 11. References

- `docs/reality/components/worker-actions-and-reconciliation.md` §§3-7 + §12 + §13 — module-level reality (T-007).
- `docs/reality/components/api-ibkr-submission-and-watchlists.md` — API-side `placeOrder` doctrine drift site (T-004).
- `docs/reality/components/storage-package-and-migrations.md` — `ibkr_submission_audit`, `ibkr_submission_lifecycle`, `ibkr_executions` tables (T-003).
- `docs/reality/workflows/action-draft-composition-and-approval.md` (T-018) — produces the `user_approved` rows this flow consumes.
- `docs/reality/workflows/morning-chain-orchestration.md` §1.2 (T-011) — the sweep is independent of the morning chain.
- `docs/reality/workflows/ibkr-readonly-sync-positions-cash.md` (T-013) — the sibling read-only IBKR flow.
- `AGENTS.md` §3.2 — "no order without explicit user approval" lock.
- `docs/intent/_trading-system-doctrine.md` §3 — paper-only enforcement.
