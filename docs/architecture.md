# Architectuur

## Backend/frontend scheiding
- Frontend: eenvoudige Nederlandse weergave, hulpteksten, duidelijke acties.
- Backend: data-inname, validatie, scoring, risicocontrole, audit, explainability.

## Professionele beslisstack
1. Universe Selection
2. Research and Signal Generation
3. Portfolio Construction
4. Risk Management
5. Execution Simulation
6. Reconciliation and Accounting
7. Tax and Compliance
8. Performance Attribution
9. Self-Learning (voorstel-gedreven, niet autonoom)

## Hoofd-backendmodules (doelarchitectuur)
Gedocumenteerde enginefamilies: universe, data quality, portfolio, risk, decision, execution simulation, tax/compliance, performance, audit, self-learning.

## Hoofd-frontendsecties
Dashboard, Prestaties, Actiesuggesties, Portefeuille, Volglijst, Kansen/Waarschuwingen, Transactiegeschiedenis, Asset Detail, Belgische fiscaliteit/compliance, Instellingen, Audit/leerinzichten.

## Versie 1 grenzen
- Paper-only.
- Geen live trading.
- Geen broker execution.
- Geen IBKR-verbinding in deze fase.

## Paper-only guardrail
Alle architectuurkeuzes ondersteunen eerst controleerbare paper workflows met volledige audittrail en zonder real-money uitvoering.
