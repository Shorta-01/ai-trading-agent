# Dashboard and order flow — intent

**Status:** locked (revised 2026-05-26 with the T-011…T-024 functional review)
**Locked on:** 2026-05-26
**Doctrine:** `docs/intent/_trading-system-doctrine.md`
**Decision records:** `docs/decisions/0002-trading-system-doctrine.md`, `docs/decisions/0008-action-draft-architecture.md`, `docs/decisions/0009-order-lifecycle-architecture.md`
**Scope:** screen-level spec for the morning dashboard and the order lifecycle. Referenced by upcoming reality and workflow tasks (T-008, T-011c, T-013, T-018, T-025, T-026, T-029, T-030).

This document is prescriptive: it states how the dashboard and order flow are intended to work. Depth-first specifications for the action draft state machine + safety guards live in `docs/intent/action-draft-state-machine.md`; for the lifecycle after transmission, in `docs/intent/order-lifecycle.md`. This file is the UX-surface spec.

## 1. Dashboard composition

- Three areas only: portfolio, watchlist, actions. No fourth area. (doctrine §10)
- A single **system-health line** at the very top of the dashboard. One line. Reflects the **worst** current state across all subsystems (sync mode, calibration drift, reconciliation status, last-full-rebuild timestamp, AI budget consumption). Colour reflects worst state: green when all subsystems are healthy (visually quiet); yellow when any subsystem is in a degraded but non-blocking state; red when any subsystem is in a blocking state (visually loud). Clicking opens a breakdown. (doctrine §10)
- A visually unmistakable **PAPER / REAL MONEY badge**. Never ambiguous, never hidden, never styled subtly. PAPER = yellow or equivalent; REAL MONEY = red or equivalent. A glance answers which mode is active. (doctrine §3.1)
- Forbidden on the dashboard: charts, news feed, sentiment ticker, market overview, notifications panel, past-actions history. Those belong on dedicated screens. (doctrine §10)
- When the actions area is empty, a one-line explanation states *why* it is empty (e.g. "watchlist stable, portfolio within target ranges, no forecast triggered a signal"). Empty without explanation is forbidden. (doctrine §10)

## 2. Portfolio area

- Sourced from IBKR. The dashboard reflects what IBKR currently reports. (doctrine §2)
- Each row shows the position-level current value **computed from the last-close price** (doctrine §10). Live prices are used only at the moment of order ticket construction (the on-demand IBKR live quote refresh — see `docs/intent/data-sources.md`).
- No daily P&L on the dashboard. No daily change colouring. No totals delta. (doctrine §10)
- Daily P&L is deliberately not surfaced anywhere as a headline metric — neither here nor on the performance screen — to discourage emotional reactions to single-day moves. (doctrine §11)
- Performance metrics live on a separate Performance Review screen (§8 below), not the dashboard.

## 3. Watchlist area

- Items being tracked but not held.
- Each item shows an inline **"proximity to action"** signal — a small badge or colour cue indicating how close the asset is to triggering a buy suggestion. (doctrine §10)
- The exact definition of the proximity signal (what inputs feed it, what thresholds map to which states) is open and will be defined in T-018 and follow-up brainstorming. See doctrine §15.

## 4. Actions area — two grids + system-decision items

The actions area mixes two categories of items:

- **Order actions** (the dominant category): suggested orders + open orders.
- **System-decision actions** (smaller stream): predictor retirement decisions, settings warnings, reconciliation D-class items, shadow-predictor promotion decisions, audit exceptions.

Both categories share the actions area; visually distinguished by category. There is no separate fourth area on the dashboard. (doctrine §10)

The order-action category contains two distinct grids, each with its own approval action. Approving in the first grid is *not* the same as approving in the second. (doctrine §4)

### 4.1 Suggested orders grid

- System-generated order tickets, IBKR-shaped, with every field pre-filled. (doctrine §4.1, §5)
- **Per-row trust signal**, inline: a single cue that converges three concerns — forecast confidence + data freshness + decision-package trust tier (full / degraded / minimal). Not separate badges. (doctrine §10)
- **Per-row explanation icon.** Clicking it reveals the AI-generated explanation (see `docs/intent/ai-usage.md` for depth B/C):
  - What the forecast says
  - What data drove it (sources, freshness)
  - What risk and sizing logic produced the field values
  - Which of the three sizing layers (Kelly base, conviction scaling, hard caps — see §5.1) was binding for this order
  - What alternatives were considered, if any (depth C, on-demand)
