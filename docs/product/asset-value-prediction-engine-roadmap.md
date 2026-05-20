# Asset-Value Prediction Engine Roadmap (Version 1, personal-use, paper-only)

## 1. Scope lock and safety boundary

Version 1 bevat expliciet de volledige Portfolio Outlook Manager / Asset-Value Prediction Engine roadmap in interne fasen, maar blijft:
- personal-use
- IBKR paper/simulatie-only
- geen live trading, geen real-money execution, geen automatische orders
- geen opties/futures/leverage/short selling/crypto/penny stocks/CFD’s/complexe derivaten.

Personal-use verlaagt geen kwaliteitslat: datahygiëne, validatie, audittrail, risico-gates en modelcontrole blijven verplicht.

## 2. Internal stage plan (V1.0–V1.8)

### V1.0 — Foundations
AssetMaster/AssetListing split; identity links (conid/ISIN/LEI/CIK/OAM filing waar relevant); point-in-time storage; provider adapters; evidence ledger upgrade; prompt/output log foundation; config registry; model registry; immutable run IDs; freshness gates; **nog geen prediction**.

### V1.1 — Baseline prediction engine
ARIMA/ETS; GARCH(1,1); HAR-RV; LightGBM/XGBoost cross-sectional model; LightGBM quantile heads; p10/p50/p90; P(gain), downside risk; HMM 3-state regime classifier; walk-forward backtesting; CPCV/DSR/PBO; deterministische NL label translator; **geen AI; geen suggestions zonder gates + Decision Package**.

### V1.2 — AI text-to-feature
News/filings ingestie; transcripts later waar beschikbaar; FinBERT + FinGPT sentiment/event scoring; GPT-4-class/GPT-5-class event tagger met strict schema; entity linking naar conid/AssetListing; event-features naar quant-modellen; AI confidence = feature, nooit financiële kans; prompt/output hash + source IDs; **geen AI-financiële nummers**.

### V1.3 — Challenger models
TSFM challengers: Chronos-Bolt, TimesFM 2.5, Moirai-2; plus PatchTST en N-HiTS; champion/challenger vergelijking; periodieke model tournament; promotie alleen met CPCV/DSR/PBO + calibratiebewijs.

### V1.4 — AI Dutch explanation/RAG
RAG corpus per asset/conid/datum/source; strict schema output; evidence-grounded Nederlandse uitleg; geen free-form advice; geen AI-originated prijzen/kansen/risico/sizing; prompt-injection filtering; source allowlist; evidence-vs-instruction separation; refusal path; uitleg alleen bij Decision Package.

### V1.5 — AI dissent challenger
Twee-model dissent; bull/bear/risk agent review; TradingAgents-stijl als challenger-only; kwalitatieve agreement/disagreement score; alleen confidence downgrade; geen suggestion- of orderbeslissing; geen financiële nummercreatie.

### V1.6 — Monitoring and drift
Feature/label drift; IC/rank-IC decay; hit-rate decay; CRPS/pinball-loss; p10/p90 coverage diary; PSI/KS drift checks; conformal coverage alerts; retraining triggers; champion/challenger promotion diary.

### V1.7 — Decision Package + suggestion layer
Immutable Decision Package met forecast/evidence/market-data/portfolio snapshots, gate outcomes, model version, expiry/valid-until, NL uitleg, deterministisch label; **geen suggestion zonder valide Decision Package**.

### V1.8 — Paper action workflow
IBKR paper-only; eerste uitvoerbare flow LMT-only; geen market orders; geen brackets/stops/trailing in eerste flow; user approval + backend safety recheck + usable-cash contract + IBKR handshake + action history/reconciliatie.

## 3. Algorithm portfolio (expliciet)

### Classical/statistical
ARIMA; SARIMA/ARIMAX (later waar relevant); ETS; GARCH(1,1); EGARCH (later waar nuttig); HAR-RV; realized-vol estimators; historical bootstrap fallback; Bayesian ridge voor langere horizon/factorstijl.

### Tree/tabular ML
LightGBM; XGBoost; CatBoost (optioneel challenger); cross-sectional ranking; factor-residualized returns; FF5+Momentum features; quantile heads (p10/p50/p90); ensemble/stacked distributie.

