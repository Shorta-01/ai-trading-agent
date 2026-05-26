# Dashboard and order flow — intent

**Status:** locked
**Locked on:** 2026-05-26 (with doctrine `_trading-system-doctrine.md`)
**Doctrine:** `docs/intent/_trading-system-doctrine.md`
**Scope:** screen-level spec for the morning dashboard and the order lifecycle. Referenced by upcoming reality and workflow tasks (T-008, T-013, T-018, T-025, T-026, T-029, T-030).

This document is prescriptive: it states how the dashboard and order flow are intended to work. Where it leaves a question open, the question is listed in §10 with a pointer to the doctrine section that needs it.

## 1. Dashboard composition

- Three areas only: portfolio, watchlist, actions. No fourth area. (doctrine §10)
- A single system-health line at the very top of the dashboard. One line. Green when healthy and visually quiet; red when degraded and visually loud. Reflects sync status, data freshness, and IBKR connectivity. (doctrine §10)
- A visually unmistakable PAPER / REAL MONEY badge. Never ambiguous, never hidden, never styled subtly. PAPER = yellow or equivalent; REAL MONEY = red or equivalent. A glance answers which mode is active. (doctrine §3.1)
- Forbidden on the dashboard: charts, news feed, sentiment ticker, market overview, notifications panel, past-actions history. Those belong on dedicated screens. (doctrine §10)
- When the actions area is empty, a one-line explanation states *why* it is empty (e.g. "watchlist stable, portfolio within target ranges, no forecast triggered a signal"). Empty without explanation is forbidden. (doctrine §10)

## 2. Portfolio area

- Sourced from IBKR. The dashboard reflects what IBKR currently reports. (doctrine §2)
- Each row shows position-level current value.
- No daily P&L on the dashboard. No daily change colouring. No totals delta. (doctrine §10)
- Daily P&L is deliberately not surfaced anywhere as a headline metric — neither here nor on the performance screen — to discourage emotional reactions to single-day moves. (doctrine §11)
- Performance metrics live on a separate Performance Review screen, not the dashboard (§7 below).

## 3. Watchlist area

- Items being tracked but not held.
- Each item shows an inline "proximity to action" signal — a small badge or colour cue indicating how close the asset is to triggering a buy suggestion. (doctrine §10)
- The exact definition of the proximity signal (what inputs feed it, what thresholds map to which states) is open and will be defined in T-018 and follow-up brainstorming. See §10 below.

## 4. Actions area — the two-grid model

The actions area contains two distinct grids, each with its own approval action. Approving in the first grid is *not* the same as approving in the second. (doctrine §4)

### 4.1 Suggested orders grid

- System-generated order tickets, IBKR-shaped, with every field pre-filled. (doctrine §4.1, §5)
- Per-row trust signal, inline: forecast confidence + data freshness. Not in a separate side panel.
- Per-row explanation icon. Clicking it reveals plain-language rationale for the proposed order:
  - What the forecast says
  - What data drove it (sources, freshness)
  - What risk and sizing logic produced the field values
  - Which of the three sizing layers (Kelly base, conviction scaling, hard caps — see §5.1) was binding for this order
  - What alternatives were considered, if any
- User actions on a suggested row:
  - **Approve as-is.** The order is parked in IBKR. It does *not* go to the market.
  - **Edit then approve.** Edited fields are validated client-side instantly (§5.6). The full IBKR `whatIfOrder` validation runs once when the user presses Approve. On success the order is parked in IBKR; on rejection the order is blocked and the reason is shown.
  - **Reject.** Optional one-word reason (cash / risk / personal / other), logged silently for later pattern analysis. The order never reaches IBKR. (doctrine §4.1)
- Recurrence counter, inline. When the same suggestion (same asset, same direction, similar size) appears on consecutive days, the row shows a counter ("3rd time this week"). Informational only — no snooze, no permanent dismissal, no "reject for a week". Every day evaluates fresh. (doctrine §9)

### 4.2 IBKR todo grid

- A live view of IBKR's current order book. Whatever IBKR currently holds is what this grid shows. (doctrine §4.2)
- Includes orders from any origin (system-originated *and* orders placed manually by the user inside IBKR or TWS). The grid does *not* distinguish them — IBKR is the source of truth and the grid mirrors it without origin badges, without edit-history flags, without a recently-filled section.
- Sync model: hybrid push/pull (event-driven subscription primary; periodic polling fallback). The system-health line (§1) reflects which mode is currently active. (doctrine §6)
- User actions on an IBKR-todo row:
  - **Approve.** Submits the order to the market. This is the *real* submission. (doctrine §4.2)
  - **Edit then approve.** Edits are pushed to IBKR via the modify-order API. The full IBKR `whatIfOrder` validation re-runs before the second approve. (doctrine §5.5)
  - **Cancel.** Deletes the order from IBKR's order book. (doctrine §4.2)

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
- **Forecast override:** when the system's forecast-implied fair value disagrees materially with the mid-price (threshold to be defined — see §10), the forecast value overrides the patient-liquidity default.

