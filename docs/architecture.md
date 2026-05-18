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
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n
