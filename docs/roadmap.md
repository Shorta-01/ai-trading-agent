# Roadmap

## Milestone 1: Trustworthy paper core
Fundament voor paper portfolio, audittrail, risicohandhaving en betrouwbare datastromen.

## Milestone 2: AI explanation and research layer
Gecontroleerde AI-uitleglaag met schema-validatie en strikte policy-afbakening.

## Milestone 3: Discovery and monitoring
Uitbreiding met discovery- en intraday-monitoringmodi.

## Milestone 4: Backtesting and performance evaluation
Backtesting, walk-forward evaluatie, performance attribution en calibratie.

## Milestone 5: IBKR paper integration (later)
Later pas broker-koppeling voor papercontext; live uitvoering blijft buiten v1.

## Expliciet niet in versie 1
- Geen live trading.
- Geen real-money execution.
- Geen broker order-routing.
- Geen automatische plaatsing van echte orders.

## Toegevoegd binnen paper foundation
- Ondersteuning voor een aparte paper asset-zone: **Mijn termijnrekeningen** (contracten + pure berekeningshelpers).
- API-endpoints, database-opslag en frontend-flow voor termijnrekeningen blijven expliciet future work.

## Capability roadmap (nieuw)
- Capabilities inbouwen in paper order creation en transaction-guardrails.
- Capabilities blootstellen via API-contracten.
- Toegestaan/alleen opvolgen/geblokkeerd zichtbaar maken in de Nederlandse UI.
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 11 data-source strategie
- Domeincontracten toegevoegd voor bronbeleid, betrouwbaarheid, gebruiksrechten, versheid en failure policy.
- IBKR blijft enige toekomstige broker/execution route; geen runtime integraties toegevoegd.
- Publieke nieuws- en websitebronnen zijn standaard niet geschikt voor suggestion eligibility.
- Geen data kwaliteit of traceerbaarheid betekent geen advies/suggestie.

