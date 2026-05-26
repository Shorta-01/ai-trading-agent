# 0011 — Adopt the portfolio-valuation architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/portfolio-valuation.md`, `docs/intent/belgian-tax.md`, doctrine §10 and §11, §15.

## Context

T-021 (`portfolio-valuation-and-cost-basis.md` reality) raised three coupled questions:

1. How are lots stored, and how does the user-preferred display method interact with the tax-calculation method?
2. Which use sites legitimately need different valuation inputs (live vs last-close, execution vs period-end FX)?
3. How is currency exposure tracked when the portfolio holds non-EUR positions?

Without an authoritative valuation-by-purpose table, every use site would re-derive its own price/FX choice and the system would silently disagree with itself.

## Decision

Adopt the architecture defined in `docs/intent/portfolio-valuation.md`:

- **Always store individual lots.** Lot granularity is the floor; aggregation is reporting.
- **Display method is a reporting choice**, configurable per user (default: weighted average cost; alternatives FIFO, Specific Lot ID).
- **Tax calculation method is separate from display.** Tax uses the legally-correct method per asset class (Belgian jurisdictional mapping in `docs/intent/belgian-tax.md`).
- **Valuation-by-purpose table** (normative): dashboard portfolio = last close; decision package sizing context = live mid-price; performance review = last close; exposure calcs = last close; tax period valuation = last close; tax disposal events = actual execution price; audit log = whichever was used, captured explicitly.
- **Currency:** convert for display, track currency exposure separately; storage retains both local and EUR per position.
- **Hedging deferred.**

## Alternatives considered

- **Aggregate lots into a single weighted-average position in storage.** Rejected: irreversible. The system would not be able to recompute FIFO or specific-lot for tax purposes once the granularity is lost.
- **Use live prices everywhere.** Rejected: feeds noise into performance reporting and tax calculations. Live is only correct at the moment of execution / pricing-the-ticket.
- **Auto-hedge FX exposure.** Rejected: out of scope for v1. Currency exposure is shown; the user decides.

## Consequences

- T-021 reality describes existing valuation code against this intent.
- The valuation-by-purpose table becomes a hard reference for every screen and module that displays a value.
- Display-method preference moves to Category 2 of `docs/intent/settings-and-credentials.md`.
- Open questions (per-currency Kelly cap, accrued dividends, corporate actions, hedging policy) remain doctrine §15.
