# 0010 — Adopt the reconciliation architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/reconciliation.md`, doctrine §6 and §10, §15.

## Context

T-020 (`ibkr-reconciliation-passes-a-b-c.md` reality) and the doctrine §6 update needed to answer:

1. How often does reconciliation run?
2. What is the relationship to the morning chain?
3. How are discrepancies classified, and what does the system do with each class?
4. What is the user-facing surface, if any?
5. What is **not** in scope for reconciliation?

The Task 135 product lock specifies the three passes (A/B/C) but not the periodic cadence, the discrepancy-classification model, or the system-decision surface for D-class items.

## Decision

Adopt the reconciliation architecture defined in `docs/intent/reconciliation.md`:

- **Hybrid cadence.** Periodic baseline every 15 min during market hours, every hour outside; plus event triggers (07:00 before morning chain — mandatory blocking; after fills; after IBKR reconnect; on user demand).
- **Four-tier discrepancy classification.** B/C/D/E (A explicitly forbidden by AGENTS.md "no silent data correction"). B/C auto-correct with audit log; D blocks downstream and surfaces as system-decision item; E halts order generation and data writes.
- **Default classification table per pass** with configurable thresholds in Category 3 settings.
- **Three non-scope rules.** No back-fill of audit log entries; no retroactive rebuild of decision packages; no auto-retry indefinitely (max 3 attempts, then fail loudly).
- **User-initiated reconciliation** in v1 = same as periodic, immediate.

## Alternatives considered

- **Single-tier "any discrepancy is a halt".** Rejected: rounding-level drift would halt the system constantly. Tiered classification matches reality.
- **Auto-correct any discrepancy without audit-logging it.** Forbidden by AGENTS.md "no silent data correction"; not really an option.
- **Reconciliation as the primary sync, with event-stream as a "nice to have".** Rejected: reverses doctrine §6. Event-stream is primary because it's real-time; reconciliation is the backstop.
- **Deep mode** (historical fill replay) in v1. Rejected: risk of disrupting the audit chain outweighs benefit. Deferred indefinitely.

## Consequences

- T-020 reality describes existing reconciliation code against this intent.
- T-028 (`user-acknowledge-manual-review.md`) walks the D-class system-decision UX.
- The 07:00 mandatory-blocking rule constrains the morning chain orchestration (T-011).
- Threshold defaults per pass remain doctrine §15 open.
