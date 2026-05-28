# Dashboard Composition — The Contract as a Whole

**Scope.** What the dashboard at `apps/web/app/page.tsx` actually assembles, against intent §1 of `dashboard-and-order-flow.md` — the locked 3-area contract. Distinct from T-008's per-component reality (which documented each widget); T-011c documents the dashboard as an assembled contract + surfaces the intent-vs-reality divergences.

**Carry-forward task** from the 2026-05-26 functional review. The review flagged that the audit needed a doc covering "what the dashboard assembles as a whole" — the contract, not the parts.

## 0. TL;DR — intent contract vs reality

| Intent §1 element | Reality | Status |
|-------------------|---------|--------|
| Three areas only: portfolio + watchlist + actions | Portfolio area present; watchlist + actions areas absent from dashboard | **Partial** |
| Single system-health line at top (worst-state, clickable breakdown) | Multiple separate badges (Scheduler + Calibration) + a "Systeemstatus" panel | **Violation** |
| PAPER / REAL MONEY badge (unmistakable, never hidden) | `<AccountModeBadge>` mounted globally in `layout.tsx:47` | **Honored** |
| Forbidden: charts, news feed, sentiment, market overview, notifications, past-actions | "Portefeuille-evolutie" `<ChartPlaceholder>` present on dashboard | **Violation** (charts forbidden but present) |
| Empty actions area must explain WHY | No actions area exists; placeholder cards say "runtime bestaat nog niet" | **Violation** (out-of-date placeholders) |

**One of five intent-§1 elements fully honored** (the PAPER/REAL badge). The dashboard diverges from the locked contract more than any other surface in the audit.

## 1. Intent §1 — the locked dashboard contract

`docs/intent/dashboard-and-order-flow.md` §1 ("Dashboard composition") is one of the most prescriptive intent sections:

- **"Three areas only: portfolio, watchlist, actions. No fourth area." (doctrine §10)**
- **"A single system-health line at the very top. One line. Reflects the worst current state across all subsystems (sync mode, calibration drift, reconciliation status, last-full-rebuild timestamp, AI budget consumption). Colour reflects worst state... Clicking opens a breakdown." (doctrine §10)**
- **"A visually unmistakable PAPER / REAL MONEY badge. Never ambiguous, never hidden, never styled subtly." (doctrine §3.1)**
- **"Forbidden on the dashboard: charts, news feed, sentiment ticker, market overview, notifications panel, past-actions history. Those belong on dedicated screens." (doctrine §10)**
- **"When the actions area is empty, a one-line explanation states why it is empty... Empty without explanation is forbidden." (doctrine §10)**

## 2. Reality — what `apps/web/app/page.tsx` assembles

The dashboard homepage (`HomePage`, ~135 LOC) composes, top to bottom:

### 2.1 Top badge row (`:67-70`)
- `<SchedulerStatusBadge>` — worker scheduler health.
- `<CalibrationCoverageBadge>` — calibration coverage status.

### 2.2 Forecast day summary (`:71-73`)
- `<ForecastDaySummaryWidget>` — the day's forecast summary.

### 2.3 Reconciliation status (`:74-76`)
- `<ReconciliationStatusWidget>` — the gateway to `/admin/reconciliation` (per T-028 §1).

### 2.4 Metrics grid (`:77-94`) — 6 `<MetricCard>`s
| Card | Source | Value |
|------|--------|-------|
| Totale portefeuillewaarde | `valuationReadiness.total_portfolio_value` (T-021) | Live or "Niet beschikbaar" |
| Dagresultaat | hard-coded | "Niet beschikbaar" — "verschijnt zodra echte gegevens beschikbaar zijn" |
| Totaal resultaat | hard-coded | "Niet beschikbaar" — same |
| Cashwaarde | `valuationReadiness.total_cash_value` | Live or "Niet beschikbaar" |
| Actieve suggesties | hard-coded | "Niet beschikbaar" — "Suggestion runtime bestaat nog niet" |
| Te keuren acties | hard-coded | "Niet beschikbaar" — "Action-draft runtime bestaat nog niet" |

### 2.5 Dashboard layout (`:96-135`) — 4 `<DashboardPanel>`s
| Panel | Content |
|-------|---------|
| Portefeuille-evolutie | `<ChartPlaceholder>` — "verschijnt hier na IBKR-sync en marktdataverwerking" |
| Waardering | valuation StatusCards (market value / cash / conversion) |
| Synchronisatie en status | IBKR sync StatusCard + 4 SyncStatusBadges (accountmodus / marktdata / suggesties / AI-briefing) |
| Systeemstatus | `systemStatus.services` StatusCards |

