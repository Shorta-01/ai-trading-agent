# Belgian tax — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0012-belgian-tax-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§15)

## Scope

This document specifies what the system computes for Belgian tax purposes, what it records, and what it produces (annual report). It also lists which tax-aware behaviours are in v1, which are Phase 4 candidates, and which are deferred indefinitely.

Authoritative responsibility for filing the tax return remains with the user and their accountant. The system supports the accountant; it does not replace one.

## 1. Tiered compute/record approach

Two operations exist: **compute** (the system derives a value with deterministic Python math) and **record** (the system stores facts that an accountant will interpret).

### Compute

- **TOB per transaction.** Tax on stock exchange transactions, computed at the moment of execution from the executed notional, the instrument's TOB-rate-class, and the rules locked at the time of execution.
- **Total TOB for the year.** Sum of per-transaction TOB.
- **Withholding tax actually withheld per dividend.** From the IBKR dividend event payload.
- **Total withholding for the year.** Sum.
- **Per-disposal realized gain/loss in EUR.** Disposal price × quantity, less acquisition cost (per the legally-correct method per asset class — see `docs/intent/portfolio-valuation.md` §3), in EUR using the execution-time FX rate.

### Record (not compute)

- **Reynders bond-component data per disposal.** Bond fund classification + per-disposal bond-share data. The system stores; the accountant decides if the trade qualifies and at what split.
- **Capital gains classification context.** Trade count, turnover, holding-period distribution. Inputs to "speculative classification" determination; the system does not classify.
- **Foreign withholding reclaim eligibility data.** Treaty rate vs withheld rate per dividend; whether the asset's domicile has a Belgium tax treaty applicable.
- **Annual securities account tax data.** Only relevant if portfolio crosses €1M average; the data is captured regardless so the threshold check is deterministic.

## 2. Recording standard: accountant-grade

The recording standard is **accountant-grade**: sufficient for a Belgian accountant to file the return without coming back with data questions. Every recorded item carries source references (IBKR event ID, audit-log entry ID).

## 3. Annual report — eight sections

PDF output with eight sections (sections 1–7) plus a CSV pack (section 8):

1. **Transactions and TOB.** Per-transaction list with TOB applied and total.
2. **Dividends and withholding.** Per-dividend list with withholding applied and total.
3. **Realized gains/losses.** Per-disposal list with computed gain/loss in EUR.
4. **Capital gains classification risk indicator.** Summary stats (trade count, turnover, average holding period) plus a non-binding "speculative pattern present? yes/no/borderline" flag. The user is told this is informational only; the accountant decides.
5. **Reynders disposals.** Per-disposal Reynders-applicable data with bond-component values recorded.
6. **Year-end position and currency exposure.** Holdings at 31 Dec by instrument, asset class, sector, currency.
7. **Foreign-source income summary.** Per-source-country breakdown of dividends and withholding, with treaty-rate notes.
8. **Supporting CSV exports.** Raw data behind sections 1–7 in machine-readable form.

### Report properties

- **Format:** PDF (sections 1–7) + CSV files (section 8).
- **Language:** Dutch.
- **Generation:** annually at year-end (configurable default: late January).
- **On-demand availability:** from Category 5 of `docs/intent/settings-and-credentials.md` ("on-demand annual tax report generation").
- **Versioning:** versioned and dated. Re-runs regenerate from current data; **previous reports are retained in the audit log**, never overwritten.

## 4. Tax-aware suggestions in v1

Two behaviours are in scope:

- **TOB-aware suggestions.** The expected return from a suggestion is computed **net of expected TOB**. A trade with a negative net expected return after TOB is not suggested. TOB is treated as a real cost on every BUY/SELL, not a footnote.
- **Speculative-classification awareness.** The system tracks live trade count and turnover. When the rolling totals approach the pattern thresholds (Category 3 settings, see `docs/intent/settings-and-credentials.md`), the system surfaces a **system-decision item** in the actions area (doctrine §10): "Activity approaching speculative-classification pattern. Review with accountant." The user decides; the system does not block trading.

## 5. Phase 4 evolution candidates

- **Lot-selection optimization.** Choosing which lot to dispose of (where the user's accountant permits flexibility) to minimise tax.
- **Tax-loss harvesting (if Belgian capital gains become taxable for the user).** Currently most Belgian retail investors are not subject to capital gains on standard equity disposals; this would change if the user is reclassified as speculative. The system would propose offsetting trades.
- **Year-end position adjustment suggestions.** E.g. selectively realising losses before 31 Dec.

## 6. Deferred indefinitely

- US-style standard tax-loss harvesting (different jurisdiction, different rules).
- Wash-sale avoidance (not a Belgian concept in the same form).

## 7. Open questions

- Tax rules versioning and annual update mechanism (doctrine §15) — TOB rates and Reynders thresholds change; the system needs a versioning model.
- Speculative-classification threshold defaults (doctrine §15) — require accountant review before being locked.
- Fund classification storage (Reynders-applicable) (doctrine §15) — system-stored vs accountant judgment per disposal.

## 8. Cross-references

- Doctrine §15 (open questions)
- `docs/intent/portfolio-valuation.md` (tax calculation method per asset class; valuation-by-purpose disposal row)
- `docs/intent/settings-and-credentials.md` (Category 3: speculative thresholds; Category 5: on-demand report)
- `docs/intent/dashboard-and-order-flow.md` (system-decision items appear in the actions area)
- Existing locked decision: `docs/product/locked-decisions.md` "Task 16) Belgische tax/compliance"
