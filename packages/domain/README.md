# portfolio-outlook-domain

Dit package bevat alleen **gedeelde domeincontracten** voor Portfolio Outlook Manager.

## Wat dit package wel is
- Gevalideerde Pydantic-modellen en enums.
- Stabiele data-structuren voor API, workers en auditopslag.
- Financiële primitieve types op basis van `Decimal`.

## Wat dit package expliciet niet doet
- Geen tradinglogica.
- Geen AI-calls of promptlogica.
- Geen brokerintegratie.
- Geen database- of ORM-code.

## Waarom `Decimal`
Geld, aantallen, prijzen en percentages gebruiken `Decimal` om afrondingsproblemen van `float` te vermijden.

## Tests lokaal draaien
```bash
cd packages/domain
python -m pip install -e .[dev]
python -m ruff check .
python -m mypy src
python -m pytest -q
```

## Paper ledger and accounting contracts
- Alleen contracten (datavormen en validatie), geen accounting engine.
- Nog geen FIFO-verkoopallocatie-algoritme.
- Nog geen database/ORM-opslag.
- Geen broker-executie.
- Paper-only afbakening blijft actief.
- Financiële waarden blijven Decimal-only via `Money`, `Quantity` en `Percentage`.

## Termijnrekening-contracten
- Nieuwe contracten voor manuele termijnrekeningen: input- en projectiemodel.
- Ondersteunt vaste rente en vast intrestbedrag, plus kosten en geschatte taksen.
- Alleen validatie en datastructuur; geen tax engine of bankintegratie.

## Capability contracts
- `AssetCapability` en `CapabilityCheckResult` leggen centraal vast wat per categorie toegestaan, watch-only of geblokkeerd is.
- Inclusief reden-codes en eenvoudige Nederlandse uitleg voor latere UI-weergave.
\n## Update: execution/approval/research contracts\n- Paper-first is full workflow (niet prototype) met verplichte goedkeuring per koop/verkoop.\n- Execution modes: internal_paper, ibkr_paper, ibkr_live_read_only, ibkr_live_manual, blocked_auto.\n- Automatische trading blijft geblokkeerd; blocked_auto is altijd blocked.\n- IBKR paper is toekomstig execution target na setup en goedkeuring.\n- Broker-neutrale flow: suggestion -> approval -> execution_intent -> execution adapter.\n- IBKR metadata blijft in reference contracts (geen live API-calls).\n- AI research output is alleen onderzoek/uitleg; nooit approval/execution override.\n- Source/reference + hashes + archiefkoppeling vormen auditlijn: source -> report -> suggestion -> approval -> order -> transaction.\n- Geen persistence, geen DB-modellen, geen API/worker/frontend wijzigingen in deze stap.\n

## Task 11 data-source strategie
- Domeincontracten toegevoegd voor bronbeleid, betrouwbaarheid, gebruiksrechten, versheid en failure policy.
- IBKR blijft enige toekomstige broker/execution route; geen runtime integraties toegevoegd.
- Publieke nieuws- en websitebronnen zijn standaard niet geschikt voor suggestion eligibility.
- Geen data kwaliteit of traceerbaarheid betekent geen advies/suggestie.

\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