### 2.6 In the layout (not the page)
- `<AccountModeBadge>` (`layout.tsx:47`) — the PAPER/REAL badge.
- `<ColdStartBanner>` (`layout.tsx:51`) — the cold-start nudge (T-025).

## 3. Intent-vs-reality violations

### 3.1 Charts forbidden but present — **Violation**

Intent §1: "**Forbidden on the dashboard: charts**, news feed, sentiment ticker, market overview, notifications panel, past-actions history."

Reality: the "Portefeuille-evolutie" `<DashboardPanel>` (`page.tsx:97-99`) hosts a `<ChartPlaceholder>` with text "Portefeuille-evolutie verschijnt hier na IBKR-sync en marktdataverwerking." The chart is a placeholder today, but the intent forbids charts on the dashboard at all — they belong on the Performance Review screen (intent §8, the T-021b screen).

The placeholder signals the team intends to put a chart here, which would directly violate the locked contract. The intent doc is explicit that portfolio evolution charts belong on the separate Performance Review screen. §6.1.

### 3.2 No actions area — **Violation**

Intent §1: actions is one of the three mandated areas. Intent §4 details the actions area (suggested orders grid + open orders grid + system-decision items).

Reality: there is **no actions area on the dashboard**. The closest is the "Te keuren acties" metric card (`page.tsx:93`) which is hard-coded "Niet beschikbaar — Action-draft runtime bestaat nog niet". The action drafts surface lives entirely on `/ibkr-acties` (T-026), not the dashboard.

The "Action-draft runtime bestaat nog niet" text is **out of date** — action drafts DO exist (T-018 composer, T-026 approval flow, T-019 submission). Like T-026 §6's "future update" banner, the dashboard card text lags the implementation reality. §6.2.

### 3.3 No watchlist area — **Violation**

Intent §1: watchlist is one of the three mandated areas. Intent §3 details it (items tracked but not held + proximity-to-action signal).

Reality: there is **no watchlist area on the dashboard**. The watchlist lives entirely on `/volglijst` (T-025). The dashboard has no watchlist surface at all. §6.3.

### 3.4 No single system-health line — **Violation**

Intent §1: "A single system-health line at the very top. One line. Reflects the worst current state across all subsystems... Clicking opens a breakdown."

Reality: there is **no single system-health line**. Instead:
- Two separate badges at top (`<SchedulerStatusBadge>` + `<CalibrationCoverageBadge>`).
- A separate "Systeemstatus" panel at the bottom (`page.tsx:122-135`) iterating `systemStatus.services`.
- The reconciliation status is a separate widget (`<ReconciliationStatusWidget>`).
- AI budget consumption (intent §1 lists it as a system-health input) is NOT surfaced anywhere (T-047 §4 — 80/100% thresholds absent).

The intent's "one line, worst-state, clickable breakdown" is unimplemented. The reality scatters subsystem health across ~4 surfaces. §6.4.

### 3.5 PAPER / REAL badge — **Honored**

Intent §1 + §3.1: "A visually unmistakable PAPER / REAL MONEY badge. Never ambiguous, never hidden, never styled subtly."

Reality: `<AccountModeBadge>` is mounted globally in `layout.tsx:47` — visible on every page including the dashboard. Per the PAPER-only architectural lock (T-061 — PAPER→REAL forbidden at 3 layers), the badge reads PAPER. This is the **one intent §1 element fully honored**.

## 4. Why the divergence

The dashboard reality reflects a **build-order artefact**: the dashboard was scaffolded early (Phase 0 / early Phase 1) with placeholder cards + a chart placeholder, before the underlying runtimes (action drafts, suggestions, market data) were built. As those runtimes landed (T-018 action drafts, T-005 suggestions, T-014 market data), the dashboard cards were NOT updated to consume them — they still say "runtime bestaat nog niet".

The result: the dashboard shows a Phase-0-era view of a system that has since grown the runtimes it claims don't exist. The placeholder text is honest about the dashboard's wiring, not about the system's capabilities.

This is the dashboard-level instance of the recurring "UI text lags implementation reality" pattern (T-026 §6 banner, T-027 §5.1 docstring, T-034 §5 banner).

