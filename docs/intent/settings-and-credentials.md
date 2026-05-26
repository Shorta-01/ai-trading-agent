# Settings and credentials — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0004-settings-and-credentials-structure.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§3, §13, §15)

## Scope

This document is the live spec for everything a user can configure in the system: connections, preferences, safety limits, monitoring, and audit/backup/observability. It also covers how secrets are stored, displayed, and rotated, and how a change in any category propagates.

Five categories. Every concrete setting belongs to exactly one of them. The UI is grouped by category.

## 1. Category 1 — Connections

External-system credentials and connection parameters. Secrets live here.

- **IBKR connection.** Host, port, client ID, account ID. Paper / real-money toggle: the toggle itself is a setting; flipping it from PAPER to REAL requires the user to type a confirmation phrase before the change is accepted. The mode badge (doctrine §3.1) reads from this setting.
- **EODHD API key.** Plus tier selector (All-In-One required for v1; see `docs/intent/data-sources.md`) and a live quota-usage display.
- **AI explanation provider configuration.** Primary provider toggle (Anthropic Claude — default; OpenAI GPT — alternative). Both providers' API keys. Per-provider monthly budget cap. Fallback-enabled toggle.
- **Database connection.** Host, port, database, user, password.

Test-connection button per credential (round-trip to the actual external system).

## 2. Category 2 — User preferences

Things the user decides about how the system behaves on their behalf. No secrets.

- **Base currency.** Default EUR.
- **Tax residency.** Default Belgium.
- **Trading hours / market focus.** Which exchanges / markets the user trades.
- **Morning evaluation time.** Default 07:00 (Europe/Brussels).
- **Hourly refresh.** Enabled toggle + hours window (default 08:00–20:00).
- **UI language.** Default Dutch.
- **Risk profile.** Conservative (0.15 Kelly), Moderate (0.25 Kelly — default), Aggressive (0.40 Kelly).
- **Investment policy caps.** Max % per single position, per sector, per asset class (doctrine §5.1 layer 3).
- **Default order behaviour.** Patient-liquidity discount/premium default (default 0.2%; doctrine §5.3).
- **Stop-loss policy.** ATR-based / fixed % / none. Default is an open question in doctrine §15.
- **Portfolio valuation display method.** Weighted average / FIFO / specific lot ID. Default weighted average. (See `docs/intent/portfolio-valuation.md`.)

### 2.1 Data features (sub-section of Category 2)

A separate sub-section for data-source feature toggles. The toggles interact with Category 1 (EODHD tier).

