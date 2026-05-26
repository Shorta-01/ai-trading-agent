# Decision package — intent

**Status:** locked
**Locked on:** 2026-05-26
**Decision record:** `docs/decisions/0007-decision-package-architecture.md`
**Doctrine:** `docs/intent/_trading-system-doctrine.md` (§6, §10, §13, §15)

## Scope

The decision package is the per-asset, per-moment container that holds everything the system has decided about an asset. It is the source-of-truth artefact consumed by the dashboard (for trust signal + explanation icon) and by the action draft composer.

## 1. Contract — what a decision package contains

Each decision package carries the fields below. All money values are Decimal.

- **Identity.** `ibkr_account_id`, `conid`, `symbol`, `exchange`, `currency_local`, `composed_at` timestamp, `decision_package_id` (UUID PK).
- **Market state.** Last-close price + as-of date, currency, freshness window. (Live prices are pulled separately at order ticket construction — see `docs/intent/data-sources.md`.)
- **Forecast snapshot.** The ensemble forecast at composition time **plus per-predictor contributions** (predictor name, raw forecast, weight, calibration status). Enables explanation drill-down.
- **Portfolio context.** Held assets only. If the asset is not held, this section is empty; the portfolio context is filled by the asset's current position.
- **Risk and sizing context.** Current exposures (per-position %, per-sector %, per-asset-class %), distance to caps, available cash, available risk budget. Feeds doctrine §5.1 layer-3 hard-cap binding-layer determination.
- **Suggested action.** Pre-filled IBKR-shaped ticket (doctrine §5) + binding sizing layer (§5.1) + recurrence info (doctrine §9, "3rd time this week").
- **AI explanation.** Lazy with caching (see §5). Not generated at composition time; generated on first explanation-icon click.
- **Audit pointers.** Event IDs in the audit log + diary reference for follow-up calibration.

## 2. Build cadence

- **Full rebuild at 07:00 morning chain.** Every eligible asset gets a fresh decision package, even if the underlying forecast hasn't changed.
- **Delta rebuild hourly during the day.** Existing packages are updated only for assets whose inputs have changed (see §3 triggers). Unchanged packages are not rewritten.
- **Selective on-demand refresh** at order ticket render. When the user opens a ticket modal, the system requests a live IBKR quote (`docs/intent/data-sources.md`) and refreshes the price-sensitive parts of the package for that one ticket.

## 3. Delta-rebuild change triggers

A decision package is rebuilt mid-day when any of these happen:

- **Price move beyond threshold.** Threshold per-asset; default value is doctrine §15 open.
- **New forecast emitted.** Hourly refresh produced a different ensemble result.
- **IBKR position change.** The user now holds the asset (or sold it).
- **IBKR cash change affecting eligibility.** A deposit / withdrawal / fill changes available cash and the package's risk-and-sizing context changes.
- **Calibration recomputation.** Monthly cadence — see `docs/intent/prediction-diary-and-calibration.md`.
- **Settings change affecting the asset.** Whitelist / blacklist / risk profile change.
- **Manual user action on the asset.** User added it to the watchlist, or rejected a prior suggestion. Forces a rebuild so the next suggestion reflects the user's intent.

## 4. Health surface

The system-health line on the dashboard (doctrine §10) shows the **last-full-rebuild timestamp**. Yellow if the morning chain failed or was skipped (e.g. reconciliation 07:00 block, see `docs/intent/reconciliation.md`). Red if the most recent full rebuild is more than 24 hours stale.

## 5. AI explanation: lazy with caching

- Not generated at composition time.
- Generated on **first click** of the explanation icon for a given decision package.
- Cached against `decision_package_id` and survives until the package is rebuilt.
- Subsequent clicks on the same package show the cached explanation **instantly**.
- Rebuild invalidates the cache.

This keeps AI cost down (most packages are never opened) and preserves the doctrine §13 budget cap behaviour.

## 6. Three-tier trust model

Each decision package carries a **trust tier**, surfaced in the per-row trust signal on the dashboard (doctrine §10).

- **Full.** All critical inputs are fresh and calibration is green.
- **Degraded.** One or more **non-critical** inputs are missing or stale, but critical inputs are fresh.
- **Minimal.** One or more **critical** inputs are missing or stale, or calibration is red.

### What is critical vs non-critical

- **Critical.** Forecast, market price, IBKR position freshness, calibration status.
- **Non-critical.** AI explanation, recurrence info, audit pointers, sector exposure metadata.

The exact freshness windows per input type are doctrine §15 open. Until thresholds are locked, the existing data_quality module (`packages/domain/.../data_quality.py`) holds the working defaults.

## 7. Hard rules

- **Trust level is never lied about.** AGENTS.md "no silent data correction" applies. A degraded package is shown as degraded; the dashboard does not paper over a minimal-trust package to look healthier.
- **Decision packages are immutable.** Each rebuild produces a new package; the prior one stays in the audit log with its hash chain (per existing `decision_package` storage schema, Task 132).

## 8. Open questions

- Exact freshness windows per input type (doctrine §15)
- Price-move threshold for delta-rebuild trigger (doctrine §15)

## 9. Cross-references

- Doctrine §6 (synchronisation — drives many delta triggers)
- Doctrine §10 (dashboard — trust signal source)
- Doctrine §13 (AI scope — AI explanation lazy + cached)
- Doctrine §15 (open questions)
- `docs/intent/forecast-engine.md` (ensemble forecast lands here)
- `docs/intent/prediction-diary-and-calibration.md` (calibration status feeds trust tier)
- `docs/intent/action-draft-state-machine.md` (action draft consumes the package's pre-filled ticket)
- `docs/intent/data-sources.md` (live IBKR quote at ticket render)
- `docs/intent/dashboard-and-order-flow.md` (per-row trust signal)
- `docs/intent/reconciliation.md` (07:00 block affects rebuild)