### Deep/TSFM challengers
Chronos-Bolt; TimesFM 2.5; Moirai-2; PatchTST; N-HiTS; Time-MoE/Toto/TiRex als watchlist research candidates; TSFM blijft challenger tot promotiebewijs.

### Regime/risk
HMM 3-state regime; regime posterior shift; crisis-state confidence downgrade; realized-vol risk; downside risk via p10 of CVaR-style metric; VaR/CVaR later; volatility targeting; risk parity later; fractional/quarter-Kelly alleen capped en pas later.

## 4. Probabilistic outputs and calibration
p10/p50/p90, P(gain), P(loss), expected volatility, downside risk, model confidence, model disagreement.
Methoden: Conformalized Quantile Regression, conformal calibration set, finite-sample coverage target, pinball loss, CRPS, PIT histograms, reliability plots, conformal coverage diary, later portfolio-level conformal intervals.

## 5. Validation and anti-overfitting gates (mandatory)
Walk-forward expanding window; purged k-fold + embargo; CPCV; DSR; PBO; permanent untouched holdout; feature ablation + LLM-feature ablation; benchmark vergelijking; post-publication performance haircut/skepsis; geen modelpromotie zonder evaluation report; geen Decision Package zonder approved model/version.

## 6. Feature engineering families
Returns/residuals: 1/5/20/60/120d log returns; residual returns vs market/sector/factors.
Liquidity/volume: volume, dollar volume, turnover, Amihud illiquidity, Roll spread.
Volatility/jumps: RV 5/20/60d, vol-of-vol, Garman-Klass, Parkinson, Lee-Mykland jumps.
Cross-section: ranks, z-scores/percentiles per universe/sector.
Calendar: day-of-week, turn-of-month, maand/kwartaal seizoen, expiration weeks (later).
Earnings/events: days-to/since earnings, SUE history, PEAD windows, guidance-change flags.
Sentiment/news: news count, polarity, novelty, surprise vs baseline, topic/event type.
Macro: 2y/10y yield, term spread, credit spreads, VIX, USD index, oil, gold; FRED/ECB SDW readiness.
Microstructure: quote-spread proxy, signed-volume proxy, gap to prior close, opening-range break.
ETF: NAV-premium/discount, AUM/flow proxies, basket factor exposure, sector/style exposure.

## 7. Data layer roadmap
IBKR TWS/Client Portal/Gateway: positions/cash/executions/open orders/OHLCV snapshots where available; tot paper action-fase read-only; pacing/freshness limits respecteren.
EODHD (of equivalent) als EU/global EOD kandidaat. Polygon (of equivalent) als US intraday/tick kandidaat indien nodig.
SEC EDGAR (fair-access/rate-limit compliant), ESMA/filings.xbrl.org/nationale OAM’s (ESAP later), Tiingo/Benzinga-equivalent nieuws, FRED/ECB SDW macro.
Niet ontwerpen rond IEX Cloud (sunset/retired).

## 8. AI implementation layers

### Layer A — text-to-feature
FinBERT/FinGPT/FinMA(where useful)/GPT-4-class or GPT-5-class structured tagger; strict JSON schema; function calling/structured output; temperature 0; fixed seed where supported; source/evidence IDs; conid/AssetListing IDs; event type/polarity/novelty/confidence/expiry/source & ingestion timestamps; AI output hash + prompt hash; alle AI text-features auditeerbaar opslaan.

### Layer B — Dutch explanation/RAG
RAG corpus by asset/conid/date/source; source allowlist; evidence-vs-instruction separation; prompt-injection scan; output schema validator; refusal path; uitleg gebruikt alleen gevalideerde Decision Package getallen; noemt onzekerheid/horizon/expiry/blockers; voegt geen nieuwe financiële waarden toe.

### Layer C — dissent/multi-agent challenger
Twee-model dissent + bull/bear/risk review; TradingAgents-stijl experimenteel; output alleen kwalitatieve dissent/agreement/confidence modulation; kan geen label/orders/financiële getallen maken; moet gated + gelogd.

