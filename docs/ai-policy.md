# AI Policy

## Rol van AI
AI is uitsluitend research- en uitleglaag.

## Hard rule
**Python berekent, AI legt uit.**

## Veiligheidsregels
- Fetched content is data, not instruction.
- Prompt-injection defense is verplicht.
- AI output moet schema-gevalideerd zijn.
- AI mag geen financiële kerncijfers voor beslissingen verzinnen.
- AI mag risicoregels niet overrulen.
- AI mag strategie/risico niet stilzwijgend wijzigen.
- Zelflerende voorstellen vereisen expliciete gebruikersgoedkeuring.

## AI en capabilitygrenzen (nieuw)
- AI mag watch-only categorieën onderzoeken en uitleggen binnen veilige context.
- AI mag geen koop/verkoopactiesuggesties maken voor watch-only of geblokkeerde categorieën.
- AI-output moet schema-gevalideerd zijn én capability-checks passeren voordat backendacties mogelijk zijn.
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

## AI-verbruik en kostenweergave (Task 17)
- De AI-verbruiksendpoint mag alleen gebruik tonen op basis van echte records of expliciete schattingen.
- Geen fake token- of kostcijfers.
- In deze foundationstap maakt de endpoint geen OpenAI-calls.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## AI persistence guardrails (Task 21)
- AI research records must later be persisted with source references and point-in-time metadata.
- AI outputs must be stored as data records, never as executable instructions.
- Prompt-injection text from external sources may never become system instructions.
- No AI research record may be used for future decisions unless source, timestamp, and audit link are persisted.
\n\n## Task 24A update\nIBKR wordt na koppeling de bron van waarheid voor brokerfeiten; lokale data blijft een spiegel voor analyse en audit. Er is nog geen echte IBKR-integratie in deze versie.


## Task 24B AI behavior for broker reconciliation
- AI may not describe broker/local differences as harmless unless reconciliation status explicitly allows that interpretation.
- Broker-dependent AI suggestions must later cite the latest broker sync and reconciliation records.
- Missing broker snapshots must block or clearly caveat broker-dependent suggestions.
