# 0012 — Adopt the Belgian-tax architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/belgian-tax.md`, `docs/intent/portfolio-valuation.md`, doctrine §15.

## Context

T-022 (`belgian-tax-computation.md` reality) surfaced that the existing `portfolio.belgian_tax` module covers some of the TOB + dividend cases but does not yet have a written rule for what to **compute** (deterministic math) vs **record** (facts an accountant interprets). Without that line, the module would expand ad hoc, the annual report wouldn't be designable, and tax-aware suggestion behaviour couldn't be specified safely.

## Decision

Adopt the architecture defined in `docs/intent/belgian-tax.md`:

- **Tiered compute/record approach.**
  - Compute: TOB per transaction + year-total; withholding actually withheld per dividend + year-total; per-disposal realized gain/loss in EUR.
  - Record: Reynders bond-component data per disposal; capital gains classification context (trade count, turnover, holding-period distribution); foreign withholding reclaim eligibility data; annual securities account tax data.
- **Recording standard: accountant-grade.** Sufficient for the user's Belgian accountant to file without coming back with data questions.
- **Annual report: eight sections** (PDF sections 1–7 + CSV pack section 8). Dutch language. Generated annually (configurable default: late January). Available on-demand from Category 5 settings. Versioned and dated; previous reports retained in the audit log.
- **Tax-aware suggestions in v1:**
  - TOB-aware suggestions: net expected return computed including TOB; negative net is not suggested.
  - Speculative-classification awareness: tracking of trade count and turnover; surfaces system-decision item when approaching pattern thresholds. User decides; system does not block.
- **Phase 4 evolution candidates:** lot-selection optimization, conditional tax-loss harvesting, year-end position adjustment suggestions.
- **Deferred indefinitely:** US-style tax-loss harvesting; wash-sale avoidance.

## Alternatives considered

- **Compute everything (including Reynders classification).** Rejected: Reynders bond-component classification depends on the fund's actual bond share at the disposal moment, which the system cannot reliably derive without external data the user's accountant has. Recording the data and leaving the call to the accountant matches legal reality.
- **Block trades that approach the speculative-classification pattern.** Rejected: speculative classification is an after-the-fact accountant call, not a hard system rule. Surfacing as a system-decision item respects user authority.
- **No annual report — let the accountant pull raw data.** Rejected: the cost to the system of formatting eight sections is small; the cost to the user of every accountant request being a data-pull project is large.

## Consequences

- T-022 reality describes existing Belgian-tax code against this intent.
- Category 3 settings host the speculative-classification thresholds (default placeholder; accountant review required before defaults are locked).
- Category 5 settings host the on-demand annual report trigger.
- Open questions: tax rules versioning + annual update mechanism; speculative-classification threshold defaults; Reynders fund classification storage (doctrine §15).
