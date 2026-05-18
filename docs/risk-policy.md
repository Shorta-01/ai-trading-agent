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

\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 14 update
Data-quality gate en suggestion eligibility foundations toegevoegd. Deze stap maakt geen aanbevelingen en geen execution.
\n## Task 15 update\nAction suggestion engine foundation toegevoegd: candidate -> capability/data-quality gates -> eligibility -> risk placeholder -> cost/tax placeholder -> suggestion draft. Dit genereert nog geen echte aanbevelingen, geen orders en geen automatische uitvoering.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.

## Status- en settings-API regels (Task 17)
- De status-API mag geen service als actief tonen als die service niet echt actief is.
- Ontbrekende IBKR- of OpenAI-configuratie moet gerelateerde jobs blokkeren.
- API-responses mogen geen geheimen of geheime waardes blootstellen.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## Storage and migration risk gates (Task 21)
- Storage not ready blocks first-run setup creation writes.
- Storage not ready blocks paper transaction persistence.
- Missing audit storage blocks future suggestion/approval persistence.
- Migration-required status must block writes until resolved.
- Backup not tested must be visible as warning or blocker based on operation context.


## Storage trust and credential risk (Task 22)
- Running a PostgreSQL container does not mean storage is trusted.
- Writes remain blocked until migrations, audit persistence, and backup/restore readiness are implemented.
- Missing credentials or placeholder/default credentials are unsafe for production use.
