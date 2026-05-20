# Probabilistic Asset Outlook Doctrine

## 1) Purpose

This document locks the long-term forecasting doctrine for Portfolio Outlook Manager / Ai Trading Agent.

The main analytical goal is not to guess one exact future price. The main analytical goal is to calculate and explain probability ranges for future asset value, with clear uncertainty, risk, evidence, freshness and auditability.

This doctrine must guide future work on market data, asset master data, quantitative models, AI event intelligence, suggestions, portfolio views, watchlist views and Dutch explanations.

## 2) Core forecasting rule

The system must not present a single exact future asset price as if it is reliable.

The system should estimate a probability distribution for future returns or future asset value. The UI may simplify this in Dutch, but the backend must preserve the underlying probability/range logic.

Preferred output style:

- expected return or expected price range
- p10 / p50 / p90 forecast range
- probability of gain
- probability of loss
- probability of loss above defined thresholds
- probability of gain above defined thresholds
- expected volatility
- downside risk
- model confidence
- model disagreement
- data freshness status
- forecast validity window and expiry
- evidence links
- blockers and caveats
- simple Dutch explanation

Forbidden output style:

- fake certainty
- exact price targets without uncertainty
- AI-originated financial numbers used for decisions
- predictions without data freshness checks
- predictions without source/evidence traceability
- predictions that bypass risk gates
- predictions that directly create orders or IBKR actions

## 3) Python calculates, AI explains

Python and deterministic model code calculate financial numbers, probabilities, ranges, scores, risk measures and portfolio effects.

AI may help interpret documents, filings, news, events and context, but only through schema-validated structured outputs. AI may explain model output in Dutch. AI must not originate final financial numbers used by the decision system.

AI event intelligence may produce structured signals such as event type, affected asset, affected sector, direction, relevance, confidence, expiry and source links. These signals are inputs to the forecasting/suggestion system, not trades.

## 4) Forecasting object target

Future implementation should move toward an auditable AssetForecast-style contract containing at least:

- asset_id
- forecast horizon
- forecast_created_at
- forecast_valid_until
- current price and price source
- expected return
- expected price or value range
- p10 / p50 / p90 price or return
- probability_gain
- probability_loss
- probability_loss_more_than_5_percent
- probability_loss_more_than_10_percent
- probability_gain_more_than_5_percent
- probability_gain_more_than_10_percent
- expected_volatility
- downside_risk_score
- confidence_score
- model_disagreement_score
- data_freshness_status
- evidence links
- blocking reasons
- scenario summary in Dutch
- explanation in Dutch

The exact schema may evolve, but the probability/range structure is locked.

## 5) Forecast horizons

The system should support multiple forecast horizons over time. Initial work may start with one horizon, but the roadmap should preserve support for:

- 1 week
- 1 month
- 3 months
- 6 months
- 12 months

Forecasts must clearly state their horizon. A forecast for one horizon must not be silently reused for another horizon.

## 6) Required foundations before serious forecasting

A serious probabilistic forecasting engine requires these foundations:

- asset master and instrument identity
- adjusted and unadjusted historical price data
- corporate actions, splits and dividends
- FX rates and FX freshness
- market calendar and trading-hour status
- benchmark/index data
- sector/industry classification
- portfolio holdings and cash state
- point-in-time data storage
- feature store with versioned features
- forecast target definitions
- model registry and versioning
- backtesting and walk-forward validation
- probability calibration checks
- audit trail and reproducibility

No advanced forecast should be considered reliable until these foundations exist.

## 7) Model families to preserve in the roadmap

The project should not rely on one magic model. The roadmap should allow a model zoo and ensemble approach:

- baseline historical return/volatility model
- factor model
- momentum/trend model
- mean-reversion or regime-aware model where justified
- volatility and downside-risk model
- quantile/range model
- Bayesian/probabilistic model
- tree/ML model only after data and validation foundations exist
- AI event signal model as contextual input only
- ensemble model that combines validated model outputs

Every model must have a clear allowed use and forbidden use.

## 8) Backtesting, calibration and model risk

Every forecast model must be testable and auditable.

Required future controls:

- walk-forward testing
- out-of-sample testing
- point-in-time validation
- benchmark comparison
- probability calibration curves
- Brier score or equivalent probability metric where applicable
- p10/p90 coverage checks for range forecasts
- drawdown and downside-risk validation
- overfitting controls
- model drift monitoring
- model version tracking
- retirement/deprecation rules for weak models

A model with poor calibration should not be allowed to produce high-confidence suggestions.

## 9) Scenario engine

Forecast output should be translated into simple Dutch scenarios:

- base scenario
- positive scenario
- negative scenario
- event-risk scenario where relevant
- probability or confidence per scenario
- drivers that would change the scenario
- expiry or validity trigger

Scenarios are explanations of probability and risk. They are not direct orders.

## 10) Portfolio-level forecasting

The project must eventually calculate not only asset-level outlook, but also portfolio-level probability and risk:

- expected portfolio value range
- probability of portfolio drawdown above thresholds
- contribution to portfolio risk by asset
- correlation clusters
- sector concentration
- FX exposure
- cash impact
- what-if scenarios
- stress scenarios

Asset forecasts must not be evaluated only in isolation. Portfolio context matters.

## 11) UI principle

The backend may be complex, but the Dutch UI must remain simple.

Example UI language:

- Verwachte richting
- Kans op stijging
- Kans op verlies
- Verwachte bandbreedte
- Risico
- Betrouwbaarheid
- Waarom?
- Wanneer vervalt dit?
- Welke data is gebruikt?
- Wat kan dit veranderen?

The user should see clear decisions and explanations, not raw quant jargon by default.

## 12) Safety and execution boundary

Forecasts are not orders.

A forecast may later feed a suggestion only after all required gates exist and pass:

- data freshness
- market calendar/tradability
- source credibility
- prompt-injection checks for external content
- evidence ledger linkage
- portfolio risk checks
- cash/position rules
- model confidence/calibration checks
- audit logging
- user review

Even then, Version 1 remains IBKR paper-only and the user decides.