- **User actions on a suggested row:**
  - **Approve as-is.** The order is parked in IBKR. It does *not* go to the market.
  - **Edit then approve.** Edited fields are validated client-side instantly (§5.6). The full IBKR `whatIfOrder` validation runs once when the user presses Approve. On success the order is parked in IBKR; on rejection the order is blocked and the reason is shown. **Edit-as-override** semantics: both the original system-proposed value and the user-edited value are recorded per field (doctrine §4.5). The original is never silently overwritten.
  - **Reject.** Optional one-word reason (cash / risk / personal / other), logged silently for later pattern analysis. The order never reaches IBKR. (doctrine §4.1)
- **Recurrence counter**, inline. When the same suggestion (same asset, same direction, similar size) appears on consecutive days, the row shows a counter ("3rd time this week"). Informational only — no snooze, no permanent dismissal, no "reject for a week". Every day evaluates fresh. (doctrine §9)
- **Bulk behaviour** (doctrine §4.4):
  - **Approval is individual-only.** No "approve all".
  - **Bulk reject** is allowed with a single shared one-word reason applied to all selected drafts. The audit log records the bulk operation as a coherent batch event.

### 4.2 Open orders grid

(Renamed from "IBKR todo grid" per doctrine §4.2 revision.)

- A **live view of IBKR's current order book.** Whatever IBKR currently holds is what this grid shows. (doctrine §4.2)
- Includes **both parked** orders (awaiting the second approve) **and transmitted** orders (live at the exchange, not yet fully filled). Per-row status badges: `parked` / `transmitted` / `partial-filled N/M`.
- Includes orders from any origin (system-originated *and* orders placed manually by the user inside IBKR or TWS). The grid does *not* distinguish them — IBKR is the source of truth and the grid mirrors it without origin badges, without edit-history flags, without a recently-filled section. Resolved orders (fully filled, cancelled, rejected) leave the grid.
- **Sync model:** hybrid push/pull (event-driven subscription primary; periodic polling fallback). The system-health line (§1) reflects which mode is currently active. (doctrine §6)
- **User actions on any unresolved row:**
  - **Approve** a parked order for submission to the market. This is the *real* submission. (doctrine §4.2)
  - **Edit then approve.** Edits to a parked or transmitted order are pushed to IBKR via the modify-order API. The full IBKR `whatIfOrder` validation re-runs before the modify is sent. (doctrine §5.5)
  - **Cancel.** Cancels the order in IBKR. Fire-and-forget; race conditions with a just-arrived fill are inherent and expected (the audit trail records what was attempted and what IBKR reported back). (doctrine §4.2)
- **Bulk behaviour** (doctrine §4.4):
  - **Submit is individual-only.** The second approve is per ticket.
  - **Bulk cancel** is allowed; same shared-reason / batch-event semantics as bulk reject.

### 4.3 Action draft state machine (summary)

The action draft is the user-owned layer between a decision package's suggested action and a real IBKR order. States (locked enum):

- `drafted` — Just created from a decision package. Editable.
- `user-approved` — User pressed Approve. Locked from further edits.
- `submitting` — Worker has picked it up; `placeOrder()` in flight.
- `ibkr-acknowledged` — IBKR returned a `permId`.
- `parked` — IBKR confirms the order is parked. Lifecycle now owned by the Open orders grid.
- `user-rejected` — User rejected. Terminal.
- `withdrawn-by-system` — Auto-withdrawal of stale draft (>24h in `drafted`) or supersede by newer decision package. Terminal.
- `failed` — Submission failed unrecoverably. Terminal.

**Retries on transient submission failures:** up to 3 attempts with exponential backoff (1s / 4s / 16s).

**Recoverable vs unrecoverable rejection** classification is **configurable** (Category 3 in `docs/intent/settings-and-credentials.md`). Default for unknown codes: unrecoverable (fail closed).

**Auto-withdrawal:** drafts in `drafted` for more than 24 hours are withdrawn by the system; the next morning's evaluation will re-propose if still warranted.

Full state diagram, transition rules, and detailed retry policy live in `docs/intent/action-draft-state-machine.md`.

### 4.4 Safety guards — eleven (summary)

