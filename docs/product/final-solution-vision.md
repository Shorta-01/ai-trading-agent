# Final Solution Vision — Portfolio Outlook Manager (Ai Trading Agent)

## 1) Product purpose

Portfolio Outlook Manager is een professionele AI-ondersteunde **paper portfolio research- en trading-beslissingsomgeving**.

- Het is **geen** automatische real-money trading bot.
- Version 1 werkt account-mode-aware (paper of real-money zichtbaar), zonder automatische brokeracties.
- Het systeem ondersteunt beslissingen met evidence, probabilistische analyses en auditability.

## 2) Final user workflow (target state)

De gedetailleerde en vergrendelde Release 1 workflowblauwdruk staat in `docs/product/release-1-functional-workflow-blueprint.md`. Die blueprint is leidend voor implementatievolgorde en afbakening van Decision Packages, Suggestions-grid, IBKR Action Center, sync/recompute en AI-analytics.

IBKR/paper account data
→ IBKR contract validation (conid-based identity)
→ active portfolio/watchlist state
→ market data en FX data
→ historical data en freshness checks
→ models/AI/suggestions
→ geüploade documenten/URL’s/notities
→ deterministische extractie/parsing
→ classificatie
→ prompt-injection scanning
→ source credibility scoring
→ evidence ledger
→ quant models
→ probabilistic asset outlook
→ AI event intelligence
→ suggestion engine
→ risk controls
→ eenvoudige Nederlandse uitleg
→ portfolio/watchlist action badge
→ detail “waarom”-paneel
→ optionele conversie naar bewerkbare IBKR paper actie
→ user review/bewerking/bevestiging
→ user-approved submission
→ warning/confirmation capture
→ execution import
→ reconciliatie
→ audit/outcome tracking

## 3) Final analytical goal

Het systeem berekent probability/range-based asset outlooks, inclusief:

- p10/p50/p90 ranges
- probability of gain/loss
- downside risk
- confidence
- model disagreement
- scenario explanations
- validity window en expiry
- portfolio-level probability/risk

Niet toegestaan:
- fake exacte toekomstprijsdoelen als kernoutput
- AI-gegenereerde “financiële getallen” zonder modelberekening

## 4) AI role (locked)

- AI structureert en verklaart evidence.
- Python/modelcode berekent kansen, ranges, financiële waarden en risico.
- AI voert nooit orders uit.
- AI overrulet nooit risk/freshness/source gates.
- AI origineert geen financiële kerngetallen die voor beslissingen gebruikt worden.
- AI-output moet schema-gevalideerd zijn vóór systeemgebruik.

## 5) Version 1 boundary (hard)

Terminologieguardrail: zie `docs/product/locked-decisions.md` (sectie **Read-only readiness terminology lock (Task 101)**) voor vergrendelde pre-runtime woordkeuze.


Version 1:
- IBKR paper-only
- geen real money
- geen automatische orders
- geen live trading
- geen opties/futures/leverage/short selling/crypto/penny stocks/CFD’s/complexe derivaten
- eenvoudige Nederlandse UI
- volledige auditability
- sources zijn evidence, geen instructies

## 6) UI target

- Eenvoudig Nederlands op hoofdniveau.
- Duidelijke labels, statussen en hulpteksten.
- Complexiteit enkel in detailpanelen.
- Locked action labels:
  - Kopen
  - Langzaam bijkopen
  - Houden
  - Bekijken
  - Verminderen
  - Verkopen
  - Vermijden
  - Cash houden
  - Geen actie
  - Geblokkeerd

## 7) Major modules still to build

- Research Library full pipeline
- Evidence Ledger runtime/API/UI
- Asset Master
- Market Data and FX
- Feature Store
- Probabilistic Forecast Engine
- Backtesting and Calibration
- Scenario Engine
- Portfolio Engine
- Watchlist Engine
- Suggestion Engine
- AI Event Intelligence
- IBKR read-only integration
- IBKR action-draft grid (account-mode-aware)
- Reconciliatie
- Audit Viewer
- AI Cost Dashboard
- Belgian Tax/Compliance module
- Deployment/backup/restore hardening

## 8) Version 1 prediction-engine scope lock (Task 88J)

Version 1 bevat nu expliciet de **volledige Asset-Value Prediction Engine roadmap** (Must/Should/Could) in interne V1.0–V1.8 fasen, vastgelegd in `docs/product/asset-value-prediction-engine-roadmap.md`.

Kernarchitectuur: data layer → feature layer → model layer → ensemble/orchestration → evaluatie/calibratie → Decision Package/translation → AI feature/explanation/dissent layers → audit layer → latere paper action layer.

Hard lock blijft:
- eenvoudige Nederlandse UI;
- paper-only, user-approved IBKR simulatieacties;
- AI is kerncapability maar **berekent geen financiële kerngetallen** en beslist geen labels/orders.