- **Price + volume.** Mandatory. Cannot be disabled.
- **Fundamentals.** Default ON in v1.
- **Earnings calendar suppression** (don't trade in the N days around earnings). Default ON in v1.
- **Macro context.** Default OFF in v1. Future evolution.
- **Alternative data** (sentiment, social signals, satellite, etc.). Default OFF in v1. Deferred.

Conflict handling: if a feature toggle is set ON but the configured EODHD tier doesn't support the underlying data, the settings UI flags the conflict visually and the system does not silently downgrade.

### 2.2 System capabilities (sub-section of Category 2)

Pattern for future feature toggles. Examples to be filled in over time: which predictors are active in the ensemble, which suggestion types (Buy / Reduce / Sell) the system is allowed to emit, which order types are enabled (LMT / MKT / bracket / stop). The pattern: a toggle with a default; toggling OFF disables the capability immediately but does not retroactively delete prior data.

## 3. Category 3 — Safety limits

Hard constraints. Reaching any of these blocks downstream behaviour (suggestion generation, order submission, or both depending on the limit). All limits are audit-logged on every change and on every breach.

- **Max order value** (per single order).
- **Max orders per day.**
- **Max total exposure** (sum of position values, percentage of net liquidation).
- **Minimum cash buffer.** Floor on usable cash; suggestions that would breach are blocked.
- **Trading halt master switch.** Single toggle that stops the system from generating new suggestions or submitting any order. Acts as a kill switch.
- **Whitelist / blacklist of instruments.** Optional. When the whitelist is populated, only listed instruments are eligible; the blacklist always blocks regardless.
- **Drawdown circuit breaker.** Default threshold 15% drawdown from peak. When tripped, halts new BUY generation. (Doctrine §15: default subject to revision.)
- **Calibration drift thresholds.** Per-predictor and ensemble-wide thresholds for yellow / red on system-health. (Doctrine §15.)
- **Predictor retirement threshold.** Default 6 months of continuous miscalibration before retirement is surfaced as a system-decision item. (Doctrine §15.)
- **Shadow-mode promotion threshold.** Default 3 months observation; new predictor must demonstrate live calibration within tolerance AND live hit rate within 25% of backtest projection before the promotion item appears. (Doctrine §15.)
- **Speculative-classification thresholds.** Trade count and turnover thresholds beyond which the system surfaces a speculative-classification warning as a system-decision item. **Default placeholder; accountant review required before the default is locked.** (Doctrine §15.)

## 4. Category 4 — Monitoring

How the system reaches the user.

- **Critical-alert email address.** Where the system sends critical alerts.
- **Which events qualify as critical.** Configurable list — reconciliation E-class, drawdown circuit breaker tripped, IBKR session lost, calibration ensemble-wide red, AI budget exhausted on both providers, scheduled morning chain failed.
- **Quiet hours.** Window during which non-critical alerts are queued instead of delivered.

Delivery channels beyond email are a doctrine §15 open question.

## 5. Category 5 — Audit, backup, observability

How the system records and protects its own state.

- **Audit log retention.** How long audit entries are kept (default: indefinitely).
- **Backup destination.** Where backups go (local path or remote target). Encrypted at rest.
- **Backup frequency.** Default daily.
- **Restore-test reminder cadence.** Default quarterly. AGENTS.md: "A backup is not trusted until restore is tested."
- **User-initiated reconciliation trigger.** Button that fires a reconciliation run immediately. Same passes, same classification, same audit logging as periodic.
- **On-demand backtest trigger.** Button that runs a backtest of the current ensemble against the configured window.
- **On-demand annual tax report generation.** Button that produces the Belgian tax report (see `docs/intent/belgian-tax.md`).

## 6. UX rules

These apply across all five categories:

1. **Grouped by category.** Settings UI shows one section per category, in the order 1 → 5.
2. **Test-connection button per credential.** Round-trips to the actual external system.
3. **Secrets never re-displayed.** Once entered, secret fields show only a "replace" affordance — never the stored value, never a masked tail.
4. **Apply cadence by category.** Category 1 (Connections): applies immediately. Category 2 (User preferences): applies on the next morning chain (07:00) so a mid-day setting change doesn't desync the day's suggestions. Category 3 (Safety limits): applies immediately and is audit-logged with the change.
5. **PAPER → REAL requires typed confirmation.** The toggle in Category 1 demands a confirmation phrase (locked Dutch: `BEVESTIG REAL`) before the change is accepted.
6. **"Show me what changed."** A button on the settings root that diffs current vs last-saved values, so the user can see what they've edited before committing.
7. **Export / import as encrypted file.** The full settings tree can be exported to an encrypted file and imported on another install. Secrets stay encrypted at rest.

## 7. Open questions

- Storage backend choice: OS keyring vs encrypted file (Doctrine §15).
- Stop-loss policy default (Doctrine §15).
- Drawdown circuit-breaker threshold default (Doctrine §15).
- Critical alert channels beyond email (Doctrine §15).
- Per-provider AI budget defaults (Doctrine §13.1, §15).
- Speculative-classification threshold defaults — accountant review needed (Doctrine §15).
- Default config of data feature toggles for new installs (Doctrine §15).

## 8. Cross-references

- Doctrine §3 (account modes — paper/real toggle UX)
- Doctrine §13 (AI scope — explanation provider configuration)
- Doctrine §15 (open questions)
- `docs/intent/data-sources.md` (EODHD tier dependency)
- `docs/intent/ai-usage.md` (per-provider budget, fallback behaviour)
- `docs/intent/portfolio-valuation.md` (display method)
- `docs/intent/predictor-lifecycle.md` (shadow promotion threshold)
- `docs/intent/reconciliation.md` (user-initiated reconciliation trigger)
- `docs/intent/belgian-tax.md` (on-demand tax report)
