# Profit-harvest doctrine (V1.2)

> Status: **Pure-function doctrine complete, worker integration pending.**
>
> This document is the single source of truth for the V1.2 retiree-income
> profit-harvest strategy. It maps every component shipped in PRs #574-#590
> and explains how they compose into one verdict per candidate.

## The strategy in one paragraph

The user is a Belgian retiree with €6M total wealth: €5M on rolling
3-6 month term deposits (€7,300 net/month at 2.5%) plus €1M earmarked
for tactical equity trading. Goal: €10,000 net/month income forever
without touching the principal. The trading bucket has to net
~€32,500/year (3.25% net) to close the gap. The doctrine is a
**buy → wait for +4% net → sell → recycle** cycle: aggressive enough
to beat term deposits, conservative enough that the €1M principal
stays intact for decades.

## Locked invariants

These are doctrine choices that must not be re-litigated without an
explicit policy review:

* **No stop-loss on held positions.** Held positions wait for the
  +4% net take-profit or a CRITICAL/ALERT news exit. No
  price-based stop.
* **Capital preservation as primary risk metric.** The €1M trading
  bucket must survive a multi-decade horizon; principal preservation
  beats yield maximisation.
* **Belgian-tax-aware targets.** All net targets are converted to
  gross before being placed at IBKR. A 4% net target on a
  standard stock places the take-profit LMT at +4.73% gross
  (compensating for the round-trip TOB of 0.70%).
* **AI never originates a number.** LLM is used for classification
  and Dutch explanation, not for forecasting prices or sizing
  positions. The forecasting math is deterministic.
* **No leveraged ETFs, no inverse ETFs, no penny stocks.** Daily-
  reset compounding decay makes any of these toxic at the
  3-6 month horizon.

## Pipeline overview

The orchestrator (V1.2 §M) runs every doctrinal gate in this order,
short-circuiting at the first failure. The order is *cheapest-first*
so the lognormal CDF math only runs on candidates that survived the
metadata gates.

```
┌───────────────────────────────────────────────────────────────────┐
│  1. Macro regime gate (V1.2 §I)                                   │
│     • VIX ≥ 30 → skip cycle                                       │
│     • Index 50d MA < 200d MA → skip cycle                         │
│     If either fires, ALL new BUYs refused for this cycle.         │
└───────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│  2. Risk-universe gate (V1.2 §G)                                  │
│     • Leveraged / inverse ETF detector                            │
│     • Market cap floor (default €5B)                              │
│     • Annual volatility ceiling (default 30%)                     │
└───────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│  3. Earnings-calendar gate (V1.2 §R)                              │
│     • Refuse new BUY in the configured pre-earnings window        │
│       (default 5 calendar days). Missing data is allowed.         │
└───────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│  4. Confidence gate (V1.2 §H + §P + §Q)                           │
│     • Compute gross take-profit price via profit-harvest tax math │
│     • P(max S_t ≥ K) using GBM running-maximum formula            │
│     • Fat-tail factor applied (default 1.15, Student-t df ≈ 5)    │
│     • Compare to user confidence threshold (default 70%)          │
└───────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│  4b. News-sentiment boost (V1.2 §S)                               │
│     • Bullish news flow lifts confidence_pct by up to             │
│       trading_news_buy_bias_max_boost_pct (default +5pp)          │
│     • Boost feeds sizing only; never overrides the gate verdict   │
└───────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│  5. Conviction-weighted sizing (V1.2 §F)                          │
│     • Linear ramp: confidence_threshold → min_position            │
│       100% → max_position                                         │
│     • Default band: €25,000 - €100,000                            │
└───────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│  6. Sector concentration gate (V1.2 §L)                           │
│     • Would the sized position push the sector over the cap?      │
│     • Cap is against total_budget_eur, not deployed capital       │
└───────────────────────────────────────────────────────────────────┘
                                ↓
┌───────────────────────────────────────────────────────────────────┐
│  7. Take-profit pair builder (V1.2 §J)                            │
│     • Entry LMT at current price                                  │
│     • Take-profit LMT at gross_target price (4.73% above entry)   │
│     • GTC for take-profit (waits for fill any time in horizon)    │
│     • DAY for entry (fill today or reconsider tomorrow)           │
└───────────────────────────────────────────────────────────────────┘
                                ↓
                         Verdict: SUGGEST
                                ↓
                ┌──────────────────────────────────┐
                │  IBKR submission adapter (§U)    │
                │  → OrderSubmissionInputs         │
                │  → 2-leg BRACKET (no stop-loss)  │
                └──────────────────────────────────┘
```

