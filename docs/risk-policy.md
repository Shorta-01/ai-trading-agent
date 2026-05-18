# Risk Policy (Paper-only v1)

## Kernregel
Versie 1 is strikt paper-only en risk-first.

## Verplichte risicoregels
- Positielimieten (max positie, max ETF-allocatie, max individuele aandeelallocatie).
- Minimale cashreserve (eerste opbouw en normaal bedrijf).
- Geen leverage.
- Geen opties.
- Geen short selling.
- Geen penny stocks.
- Geen illiquide assets.

## Blokkeerregels
- Geen trade bij datakwaliteitsfalen.
- Geen trade bij risico-overtreding.
- Geblokkeerde suggesties tonen altijd expliciete reden.

## Gedragsregels
- Geen overtrading.
- Niet alles meteen investeren.
- Beslissings-cooldown verplicht.
- “Insufficient evidence”-status totdat er voldoende paperhistoriek is.
- Geen stale advice bij scheduler/data-update falen.

## Capability-handhaving (nieuw)
- De backend moet capabilityregels afdwingen voor opvolgen, onderzoek, actiesuggesties, papieren orders, papieren transacties en portefeuilletoegang.
- UI-instellingen mogen geblokkeerde productregels nooit overrulen.
- Dormante koop/verkoopcode voor geblokkeerde categorieën is niet toegestaan.
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 11 data-source strategie
- Domeincontracten toegevoegd voor bronbeleid, betrouwbaarheid, gebruiksrechten, versheid en failure policy.
- IBKR blijft enige toekomstige broker/execution route; geen runtime integraties toegevoegd.
- Publieke nieuws- en websitebronnen zijn standaard niet geschikt voor suggestion eligibility.
- Geen data kwaliteit of traceerbaarheid betekent geen advies/suggestie.