### AI hard prohibitions
AI mag nooit origineren: prijzen/targetprijzen/returns/p10-p90/P(gain/loss)/volatiliteit/downside risk/risk score/model confidence/model disagreement/position size/buy-sell-hold label/order type/quantity/limit price/broker action.

## 9. Reference architecture layers
Data → Feature → Model → Ensemble/orchestration → Evaluation/calibration → Decision/translation → AI feature/explanation/dissent → Audit → later paper action.

## 10. Horizon model portfolio
Intraday alert: rules + momentum + microstructure + RV/HAR-RV, doorgaans zonder AI.
1–5d: LightGBM quantile residual returns + PatchTST challenger + GARCH/HAR-RV + sentiment/events.
5–60d: LightGBM/XGBoost + Chronos-Bolt/TimesFM challengers + EGARCH/jump-robust RV + sentiment/earnings/regime.
60–250d: factor-tilted LightGBM + Bayesian ridge + N-HiTS challenger + stochastic vol/long-run GARCH + filing themes.
Long-term: factor model + macro HMM + bootstrap VaR/CVaR + annual filing theme synthesis.

## 11. Deterministic Dutch suggestion mapping (future gated)
AI beslist label nooit. Python vertaalt gevalideerde outputs (p10/p50/p90, P(gain), sigma, downside risk, confidence, disagreement, gate flags) naar labels: Geblokkeerd/Geen actie/Bekijken/Kopen/Langzaam bijkopen/Houden/Verminderen/Verkopen/Vermijden/Cash houden.
Voorbeeldregels mogen in config; thresholds zijn auditeerbaar en alleen bruikbaar na CPCV/evaluatievalidatie.

## 12. Risk gates before any suggestion
Data freshness, regime-change, model confidence, model disagreement, evidence quality, earnings blackout, liquidity, conformal coverage breach, prompt-injection on AI evidence, source credibility; later concentration gates; usable-cash gate vóór action drafts; IBKR paper-only gate vóór submission.

## 13. Position sizing roadmap (future, paper-only)
Vol targeting; quarter-Kelly capped pas na validatie; max position/new-buy/sector caps; cash buffer; drawdown exposure scaling; risk parity later; geen sizing vóór Decision Package + portfolio risk gates; nooit AI-sourced sizing.

## 14. Monitoring, drift, and lifecycle
PSI/KS, label drift, rolling IC/rank-IC, hit rate, CRPS, pinball, p10/p90 coverage, feature-importance stability, SHAP pruning, VIF on linear baselines, decay alerts, retraining triggers, promotion rules, retirement/deprecation.

## 15. Must / Should / Could acceptance into V1 scope

### MUST ADD
Point-in-time hygiene; Asset Master enrichment + AssetListing model; ARIMA/ETS + GARCH + HAR-RV baselines; LightGBM cross-sectional + quantile heads; CQR; HMM gate; CPCV/DSR/PBO harness; deterministic NL translator; news/filings + FinBERT feature; evidence ledger upgrade; drift monitoring + retraining triggers; earnings blackout gate; MiFID/GDPR disclaimer + audit trail for personal-use boundary.

### SHOULD ADD
TSFM challengers (Chronos-Bolt, TimesFM 2.5, Moirai-2 where relevant), PatchTST, N-HiTS, LLM event tagger, RAG NL explanation strict schema, two-model dissent, Polygon-equivalent only if intraday focus, conformal portfolio intervals.

### COULD ADD
Multi-agent dissent, TradingAgents-style debate, RL entry timing after supervised proof, ESAP ingestion when usable, alternative data only with feature-importance justification, BloombergGPT-class interface abstraction (no cost/access assumptions), fine-tuning experiments (e.g. FinGPT-LoRA).

COULD-modules zijn challenger/experimenteel en mogen suggestions/action drafts niet beïnvloeden vóór promotie door validatiegates.

## 16. Benchmark and fallback rules
- TSFM kan champion worden bij sustained CPCV-validated DSR uplift vs LightGBM champion.
- Bij zwakke LLM-feature uplift: inferencegebruik verlagen.
- Bij persistente conformal coverage breach: degraded historical-bootstrap mode + expliciete warning.
- Model zonder calibratie mag geen high-confidence output leveren.