The explanation icon must show which logic was used (patient liquidity vs forecast override) and why.

### 5.4 Time-in-force (doctrine §5.4)

- **Default:** DAY, always. Unfilled orders auto-cancel at market close.
- **GTC and GTD:** available only via a "show advanced" toggle (§5.5). Never the system's default.
- This aligns with the morning evaluation rule (§6 below; doctrine §7): every day evaluates fresh, so a persistent open order is in tension with the model and must be a deliberate user override.

### 5.5 Ticket UI: progressive disclosure

- **Minimal view (default):** symbol (read-only), action (read-only), quantity (editable), order type (editable), limit price if applicable (editable), TIF (editable).
- **"Show advanced" toggle:** reveals the full IBKR field set.
- All other fields use system-set sensible defaults until the user expands advanced.

### 5.6 Validation (doctrine §5.5)

- **Client-side, instant:** cheap rules (positive numbers, valid symbol, lot-size multiples, valid TIF values, etc.) checked in the browser as the user edits.
- **IBKR round-trip on Approve:** `whatIfOrder` runs once when the user presses Approve. Returns margin impact, commission estimate, and any rejection reason.
- If IBKR rejects, submission is blocked and the rejection reason is shown to the user.
- This applies in both grids — the first approve (suggested → IBKR parked) and the second approve (IBKR parked → market).

## 6. Update cadence

- **07:00 morning evaluation.** Full evaluation from scratch: refresh prices, refresh FX, refresh IBKR positions, recompute valuations, generate forecasts, build decision packages, populate the suggested orders grid for the day. Yesterday's unactioned suggestions do *not* carry over. (doctrine §7)
- **Hourly during the day.** Lighter evaluations append silently to the suggested orders grid as new signals appear. No notifications, no interruptions, no badges that demand attention. The user checks when they choose to. (doctrine §8)
- **IBKR todo grid.** Real-time via the hybrid sync model (§4.2; doctrine §6). Not on a cadence.
- **Performance review screen.** User-initiated. Not periodic. (doctrine §11)

## 7. Performance review (separate screen)

A separate screen, not the dashboard. The user visits it when they choose to. (doctrine §11)

Shows:
- Time-weighted return vs benchmark
- Drawdown from peak
- Volatility / risk-budget usage
- Exposure breakdown: asset class, sector, currency
- Portfolio chart
- Weekly and monthly views

Deliberately not on the dashboard. The intent is to support deliberate weekly/monthly review, not encourage daily emotional reactions.

## 8. Audit trail (separate screen)

A separate screen, not the dashboard. Append-only, immutable. (doctrine §12)

Every state transition is recorded:
- Suggestion generated
- Suggestion approved / edited / rejected (with reason)
- Order parked in IBKR (system-originated or manual)
- Parked order edited
- Parked order approved for submission / cancelled
- Order filled (partial or full)
- Sync events
- Mode changes (paper ↔ real connection changes)

Each entry references the IBKR-side identifiers where applicable, so any event can be traced back to its IBKR record.

## 9. AI usage on the dashboard (doctrine §13)

- The explanation icon (§4.1) is the primary surface for AI output on the dashboard.
- AI explains, never decides. AI does not choose quantities, prices, order types, TIF, or any other order field. AI does not approve, reject, or modify IBKR state. (doctrine §13)
- Every AI output is schema-validated.
- AI usage is bounded by the existing `claude_ai_budget` cap.

## 10. Open design questions

The items below come from doctrine §15 and bear directly on this spec. Each will be resolved in a follow-up intent document and back-referenced from the doctrine and from this file.

- **Stop-loss derivation method.** Needed by §5.1 (Kelly base).
- **Forecast confidence score definition.** Needed by §5.1 (conviction scaling).
- **Mid-price disagreement threshold for forecast override.** Needed by §5.3.
- **Polling intervals when the event stream is unhealthy.** Needed by §4.2 / doctrine §6.
- **Watchlist proximity-to-action signal definition.** Needed by §3.
- **Bracket order policy.** When and how stop-loss / take-profit pairs are auto-attached. Affects §5.2 and §5.3.

---

**Doctrine:** `docs/intent/_trading-system-doctrine.md`
**Phase 1 tasks that consume this spec:**
- `T-008` — Reality docs for the frontend (pages, shared components, feature grids)
- `T-013` — Write `ibkr-readonly-sync-positions-cash.md`
- `T-018` — Write `action-draft-composition-and-approval.md`
- `T-025` — Write `user-confirm-starter-watchlist.md`
- `T-026` — Write `user-approve-action-draft.md`
- `T-029` — Write `user-edit-trading-settings.md`
- `T-030` — Write `user-review-decision-package-detail.md`
