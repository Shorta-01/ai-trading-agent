# Task 126 — Asset Suggestion and Financial Algorithm Roadmap

## 1. Purpose and product position
Deze roadmap beschrijft welke data-, reken-, risk-, validatie- en uitlegfundamenten nodig zijn vóór het systeem betrouwbare actie-suggesties mag tonen. Het doel is **nauwkeurigheid, auditability en uitlegbaarheid**. Het systeem mag niet van gesynchroniseerde IBKR-data direct naar advies springen zonder gecontroleerde tussenlagen.

## 2. Current repository alignment note
Productrichting is nu verduidelijkt en gedocumenteerd: Portfolio Outlook Manager is account-mode-aware en niet paper-only als productidentiteit.

Deze taak:
- wijzigt **geen runtimegedrag**;
- voegt **geen** broker execution/orderruntime toe;
- houdt de roadmapfocus op nauwkeurige, auditeerbare suggesties met gates en Decision Packages.

## 3. Source-of-truth model
- **IBKR**: operationele waarheid voor portfolio, cash, positions, orders, executions, account state.
- **Lokale database**: workflow-, model-, status- en auditwaarheid.
- **Market-data providers**: waarheid voor marktdata, maar alleen na validatie/freshness gates.
- **Python/modelcode**: berekent financiële waarden, kansen, scores, labels.
- **AI**: evidence-interpretatie + eenvoudige Nederlandse uitleg binnen gates; AI is geen financiële calculator.

## 4. Required data layers
| Data layer | Status | Opmerking |
|---|---|---|
| IBKR position snapshots | gedeeltelijk geïmplementeerd | duurzame snapshots aanwezig |
| IBKR cash/account snapshots | gedeeltelijk geïmplementeerd | duurzame snapshots aanwezig |
| IBKR open orders | gedeeltelijk geïmplementeerd | read-only sync basis |
| IBKR executions/fills | gedeeltelijk geïmplementeerd | read-only sync basis |
| AssetListing identity (validated) | gedeeltelijk geïmplementeerd | gate-basis aanwezig |
| Latest market snapshot | pending | runtime market-data nog niet actief |
| Historical prices | pending | nodig voor risk/factor/forecast |
| Volume/liquidity | pending | nodig voor uitvoerbaarheidsrisico |
| Benchmark data | pending | nodig voor active return/IR/TE |
| Sector/industry metadata | pending | nodig voor exposures/factors |
| FX rates | pending | nodig voor multicurrency waardering |
| Fundamentals | pending | nodig voor valuation/factors |
| Earnings/corporate actions | pending | event risk + freshness |
| User risk/settings | deels aanwezig, verdere uitwerking pending | nodig voor persoonlijke limits |
| Uploaded bronnen/notities/URLs | gedeeltelijk aanwezig | alleen na credibility/injection gates |

## 5. Core portfolio calculations
Verplicht: position value, (average/book) cost, unrealized/realized P&L, total account value, cash per currency, FX-conversie, asset weights, sector/currency/region exposure, open-order-adjusted exposure, portfolio return, benchmark-relative return.

Rekenregel: geld, prijzen, percentages en hoeveelheden gebruiken `Decimal` waar toepasselijk.

## 6. Risk model roadmap
Per metric: basisniveau (historisch, rolling), later niveau (regime-aware/conditional), plus eenvoudige NL uitleg.
- Volatility: schommeling van rendement.
- Beta (CAPM): gevoeligheid t.o.v. benchmarkmarkt.
- Correlation/Covariance: samen bewegen van assets.
- Drawdown: daling vanaf vorige top.
- Downside deviation: alleen negatieve variatie.
- Sharpe: extra rendement per totale risico-eenheid.
- Sortino: extra rendement per neerwaarts risico.
- Information Ratio: extra rendement t.o.v. benchmark per tracking-fout.
- Tracking error: afwijking t.o.v. benchmark.
- VaR/CVaR: verliesgrens en verwacht verlies voorbij grens.
- Concentration risk: te grote weging in asset/sector/land/valuta.
- Liquidity risk: moeilijk kunnen handelen zonder grote impact.
- Event risk: earnings, guidance, corporate actions.
- Currency risk: P&L-effect door FX-bewegingen.

## 7. Factor and benchmark model roadmap
Te ondersteunen factoren: markt, size, value, profitability, investment, momentum, quality, low-volatility, growth, dividend/yield.

Gebruikregels:
- factoren nooit standalone;
- altijd combineren met risk, valuation, portfolio context, datakwaliteit;
- factorscores en benchmarkvergelijking moeten auditeerbaar zijn.

## 8. Technical and market-behavior signal roadmap
Veilige inputs: 1/3/6/12m momentum, moving averages, relative strength, volatility regime, volume trend, drawdown-from-high, trend-break, mean-reversion.

Regel: technische signalen zijn **evidence-inputs**, nooit zelfstandig advies.

## 9. Fundamental valuation roadmap
Inputs: groei (omzet/winst), free cash flow, marges, ROE, ROIC, schuld/interest coverage, P/E, forward P/E (alleen betrouwbare bron), EV/EBITDA, P/B, P/S, FCF yield, dividend payout, sector-relative waardering, scenario-waardering, DCF met expliciete aannames.

Valuation-output moet onzekerheid + aannames expliciet tonen.

