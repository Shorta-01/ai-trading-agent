# UI Principles

## Eenvoudige Nederlandse interface
De UI moet duidelijk en begrijpelijk blijven voor niet-experts.

## Hulptekstverplichting
Elk veld, elke status en elke actie krijgt eenvoudige Nederlandse helptekst/tooltip.

## Geen onverklaard jargon
Complexe termen alleen in detail/advanced schermen met begrijpelijke uitleg.

## Hoofdsecties (NL)
Dashboard, Prestaties, Actiesuggesties, Portefeuille, Volglijst, Kansen en waarschuwingen, Transactiegeschiedenis, Belgische fiscaliteit en compliance, Instellingen.

## Voorbeeld-hulpteksten
- **Actie:** “Wat het systeem nu voorstelt (bijv. kopen, houden of geen actie).”
- **Risico:** “Hoe groot de kans is op grotere schommelingen of verlies.”
- **Vertrouwen:** “Hoe zeker het systeem is op basis van huidige data.”
- **Gerealiseerde winst/verlies:** “Winst of verlies op verkopen die al afgerond zijn.”
- **Ongerealiseerde winst/verlies:** “Winst of verlies op posities die je nog bezit.”
- **Gemiddelde aankoopprijs:** “De gemiddelde prijs die je betaalde voor deze positie.”
- **Cashreserve:** “Het deel van je vermogen dat in cash blijft als buffer.”
- **Geblokkeerd:** “Deze actie mag niet door een risico- of kwaliteitsregel.”
- **Geen actie:** “Nu niets doen is de beste keuze volgens de huidige data.”
- **Datakwaliteit:** “Geeft aan of de gebruikte data volledig en betrouwbaar is.”

## Capabilitylabels voor toekomstige UI (nieuw)
- Toegestaan
- Alleen opvolgen
- Geblokkeerd
- Niet toegestaan in versie 1

Extra hulptekst:
“Dit product mag in versie 1 niet worden gekocht of verkocht. Je kan het alleen opvolgen als marktcontext.”
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).

## Task 14 update
Data-quality gate en suggestion eligibility foundations toegevoegd. Deze stap maakt geen aanbevelingen en geen execution.
\n## Task 15 update\nAction suggestion engine foundation toegevoegd: candidate -> capability/data-quality gates -> eligibility -> risk placeholder -> cost/tax placeholder -> suggestion draft. Dit genereert nog geen echte aanbevelingen, geen orders en geen automatische uitvoering.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.

## API-naar-UI regel (Task 17)
- API-responses die bedoeld zijn voor UI-weergave moeten eenvoudige Nederlandse labels en helpteksten bevatten.
- Elke zichtbare veldnaam, status en actie moet een duidelijke Nederlandse uitleg of tooltiptekst hebben.
