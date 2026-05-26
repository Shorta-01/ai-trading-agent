# Data sources — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0005-data-sources-doctrine.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§15)

## Scope

This document defines what data sources the system uses, when, and why the split exists.

## 1. Two-source split

The system uses two distinct data sources, each optimal for a different purpose:

- **Research data (EODHD All-In-One tier, €99.99 / month).** Covers EOD prices, intraday, fundamentals, news, earnings calendar. Consumed by the morning chain (07:00) and the hourly refresh (08:00–20:00) to drive forecasts, calibration, and decision-package composition.
- **Execution data (IBKR live quotes — bid / ask / last).** Used only at the moment of order ticket construction, on-demand per ticket. No periodic polling. No extra cost beyond the standard IBKR account.

## 2. Rationale for the split

Brokers and data vendors are good at different things:

- **Brokers are excellent at execution data** — millisecond-fresh bid/ask, accurate on the moment of trade. They are **bad at research data**: rate-limited, no fundamentals, no earnings calendar, expensive per-exchange subscriptions, sparse history.
- **Data vendors are excellent at research data** — wide history, fundamentals, calendar events, normalisation across exchanges. They are **bad at execution-latency data**: end-of-day for most tiers, no live quotes for most plans, no order book.

Using each for its strength keeps cost low and quality high.

## 3. Cost

Marginal data cost: **~€100 / month** (EODHD All-In-One subscription). IBKR live quotes ship with the account.

## 4. Why not free alternatives

Considered and rejected for v1 real-money production:

- **yfinance** — unofficial scraper; rate-limited, no SLA, breaks without notice.
- **Alpha Vantage free tier** — 25 calls/day, useless for a watchlist of ~50 instruments.
- **Stooq** — EOD only, no fundamentals, sparse coverage outside US/PL.
- **FRED** — macro data only; we need per-instrument.
- **ECB data** — FX rates only.

These are fine for prototyping but cannot underpin a system that places real orders against real money.

## 5. Pattern at use sites

- **Morning chain (07:00):** batched EODHD requests against the watchlist + positions. Output stored in `market_data_snapshots` (per existing storage schema).
- **Hourly refresh (08:00–20:00):** narrower EODHD requests for assets with active suggestions or open watchlist proximity-to-action triggers.
- **Order ticket construction:** just-in-time IBKR live quote request for the specific instrument the user is approving. One request per ticket render; cached for the lifetime of the ticket modal.

## 6. Cross-references

- Doctrine §6 (synchronisation — IBKR-driven for execution data)
- Doctrine §15 (open questions)
- `docs/intent/forecast-engine.md` (EODHD tier dependency for fundamentals + calendar)
- `docs/intent/settings-and-credentials.md` (EODHD API key and tier in Category 1; data feature toggles in Category 2.1)
- `docs/intent/decision-package.md` (where research and execution data meet)
