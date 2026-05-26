# 0004 — Adopt the settings and credentials structure

- **Status:** accepted
- **Date:** 2026-05-26
- **Phase:** P1
- **Supersedes:** —
- **Superseded by:** —
- **References:** `docs/intent/settings-and-credentials.md`, doctrine §3, §13, §15.

## Context

The settings and secrets surface had grown organically across `packages/domain/.../settings.py`, `claude_ai_budget.py`, `paper_setup.py`, and ad-hoc `.env` handling. No single doc described what categories exist, how secrets flow, or how a change in one category should propagate. The functional review of 2026-05-26 surfaced that several upcoming tasks (T-018 action-draft safety guards consume cash buffer; T-022 Belgian tax wants the tax-residency setting; T-023 AI usage needs the per-provider budget cap) all assume a settings model that doesn't yet exist on paper.

## Decision

Adopt the five-category settings model defined in `docs/intent/settings-and-credentials.md`:

1. **Connections** (IBKR, EODHD, AI providers, database) — secrets live here.
2. **User preferences** (base currency, tax residency, trading hours, risk profile, default order behaviour, data-feature toggles, system-capability toggles).
3. **Safety limits** (max order value, max orders/day, max exposure, cash buffer, kill switch, whitelist/blacklist, drawdown circuit breaker, calibration / retirement / shadow-promotion thresholds, speculative-classification thresholds).
4. **Monitoring** (critical-alert email, which events qualify, quiet hours).
5. **Audit, backup, observability** (retention, backup destination, frequency, restore-test reminder, on-demand reconciliation / backtest / tax-report triggers).

Seven UX rules apply across categories — grouped UI, test-connection per credential, secrets never re-displayed, apply cadence by category, PAPER→REAL typed confirmation, "show me what changed" diff, export/import encrypted file.

## Alternatives considered

- **Flat list of settings without categories.** Rejected: the apply-cadence and audit-logging rules differ by category; flattening loses that distinction.
- **Encrypted-file storage only (no OS keyring option).** Rejected: portable across machines, but blocks the OS-keyring option for users who prefer that backend. Storage backend choice stays open (doctrine §15).
- **Single global AI provider with hardcoded fallback order.** Rejected: the user needs to choose primary provider and toggle fallback. Per-provider budget caps make this configurable inevitable.

## Consequences

- T-061 (reality of settings + credentials infrastructure) maps existing code against this intent and surfaces gaps.
- Category 3 (safety limits) becomes the configuration surface for several other intent docs (action-draft guards, calibration drift thresholds, predictor retirement, shadow-promotion, speculative-classification, reconciliation thresholds).
- PAPER→REAL typed confirmation is a hard requirement before Phase 4 ships a real-money submission flow.
