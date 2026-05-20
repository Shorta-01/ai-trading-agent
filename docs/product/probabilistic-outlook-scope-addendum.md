# Probabilistic Outlook Scope Addendum

## Purpose

This addendum locks the Version 1 scope items needed to support the long-term goal of probability/range-based asset outlooks.

The canonical doctrine is `docs/product/probabilistic-asset-outlook-doctrine.md`.

## Locked scope additions

| Feature | Purpose | Status | Notes |
|---|---|---|---|
| Probabilistic asset outlook doctrine | Locks the product direction away from fake exact price targets and toward calibrated probability/range outputs | Locked | Doctrine document added. Runtime not implemented yet. |
| Asset master foundation | Gives every asset a stable identity beyond ticker text | Planned | Needed before serious market data, portfolio and forecast work. |
| Market data storage foundation | Stores adjusted/unadjusted price data, corporate actions, FX and freshness metadata | Planned | Needed before return calculations and forecast targets. |
| Feature store foundation | Stores deterministic, versioned model inputs | Planned | Needed for reproducible quant models. |
| Forecast target definitions | Defines exactly what the system forecasts per horizon | Planned | Example: probability of gain/loss, p10/p50/p90 return ranges, downside thresholds. |
| Baseline probabilistic forecast model | First simple model to produce auditable probability/range outputs | Planned | Must be conservative and tested before any advanced model. |
| Forecast validation and calibration | Tests whether model probabilities are reliable | Planned | Includes backtesting, walk-forward checks, calibration curves and coverage checks. |
| Model registry and model risk controls | Tracks model versions, assumptions, allowed use and limits | Planned | Weak or stale models must not produce high-confidence outputs. |
| Scenario engine | Translates probability/range outputs into simple Dutch base/positive/negative scenarios | Planned | Scenarios explain risk and uncertainty. They do not create actions by themselves. |
| Portfolio-level probability and risk | Calculates portfolio value ranges, drawdown probabilities and concentration/correlation effects | Planned | Asset outlooks must eventually be evaluated in portfolio context. |

## Locked implementation order principle

Do not jump straight to an advanced AI forecasting layer.

Recommended order:

1. Asset master foundation.
2. IBKR contract identity validation / conid mapping.
3. Active watchlist contract validation.
4. Market data and FX foundation.
5. Point-in-time storage/freshness rules.
6. Return and volatility calculation engine.
7. Feature store foundation.
8. Forecast target definitions.
9. Baseline probabilistic forecast model.
10. Backtesting and probability calibration.
11. Scenario engine and Dutch explanations.
12. Ensemble/AI-event integration only after the above foundations exist.

## Safety locks

- Forecasts are not orders.
- Forecasts do not bypass source credibility, freshness, evidence, risk or user-review gates.
- Forecasts do not create IBKR actions by themselves.
- AI may explain and structure evidence, but Python/model code calculates probabilities, ranges and financial values.
- Any user-facing forecast must show uncertainty, horizon and expiry.

## Task 88J implementation-order update

Volgorde is nu vergrendeld op V1.0–V1.8 interne fasering uit `asset-value-prediction-engine-roadmap.md`.
Alle Must/Should/Could componenten zitten binnen Version 1-scope; Could blijft challenger/experimenteel en mag output niet beïnvloeden zonder promotiegates.