Every approve runs the full guard set, both at draft creation and at worker submission. The **submission-time evaluation is authoritative.** Every block is audit-logged.

| ID | Guard | Class | One-liner |
|----|-------|-------|-----------|
| A | account-mode-match | hard-block | Connected account mode (PAPER/REAL) must match draft's `account_mode_at_creation`. |
| B | connection-up | hard-block | IBKR session must be connected. |
| C | account-id-match | hard-block | Connected account ID must match draft's `ibkr_account_id`. |
| D | market-hours | hard-block | Primary exchange must be open. |
| E | duplicate-in-flight | hard-block | No duplicate (account, conid, side) in `user-approved` or `submitting`. |
| F | cash-sufficient | hard-block | Usable cash covers notional + commissions. |
| G | position-sufficient | hard-block | For SELL, held quantity ≥ draft quantity. |
| H | cooldown | hard-block | 60-second cooldown between drafts on same conid. |
| I | daily-limit | hard-block | Max approvals / 24h. |
| J | drawdown | hard/soft | Soft 5%/5-day blocks BUY only; hard 10%/20-day blocks all until acknowledged. |
| K | fomo-drift | hard-block | Price drift > 1.5% from approved limit requires re-approval. |

Full guard rationale, classification details, and audit-event schema live in `docs/intent/action-draft-state-machine.md`.

## 5. Order ticket field pre-fills (system-side rules)

When the system generates a suggestion it produces a complete IBKR-shaped order ticket. (doctrine §5)

### 5.1 Quantity (doctrine §5.1)

Three layers, applied in order:
- **Base:** fractional Kelly sizing using `kelly_sizing.py`, defaulting to 0.25 Kelly (not full Kelly). Derived from per-trade risk budget and a system-derived stop-loss level.
- **Conviction scaling:** base × forecast confidence score. High-confidence signals get full base; lower confidence proportionally less.
- **Hard caps:** max % per single position, max % per sector, max % per asset class. Caps are absolute — they override layers 1 and 2 if breached.

The order ticket shows the resulting share count. The explanation icon (§4.1) must indicate which of the three layers was binding for this specific order.

### 5.2 Order type (doctrine §5.2)

The system picks the best order type per situation: market, limit, stop, bracket. The choice is determined by the suggestion's logic, not by a global default.

### 5.3 Limit price (doctrine §5.3)

Patient-liquidity defaults:
- **Buys:** current mid-price minus a configurable discount (default 0.2%).
- **Sells:** current mid-price plus a configurable premium (default 0.2%).
- The discount/premium is per-asset configurable — higher for high-volatility assets, lower for low-volatility ETFs.
- **Forecast override:** when the system's forecast-implied fair value disagrees materially with the mid-price (threshold to be defined — see doctrine §15), the forecast value overrides the patient-liquidity default.

The explanation icon must show which logic was used (patient liquidity vs forecast override) and why.

### 5.4 Time-in-force (doctrine §5.4)

- **Default:** DAY, always. Unfilled orders auto-cancel at market close.
- **GTC and GTD:** available only via a "show advanced" toggle (§5.5). Never the system's default.
- This aligns with the morning evaluation rule (doctrine §7): every day evaluates fresh, so a persistent open order is in tension with the model and must be a deliberate user override.

### 5.5 Ticket UI: progressive disclosure

- **Minimal view (default):** symbol (read-only), action (read-only), quantity (editable), order type (editable), limit price if applicable (editable), TIF (editable).
- **"Show advanced" toggle:** reveals the full IBKR field set.
- All other fields use system-set sensible defaults until the user expands advanced.

### 5.6 Validation (doctrine §5.5)

- **Client-side, instant:** cheap rules (positive numbers, valid symbol, lot-size multiples, valid TIF values, etc.) checked in the browser as the user edits.
- **IBKR round-trip on Approve:** `whatIfOrder` runs once when the user presses Approve. Returns margin impact, commission estimate, and any rejection reason.
- If IBKR rejects, submission is blocked and the rejection reason is shown to the user.
- Applies in **both grids** — the first approve (suggested → IBKR parked) and the second approve (Open orders grid parked → market). Modify on transmitted orders re-runs `whatIfOrder` before the modify is sent.

## 6. Two action categories on the dashboard

Order actions are the dominant category in the actions area (§4.1, §4.2). The smaller stream of **system-decision actions** shares the same area with visual distinction:

