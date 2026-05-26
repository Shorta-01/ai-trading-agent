# 0002 — Adopt the trading-system doctrine

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** paper-only language listed in `docs/intent/_trading-system-doctrine.md` §14
- **Superseded by:** —
- **References:** `docs/intent/_trading-system-doctrine.md`

## Context

The repository's earliest framing scoped the AI Trading Agent as a paper-only research and decision-support tool. README.md and AGENTS.md carried explicit prohibitions: "Versie 1 werkt uitsluitend met papergeld", "Geen live trading", "Do not implement live trading", "Do not add broker execution in version 1", "Do not add IBKR live order flow".

Over time, the product's actual intent diverged from that framing. Task 126 retired the V1-paper-only enforcement (see `docs/product/locked-decisions.md` "Retired locks"), and the locked-decisions register has since assumed account-mode-aware behaviour with both paper and real-money accounts as first-class. Subsequent task locks (133/134/135) describe a full submission lifecycle, behavioural guardrails, reconciliation, and an Action Center — none of which fit a paper-only framing.

The mismatch surfaced concretely during the T-013 functional review on 2026-05-26 (`ibkr-readonly-sync-positions-cash.md`), where the reality of how the system relates to IBKR could not be cleanly described against guardrails that still forbade live trading. Continuing without a written doctrine would leave each future task arguing the same point from scratch and would leave AGENTS.md actively prohibiting work the user wants done.

## Decision

Adopt the doctrine defined in `docs/intent/_trading-system-doctrine.md`.

The intent file is the live, referenceable spec — every functional, architectural, and code-health decision must be consistent with it. This decision record captures the moment of adoption and the rationale; it does not duplicate the doctrine body. Updates to the doctrine after adoption are made in the intent file and logged either by a follow-up decision record (when material) or by a normal commit (when editorial).

## Alternatives considered

- **Keep the paper-only restriction and defer trading capability to v2.** Rejected because the user's current intent already treats real-money trading as the system's purpose, and the locked-decisions register (Tasks 126–135) has been built on that assumption for weeks. Reasserting paper-only would invalidate work already accepted.
- **Add trading capability without a written doctrine.** Rejected because subsequent intent docs (dashboard, action draft, reconciliation, sizing) and Phase 1 reality and gap tasks all need one referenceable source. Without it every task would re-derive the same product framing.
- **Write the doctrine but leave AGENTS.md and README contradicting it.** Rejected because Claude Code sessions reading the guardrails would treat them as binding and refuse to act on the new intent. AGENTS.md must be coherent with the intent it governs.

## Consequences

- The system is now scoped as a full trading system. Subsequent Phase 1 reality tasks describe existing code against this doctrine and surface gaps where the code does not yet implement what the doctrine specifies.
- `AGENTS.md` and `README.md` updated: the superseded prohibitions are removed; the doctrine is referenced as the top-level governance.
- Phase 4 brainstorming will queue the code work implied by the doctrine. The doctrine itself does not generate tasks directly; concrete tasks come from gap analysis and brainstorming.
- Where doctrine §15 leaves a question open (stop-loss derivation, forecast confidence definition, mid-price-override threshold, polling intervals, watchlist proximity signal, bracket policy, FX policy), those answers are added as further intent documents under `docs/intent/` and referenced back from §15 once they exist.

## Tasks generated

None directly. Tasks derived from this doctrine are queued separately through Phase 1 gap analysis and Phase 4 brainstorming.
