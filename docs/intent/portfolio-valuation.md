# Portfolio valuation — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0011-portfolio-valuation-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§10, §11, §15)

## Scope

This document specifies how the portfolio is valued: lot storage, display method, the valuation-by-purpose table, and currency handling.

## 1. Lot storage: always individual lots

**Always store individual lots.** Lot granularity is the lowest unit of holding; aggregation is a reporting choice on top of lots.

- Each lot carries: `acquisition_date`, `quantity`, `unit_cost_local`, `unit_cost_eur`, `fx_rate_at_acquisition`, `lot_id`.
- Lots never merge in storage. A "100-share holding of ASML" may be made up of three lots acquired on different dates at different prices; the system never collapses them.
- Disposals deplete specific lots per the active **tax calculation method** (§3), not the display method (§2).

## 2. Display method

Display method is a **reporting choice**, independent of how taxes are computed.

- **Default: weighted average cost.** Configurable in Category 2 of `docs/intent/settings-and-credentials.md`.
- **Alternatives:** FIFO, Specific Lot ID.
- A change of display method is audit-logged with `{user, from_method, to_method, changed_at}`.
- The chosen display method affects only how cost basis is shown in the UI. It does not affect tax computation, P&L for prediction-diary evaluation, or any deterministic logic.

## 3. Tax calculation method: separate from display

Belgian tax law specifies the correct method per asset class; that method is used regardless of the display setting. The full mapping is locked in `docs/intent/belgian-tax.md` (and confirmed by T-022 reality findings).

Hard rule: **tax math uses the legally-correct method, period.** The display preference cannot influence taxes.

## 4. Valuation-by-purpose table

Different uses of valuation legitimately need different inputs. The table below is normative.

| Use case | Price source | FX source | As-of |
|----------|--------------|-----------|-------|
| Dashboard portfolio area | Last close | Last-close FX rate | Trading day close |
| Decision package sizing context | Live mid-price (IBKR on-demand) | Same | Moment of ticket render |
| Performance review (historical and current) | Last close | Last-close FX rate | Trading day close |
| Exposure calculations (per-position %, per-sector %, etc.) | Last close | Last-close FX rate | Trading day close |
| Belgian tax period valuation | Last close | Last-close FX rate | Period boundary (e.g. 31 Dec) |
| Belgian tax disposal events | **Actual execution price** | **Actual execution-time FX rate** | Disposal timestamp |
| Audit log entries | Whichever was used | Whichever was used | Captured explicitly |

The audit log always captures **which** price/FX was used; the table above sets defaults at each use site.

## 5. Currency handling

- **Display:** convert to base currency (default EUR; configurable in Category 2).
- **Storage:** retain both local and EUR per position. The storage layer never co-mingles local and EUR (per existing market-data snapshot Task 129 lock).
- **Currency exposure:** tracked separately and shown on the performance review screen as a first-class dimension (doctrine §11).

## 6. Currency hedging: deferred

v1 does not hedge FX exposure programmatically. The user sees currency exposure on the performance review screen; if they want to hedge, they place orders manually. Programmatic hedging is doctrine §15 open (multi-currency reporting and FX hedging policy).

## 7. Accrued dividends

Handling of accrued dividends in valuation is doctrine §15 open. v1 default: accrued dividends are **not** added to position value on the dashboard (consistent with brokers' standard mark-to-market practice). Belgian tax module records dividend events when they pay.

## 8. Corporate actions

Splits, mergers, and special dividends are doctrine §15 open — never explicitly designed in this project. v1 relies on IBKR's adjustment; the system reconciles against IBKR truth (doctrine §2) and surfaces any discrepancy through reconciliation D-class items (`docs/intent/reconciliation.md`).

## 9. Open questions

- Per-currency hard cap in Kelly sizing (doctrine §15)
- Accrued dividend handling in valuation (doctrine §15)
- Corporate actions handling (doctrine §15)
- Currency hedging policy (doctrine §15)

## 10. Cross-references

- Doctrine §10 (dashboard portfolio area uses last-close)
- Doctrine §11 (performance review screen)
- Doctrine §15 (open questions)
- `docs/intent/belgian-tax.md` (tax computation method per asset class)
- `docs/intent/decision-package.md` (sizing context uses live mid)
- `docs/intent/data-sources.md` (live IBKR quote on demand)
- `docs/intent/settings-and-credentials.md` (display method preference in Category 2)
- `docs/intent/reconciliation.md` (corporate-action discrepancies surface via D-class)
