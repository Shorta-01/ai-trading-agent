# 0007 — Adopt the decision-package architecture

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/decision-package.md`, doctrine §6, §10, §13, §15.

## Context

T-017 (`decision-package-composition.md` reality) had to answer: what is in a decision package, how often is it built, what is its trust contract with the dashboard, and how does AI explanation fit in. The existing Task 132 lock specifies the storage-level decision-package shape and the hash chain, but not the lifecycle, the trust tiers, or the AI-caching strategy. Without those, the dashboard's per-row trust signal and the AI budget interplay can't be designed coherently.

## Decision

Adopt the architecture defined in `docs/intent/decision-package.md`:

- **Contract:** identity, market state (last close), forecast snapshot with per-predictor contributions, portfolio context, risk and sizing context, suggested action with pre-filled IBKR ticket and binding sizing layer and recurrence info, AI explanation (lazy + cached), audit pointers.
- **Build cadence:** full rebuild at 07:00 morning chain; delta rebuild hourly during the day with explicit triggers; selective on-demand refresh at order ticket render (uses live IBKR quote).
- **Three-tier trust model.** Full / degraded / minimal, surfaced via the per-row trust signal on the dashboard.
- **Critical vs non-critical inputs.** Critical = forecast, market price, IBKR position freshness, calibration. Non-critical = AI explanation, recurrence info, audit pointers, sector exposure metadata.
- **AI explanation is lazy + cached.** Generated on first explanation-icon click; cached against `decision_package_id`; invalidated on rebuild.
- **Trust level never lied about.** AGENTS.md "no silent data correction" preserved.

## Alternatives considered

- **Eager AI explanation generation** (at decision-package composition time). Rejected: most packages are never opened. Eager generation would burn the per-provider AI budget on outputs no human reads.
- **Single trust state (healthy / unhealthy)**, not three tiers. Rejected: the degraded state is genuinely different from minimal — degraded means "you can trust the action, but the explanation may be sparse"; minimal means "do not act on this until critical inputs are restored". Collapsing them loses signal.
- **Decision packages mutable.** Rejected: violates Task 132's append-only / hash-chained model. Every rebuild produces a new package.

## Consequences

- T-017 reality describes existing decision-package composition against this intent.
- Dashboard trust signal (doctrine §10 revision) reads the package's trust tier.
- AI budget behaviour (`docs/intent/ai-usage.md`) accounts for the lazy-explanation pattern.
- Delta-rebuild change triggers depend on doctrine §15 open thresholds (price-move trigger, freshness windows per input type).