- Predictor retirement decisions (`docs/intent/prediction-diary-and-calibration.md` §5)
- Shadow-predictor promotion decisions (`docs/intent/predictor-lifecycle.md` §4)
- Reconciliation D-class items (`docs/intent/reconciliation.md` §3)
- Settings warnings (e.g. EODHD tier conflict with a feature toggle)
- Audit exceptions (e.g. hash-chain break detected)

Each system-decision item is a single row with a clear question and the user's decision options inline. No separate inbox; they appear and disappear like order rows.

## 7. Update cadence

- **07:00 morning evaluation.** Full evaluation from scratch (doctrine §7). Yesterday's unactioned suggestions do *not* carry over. The morning chain is blocked by the mandatory 07:00 reconciliation (`docs/intent/reconciliation.md` §1).
- **Hourly during the day.** Lighter evaluations append silently to the suggested orders grid as new signals appear. No notifications. (doctrine §8)
- **Open orders grid.** Real-time via the hybrid sync model (§4.2; doctrine §6). Not on a cadence.
- **Performance review screen.** User-initiated. Not periodic. (doctrine §11)

## 8. Performance review (separate screen)

A separate screen, not the dashboard. The user visits it when they choose to. (doctrine §11) See `docs/reality/functionality/performance-review.md` (T-021b) for the screen spec.

Shows:
- Time-weighted return vs benchmark
- Drawdown from peak
- Volatility / risk-budget usage
- Exposure breakdown: asset class, sector, currency
- Portfolio chart
- Weekly and monthly views

Deliberately not on the dashboard. The intent is to support deliberate weekly/monthly review, not encourage daily emotional reactions.

## 9. Audit trail (separate screen)

A separate screen, not the dashboard. Append-only, immutable. (doctrine §12)

Every state transition is recorded:
- Suggestion generated
- Suggestion approved / edited / rejected (with reason; with both original and edited per-field values when edit-as-override applies)
- Order parked in IBKR (system-originated or manual)
- Parked order edited
- Parked order approved for submission / cancelled
- Order filled (partial or full — every partial recorded distinctly)
- Sync events
- Mode changes (paper ↔ real connection changes)
- Reconciliation events (B/C/D/E with classification and threshold context)

Each entry references the IBKR-side identifiers where applicable, so any event can be traced back to its IBKR record.

## 10. AI usage on the dashboard (doctrine §13)

- The explanation icon (§4.1) is the primary surface for AI output on the dashboard.
- AI explains, never decides. AI does not choose quantities, prices, order types, TIF, or any other order field. AI does not approve, reject, or modify IBKR state. (doctrine §13)
- Every AI output is schema-validated.
- AI usage is bounded by the existing `claude_ai_budget` cap, extended to multi-provider in v1 (`docs/intent/ai-usage.md` §4).

## 11. Open design questions

Bear directly on this spec:

- **Stop-loss derivation method.** Needed by §5.1 (Kelly base).
- **Forecast confidence score definition.** Needed by §5.1 (conviction scaling).
- **Mid-price disagreement threshold for forecast override.** Needed by §5.3.
- **Polling intervals when the event stream is unhealthy.** Needed by §4.2 / doctrine §6.
- **Watchlist proximity-to-action signal definition.** Needed by §3.
- **Bracket order policy.** When and how stop-loss / take-profit pairs are auto-attached. Affects §5.2 and §5.3.
- **Exact freshness windows per input type for the trust signal.** Needed by §4.1.
- **Initial population of rejection classification mapping.** Needed by §4.3.

All of the above are tracked in doctrine §15.

---

**Doctrine:** `docs/intent/_trading-system-doctrine.md`
**Phase 1 tasks that consume this spec:**
- `T-008` — Reality docs for the frontend (pages, shared components, feature grids)
- `T-011c` — Reality doc `dashboard-composition.md`
- `T-013` — Reality doc `ibkr-readonly-sync-positions-cash.md`
- `T-018` — Reality doc `action-draft-composition-and-approval.md`
- `T-025` — Reality doc `user-confirm-starter-watchlist.md`
- `T-026` — Reality doc `user-approve-action-draft.md`
- `T-029` — Reality doc `user-edit-trading-settings.md`
- `T-030` — Reality doc `user-review-decision-package-detail.md`