## 10. Probabilistic forecasting roadmap
Fasering:
1) baseline historisch model;
2) benchmark-relatief model;
3) volatiliteitsmodel;
4) factor-gebaseerde expected-returnlaag;
5) quantile/range forecasting;
6) ensemble;
7) onzekerheidskalibratie (bijv. conformal) waar haalbaar;
8) model-disagreement + confidence.

Outputvormen (geen fake precieze koersdoelen): p10/p50/p90, kans op winst/verlies, expected downside, confidence, validity window, waarom model fout kan zitten.

## 11. Portfolio construction and action-translation roadmap
Constructie-referenties: mean-variance, minimum variance, risk parity, later kandidaat: Black-Litterman.

Met constraints: position-size, cash buffer, concentratielimieten, turnover-awareness, later tax/compliance.

Actielabels: Kopen, Langzaam bijkopen, Houden, Bekijken, Verminderen, Verkopen, Vermijden, Cash houden, Geen actie, Geblokkeerd.

Final label moet deterministisch uit Python-rules komen, niet direct uit AI.

## 12. Suggestion gate model
Vereiste gates vóór zichtbare suggestie:
- IBKR identity valid;
- portfolio vers;
- market data vers;
- benchmark beschikbaar;
- FX beschikbaar indien nodig;
- geen unresolved corporate action;
- geen stale/failing scheduler (wanneer runtime bestaat);
- source credibility pass;
- prompt-injection scan pass;
- approved model version;
- acceptabele validation/backtest status;
- risk-limits geëvalueerd;
- audit package compleet.

Bij gate-fail: output **Geblokkeerd** of **Controle nodig**.

## 13. AI role roadmap
AI mag: rapporten samenvatten, events extraheren, risico/kansen detecteren, contradicties detecteren, evidence-linked uitlegdrafts maken, dissent check, simpele Nederlandse uitleg.

AI mag niet: financiële kernwaarden berekenen, prijzen/kansen verzinnen, direct buy/sell/hold beslissen, gates omzeilen, user-tekst als instructie behandelen, orders maken/versturen.

## 14. Validation and model-risk roadmap
- Backtests + walk-forward;
- time-series-safe/purged validatie;
- geen look-ahead of survivorship bias;
- kosten/slippage aannames;
- benchmarkvergelijking;
- prediction diary;
- drift/cov-shift monitoring;
- calibration checks;
- model registry/versioning;
- challenger models;
- rollback rules.

## 15. Decision Package dependency
Minimale velden:
asset identity, IBKR portfolio snapshot, market snapshot, benchmark snapshot, FX snapshot (indien nodig), factor scores, risk metrics, valuation metrics, forecast range, evidence refs, AI event signals (indien gebruikt), gate outcomes, deterministisch label, NL uitleg, validity/expiry, audit links.

## 16. Suggested staged implementation plan
- **Phase A**: read-only portfolio valuation prep.
- **Phase B**: market data + benchmark foundation.
- **Phase C**: risk metrics.
- **Phase D**: factor + technical signals.
- **Phase E**: fundamental inputs.
- **Phase F**: probabilistic baseline.
- **Phase G**: validation + model registry.
- **Phase H**: Decision Package foundation.
- **Phase I**: deterministische suggestion translator.
- **Phase J**: AI explanation + dissent layer.
- **Phase K**: later user-approved action-draft flow.

Per fase geldt: doel, benodigde data, output, blockers, en expliciete “nog niet toevoegen”-lijst (geen execution/live ordergedrag).

## 17. First recommended implementation slice
Aanbevolen volgende slice: terug naar Task 125D-principe — read-only portfolio valuation preparation vanuit duurzame IBKR snapshots met expliciete blocked/missing-market-data status. Geen market-data runtime, geen suggesties, geen orders, geen fake prijzen.

## 18. Glossary (simple Dutch)
- Rendement: opbrengst/verlies over periode.
- Risico: kans dat uitkomst tegenvalt.
- Volatiliteit: hoe sterk waarde op en neer gaat.
- Benchmark: referentie om mee te vergelijken.
- Beta: gevoeligheid t.o.v. benchmark.
- Correlatie: mate waarin twee assets samen bewegen.
- Drawdown: daling vanaf eerdere top.
- Factor: eigenschap die rendement mee kan verklaren.
- Momentum: recente trendsterkte.
- Waardering: hoe duur/goedkoop asset lijkt.
- Fundamentele analyse: analyse van bedrijfsresultaten/financiën.
- Technische analyse: analyse van prijs/volume patronen.
- Voorspelling: inschatting van mogelijke toekomstige uitkomst.
- Kansbereik: bandbreedte met kansen (bijv. p10/p50/p90).
- Confidence: hoe zeker model is binnen grenzen.
- Decision Package: compleet onderbouwd beslisdossier.
- Dataversheid: hoe actueel data is.
- Audit trail: volledige navolgbare geschiedenis.

## 19. Sources and research notes
Compacte bronset voor roadmap-onderbouwing:
- Markowitz (1952), portfolio selection (MPT).
- Sharpe (1964), CAPM.
- Fama & French (1993), factor model basis.
- Carhart (1997), momentumfactor uitbreiding.
- NIST AI RMF 1.0, AI-modelrisico/governance.
- Hyndman & Athanasopoulos, forecasting/workflow discipline.
- Lopez de Prado, time-series-safe/purged CV principes.
- Recent conformal time-series literatuur voor onzekerheidskalibratie.
- CFI/educatieve risk-ratio bronnen voor gebruikersgerichte uitlegterminologie.

Deze bronnen ondersteunen architectuurkeuzes; ze activeren geen runtimegedrag.
