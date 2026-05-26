# Reconciliation — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0010-reconciliation-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§6, §15)

## Scope

This document specifies the periodic backup-sync layer that compares the system's local snapshot of IBKR state against IBKR truth, classifies discrepancies, and surfaces material ones for user attention. Reconciliation is the **backstop** beneath the event-stream sync (doctrine §6).

## 1. Hybrid cadence

### Periodic baseline

- **Every 15 minutes during market hours.** A market is "open" if any of the configured exchanges is in its primary trading session.
- **Every hour outside market hours.** Reduced cadence for off-hours; positions can still drift due to dividend payments, corporate actions, or manual broker activity.

### Event triggers

Five event triggers cause an immediate reconciliation run, regardless of schedule:

- **07:00 before the morning chain.** **Mandatory; blocks the morning chain until complete.** If reconciliation fails to finish, the morning chain does not run, the dashboard shows the previous day's state, and the system-health line turns red.
- **After every order fill.** Re-verify post-fill state.
- **After IBKR session reconnect.** Anything could have changed during the disconnect.
- **On user demand.** Button in Category 5 of `docs/intent/settings-and-credentials.md` — "user-initiated reconciliation trigger".

## 2. Passes per run

Each run executes the three reconciliation passes locked in Task 135:

- **Pass A — orphaned executions** (IBKR has fills we missed).
- **Pass B — stale in-flight** (drafts we think are in-flight that IBKR no longer reports).
- **Pass C — 24h timeout escalation** (`awaiting_reply_timeout` drafts that still have no IBKR data after the cut-off → `requires_manual_review`).

Content of each pass is owned by the existing Task 135 product locks; this intent file does not redefine pass behaviour.

## 3. Four-tier discrepancy classification

Class A is **explicitly forbidden** by AGENTS.md "no silent data correction" — there is no auto-correct-without-trace tier. The four operative tiers are B / C / D / E.

| Tier | Severity | Action | System-health |
|------|----------|--------|---------------|
| **B** — Expected drift | Low | Auto-correct with audit log. No user signal. | No change |
| **C** — Material drift | Medium | Auto-correct with audit log. | Yellow |
| **D** — Suspicious drift | High | **Block downstream**, surface as system-decision item in actions area. | Red |
| **E** — Critical drift | Critical | **Halt order generation**, halt data writes, prominent surfacing. | Red |

Examples (defaults; subject to T-020 reality):

- B: cash balance differs by ≤ €0.01 — rounding.
- C: position quantity differs by < 1 share for a stock — likely partial-fill event in flight, will resolve on next sync.
- D: position appears in IBKR that the system never recorded a fill for — possible silent failure of fill ingestion. User reviews.
- E: cash balance differs by > 5% with no plausible event explanation — possible corruption. Halt.

## 4. Default classification table

Per-pass default thresholds. Configurable in Category 3 of `docs/intent/settings-and-credentials.md`. Doctrine §15 open.

| Pass | Subject | B threshold | C threshold | D threshold | E threshold |
|------|---------|-------------|-------------|-------------|-------------|
| A | Orphaned execution | n/a (any orphan is at least C) | always C | matches no draft → D | huge value → E |
| B | Stale in-flight | n/a | < 5min stale → C | 5–30min → D | > 30min → E |
| C | 24h timeout | n/a | n/a | < 48h → D | > 48h → E |

Thresholds **changes** are audit-logged with `{user, pass, field, from, to, changed_at}`.

## 5. Three non-scope rules

1. **No back-fill of audit log entries.** When reconciliation discovers a missed event, it writes a **reconciliation event** with full context. It does not retro-insert the event at its original timestamp. Audit is append-only.
2. **No retroactive rebuild of decision packages.** Decision packages from prior moments stay intact. A future package may reflect the reconciled state, but past packages are immutable.
3. **No auto-retry indefinitely.** Max 3 attempts per reconciliation run; then the run fails loudly (audit-logged, system-health red, no silent loop).

## 6. User-initiated reconciliation in v1

- Same as periodic: same passes, same classification, same audit logging.
- Immediate execution; no batching.
- Subject to the single-flight Postgres advisory lock (per existing Task 127 product lock) — a user-triggered run that overlaps with a scheduled run waits or skips per the same single-flight discipline.

### Phase 4 evolution candidates

- **Dry-run mode.** Run the passes without writing any corrections; show what would change.

### Deferred indefinitely

- **Deep mode.** Historical fill replay (re-fetch and re-apply all historical IBKR executions). Risk of disrupting the existing audit chain outweighs benefit.

## 7. Open questions

- Default reconciliation thresholds per pass (current values are intent; reality may differ) (doctrine §15)
- Whether to add dry-run mode in Phase 4 (open scope question)

## 8. Cross-references

- Doctrine §6 (synchronisation — reconciliation is the backup beneath event-stream sync; 07:00 mandatory block)
- Doctrine §10 (system-health line; D-class items as system-decision actions)
- Doctrine §15 (open questions)
- `docs/intent/order-lifecycle.md` (Open orders grid verified against reconciliation truth)
- `docs/intent/portfolio-valuation.md` (corporate-action drift surfaces as D-class)
- `docs/intent/settings-and-credentials.md` (Category 3: configurable thresholds; Category 5: user-trigger button)
- Existing Task 135 product locks (passes A/B/C content + state-machine widening)
- Existing Task 127 product locks (APScheduler single-flight lock)
