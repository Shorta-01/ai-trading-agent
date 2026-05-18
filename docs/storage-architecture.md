# Storage Architecture

## Opslaglagen
1. **PostgreSQL/TimescaleDB** voor gestructureerde data, tijdreeksen, portfolio, transacties, instellingen, suggesties en jobs.
2. **Immutable raw archive** voor originele bronbestanden/snapshots.
3. **Research & audit archive** voor AI-input/output, referenties, model/promptversies en besliscontext.

## Auditlog
Append-only of hash-ready auditlog voor controleerbaarheid, herleidbaarheid en tamper-evident evolutie.

## Point-in-time regel
Beslissingen en backtests moeten point-in-time correct zijn; geen toekomstige informatie in historische beslissingen.

## Verplichte tijdvelden
Records ondersteunen o.a. as_of_date, valid_from, valid_to, published_at, retrieved_at, used_in_run_id, source_snapshot_id.

## Dataflow (target)
1) Fetch
2) Immutable raw opslag
3) Source record
4) Data quality checks
5) Normalisatie naar DB
6) Python berekening
7) Controlled AI research package
8) Schema-validatie AI output
9) Decision/risk combinatie
10) Suggestiecreatie
11) Risk approve/block
12) UI-publicatie
13) Actie/executie logging
14) Outcome tracking

## Backup en restore
Backups zijn verplicht, maar pas vertrouwd na periodieke restore-tests.

## Migratiepad Raspberry Pi -> mini PC
Infra blijft platform-onafhankelijk via Docker Compose, env-files, named volumes en gestandaardiseerde data-export/import zonder code rewrite.
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 11 data-source strategie
- Domeincontracten toegevoegd voor bronbeleid, betrouwbaarheid, gebruiksrechten, versheid en failure policy.
- IBKR blijft enige toekomstige broker/execution route; geen runtime integraties toegevoegd.
- Publieke nieuws- en websitebronnen zijn standaard niet geschikt voor suggestion eligibility.
- Geen data kwaliteit of traceerbaarheid betekent geen advies/suggestie.

\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 14 update
Data-quality gate en suggestion eligibility foundations toegevoegd. Deze stap maakt geen aanbevelingen en geen execution.
\n## Task 15 update\nAction suggestion engine foundation toegevoegd: candidate -> capability/data-quality gates -> eligibility -> risk placeholder -> cost/tax placeholder -> suggestion draft. Dit genereert nog geen echte aanbevelingen, geen orders en geen automatische uitvoering.
