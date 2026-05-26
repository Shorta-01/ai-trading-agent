# 0005 — Adopt the data-sources doctrine

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/data-sources.md`, doctrine §6, §15.

## Context

T-014 (`market-data-pipeline.md`, formerly `market-data-eod-and-fx-snapshots.md`) and the broader discussion of where the system gets its data revealed an implicit assumption with no written rule: research data comes from EODHD, execution data from IBKR. Without writing this down, future tasks would re-derive the split or — worse — drift to a single-source model that's wrong for at least one of the two roles.

## Decision

Adopt the two-source split defined in `docs/intent/data-sources.md`:

- **Research data: EODHD All-In-One tier** (€99.99 / month). EOD + intraday + fundamentals + news + earnings calendar. Consumed by the morning chain (07:00) and the hourly refresh.
- **Execution data: IBKR live quotes** (bid/ask/last). Used only at the moment of order ticket construction, on-demand per ticket. No periodic polling. No extra cost beyond standard IBKR account.

## Alternatives considered

- **Single-source via IBKR for everything.** Rejected: IBKR is rate-limited for research-style queries, lacks fundamentals, and charges per-exchange subscriptions for breadth. Research-quality data is not their product.
- **Single-source via EODHD for everything (including execution).** Rejected: EOD prices are by definition stale for execution; using last-close to set a limit price minutes before market open is exactly the wrong pattern.
- **Free-tier stack (yfinance / Alpha Vantage free / Stooq / FRED).** Rejected for real-money production: rate limits, no SLA, breakage without notice, no fundamentals breadth.

## Consequences

- T-014 reality documents both data flows and how they interact at the use sites.
- T-061 reality reflects the EODHD-tier + API-key settings in Category 1.
- The marginal ~€100/month data spend is acknowledged as the cost of correctness.
- IBKR-live-quote on-demand pattern becomes a hard requirement for order-ticket UX (`docs/intent/dashboard-and-order-flow.md`).