## 5. The forbidden-items check

Intent §1 forbids 6 item types. Reality check:

| Forbidden item | On dashboard? |
|----------------|---------------|
| Charts | **Yes** — `<ChartPlaceholder>` (violation) |
| News feed | No |
| Sentiment ticker | No |
| Market overview | No |
| Notifications panel | No |
| Past-actions history | No |

5 of 6 forbidden items correctly absent. Only charts violate.

## 6. Phase 1c surface (5 findings on the dashboard contract)

1. **Charts forbidden-but-present** (§3.1) — the "Portefeuille-evolutie" ChartPlaceholder violates intent §1's explicit charts-forbidden rule. Charts belong on the Performance Review screen (intent §8 / T-021b). Phase 1c: remove the chart panel from the dashboard OR move it to the perf screen.
2. **No actions area on the dashboard** (§3.2) — intent §1 mandates it as one of 3 areas. Reality: action drafts live on `/ibkr-acties`. The dashboard "Te keuren acties" card is a stale placeholder. Phase 1c: surface the actions area on the dashboard per intent §4, OR amend intent to accept the `/ibkr-acties` page as the actions surface.
3. **No watchlist area on the dashboard** (§3.3) — intent §1 mandates it. Reality: watchlist lives on `/volglijst`. Same decision as #2.
4. **No single system-health line** (§3.4) — intent §1 mandates ONE worst-state line. Reality: ~4 scattered surfaces. AI budget consumption (an intent-listed input) not surfaced anywhere. Phase 1c: build the single system-health line aggregating all subsystem states.
5. **Out-of-date "runtime bestaat nog niet" placeholders** (§3.2, §4) — "Action-draft runtime bestaat nog niet" + "Suggestion runtime bestaat nog niet" cards contradict shipped runtimes (T-018, T-005). Same UI-text-lag pattern as T-026/T-027/T-034. Phase 1c: wire the cards to the live data OR update the text.

## 7. Cross-references

| Concern | Where documented |
|---------|------------------|
| Per-component dashboard reality | T-008 `web-pages.md` + `web-components-status-and-shared.md` |
| Action draft surface (/ibkr-acties) | T-026 |
| Watchlist surface (/volglijst) | T-025 |
| Reconciliation widget → admin page | T-028 §1 |
| Portfolio valuation card data | T-021 §2-§3 |
| AI budget system-health line gap | T-047 §4 |
| PAPER-only architectural lock | T-061 |
| Performance review screen (where charts belong) | T-021b (functional-review addition) |
| UI-text-lags-reality pattern | T-026 §6, T-027 §5.1, T-034 §5 |
| Phase 1c missing actions/watchlist surfaces | T-044 (missing features) |

## 8. Out of scope

- T-008 per-component deep dives (merged sibling).
- Order-flow lifecycle (intent §4-§6; T-018/T-019/T-026).
- Performance review screen spec (T-021b — separate functional-review addition).
- Live valuation data flow (T-021 — merged sibling).

## 9. References

- `apps/web/app/page.tsx:1-135` (the dashboard homepage)
- `apps/web/app/layout.tsx:47` (`<AccountModeBadge>` — PAPER/REAL badge), `:51` (`<ColdStartBanner>`)
- `apps/web/components/` — `SchedulerStatusBadge`, `CalibrationCoverageBadge`, `ForecastDaySummaryWidget`, `ReconciliationStatusWidget`, `MetricCard`, `DashboardPanel`, `ChartPlaceholder`, `StatusCard`, `SyncStatusBadge`, `EmptyState`
- `docs/intent/dashboard-and-order-flow.md` §1 (the locked 3-area contract)
- T-008 `web-pages.md`, `web-components-status-and-shared.md` (component reality)
- T-021 `portfolio-valuation-and-cost-basis.md` (valuation card data)
- T-025 `user-confirm-starter-watchlist.md` (watchlist on /volglijst)
- T-026 `user-approve-action-draft.md` (actions on /ibkr-acties + UI-text-lag pattern)
- T-028 `user-acknowledge-manual-review.md` §1 (reconciliation widget)
- T-044 `01-missing-features.md` (missing actions/watchlist surfaces + performance review)
- T-047 `04-ai-integration-gaps.md` §4 (AI budget system-health line gap)
- T-061 `settings-and-credentials-infrastructure.md` (PAPER-only lock)