## Component map

### Pure-function doctrine (`packages/portfolio`)

| Module | PR | Doctrine § | Purpose |
|---|---|---|---|
| `profit_harvest.py` | #574 | §F | Tax-aware target math + conviction-weighted sizing |
| `risk_universe_gate.py` | #575 | §G | Leveraged / cap / vol filter |
| `confidence_gate.py` | #576, #584, #585 | §H, §P, §Q | Running-max P(target hit) + fat-tail correction |
| `macro_regime_gate.py` | #577 | §I | VIX + index MA crossover |
| `take_profit_pair.py` | #578 | §J | Entry + take-profit LMT pair builder |
| `news_severity.py` | #579 | §K | INFO / WARN / ALERT / CRITICAL classifier (exit signal) |
| `sector_concentration.py` | #580 | §L | Per-sector concentration cap |
| `profit_harvest_orchestrator.py` | #581 | §M | Single entry-point combining all gates |
| `analyst_revision_predictor.py` | #583 | §O | 3m / 6m EPS + 3m target revision composite |
| `earnings_calendar_gate.py` | #586 | §R | Pre-earnings BUY exclusion window |
| `news_sentiment.py` | #587 | §S | Bullish-flow conviction booster |
| `orchestrator_explanation.py` | #589 | §T | Dutch summary + detail for the operator UI |

### Domain settings (`packages/domain`)

`UserStrategySettings` carries 13 V1.2 cycle parameters; defaults match
the doctrine table below.

| Setting | Default | Range | Doctrine § |
|---|---|---|---|
| `trading_target_net_pct` | 4 | 1–50 | F |
| `trading_horizon_min_months` | 3 | 1–24 | F |
| `trading_horizon_max_months` | 6 | 1–24 | F |
| `trading_min_position_eur` | 25,000 | > 0 | F |
| `trading_max_position_eur` | 100,000 | > 0 | F |
| `trading_confidence_threshold_pct` | 70 | 0–100 | H |
| `trading_max_sector_pct` | 25 | 0–100 | L |
| `trading_min_market_cap_eur` | 5,000,000,000 | > 0 | G |
| `trading_max_annual_volatility_pct` | 30 | 0–100 | G |
| `trading_total_budget_eur` | 1,000,000 | > 0 | F |
| `trading_fat_tail_factor` | 1.15 | 0.5–2.5 | Q |
| `trading_earnings_block_days` | 5 | 0–30 | R |
| `trading_news_buy_bias_max_boost_pct` | 5 | 0–20 | S |

### IBKR integration

| Module | PR | Purpose |
|---|---|---|
| `take_profit_submission_adapter.py` (API) | #590 | `TakeProfitOrderPair` → `OrderSubmissionInputs` |
| `ibkr_ibapi_order_submission_client.py` | #590 | BRACKET branch accepts `stop_loss=None` (2-leg variant) |

### UI

| Page | PR | Purpose |
|---|---|---|
| `instellingen` | #582, #588 | All 13 doctrine settings with Dutch help text |

## What's NOT yet wired

The pure-function doctrine is complete; the **worker integration is pending**.
At present:

* The orchestrator is callable from any module that depends on
  `portfolio_outlook_portfolio`.
* The suggestion engine in the worker has *not yet* been migrated to
  call the orchestrator. The legacy ensemble + label translator is
  still the live path.
* The submission adapter is callable from the API but the IBKR action-
  draft submission flow has not been migrated to use take-profit pairs.

A future PR series should:

1. Add an "experimental" parallel path in the worker that runs the
   orchestrator alongside the legacy engine and stores both verdicts.
   This lets the doctrine be validated against real candidates before
   becoming the live path.
2. Once validated, make the orchestrator the canonical suggestion
   source. Retire the legacy ensemble label-translator path for the
   profit-harvest cycle (legacy may remain for non-cycle use cases).
3. Wire the take-profit submission adapter into the action-draft
   submission flow so accepted suggestions flow end-to-end into IBKR.

## How to read this doc

When you change a doctrinal default — fat-tail factor, confidence
threshold, sector cap, anything — update both the relevant section
above AND the locked default in `packages/domain/.../settings.py`.
The doc and the code must stay in sync; both serve as the contract
between the user and the system.

When you add a new gate, append it to the pipeline diagram **and**
to the component map. Then update `orchestrator_explanation.py` with
the new Dutch reason string so the operator UI doesn't fall through
to the generic "Onbekende beslissing" line.
