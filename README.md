# Portfolio Outlook Manager

## Doel van het project
Portfolio Outlook Manager is een professionele **AI-ondersteunde paper portfolio research- en beslissingsomgeving**. Het systeem helpt een gebruiker bij het analyseren van toegelaten ETF's, aandelen en valuta's, en geeft duidelijke actiesuggesties in eenvoudige Nederlandse taal.

## Belangrijke waarschuwing: versie 1 is paper-only
- Versie 1 werkt **uitsluitend** met papergeld.
- Geen live trading.
- Geen real-money orders.
- Geen broker execution.
- Geen automatische orderplaatsing.

## Kernprincipes
- **Complexe backend, eenvoudige Nederlandse frontend.**
- **Python berekent, AI legt uit.**
- AI is onderzoek/uitleg, niet uitvoering.
- Risicoregels en audittrail zijn leidend.

## High-level architectuur (foundation)
- **Frontend (apps/web):** eenvoudige Nederlandse UI met hulpteksten.
- **API-backend (apps/api):** FastAPI shell met health-endpoints en basisconfiguratie.
- **Workers (apps/worker):** placeholder workerproces met veilige paper-only statusfunctie.
- **Pakketten (packages/*):** placeholder domeinmodules (risk, portfolio, tax, audit, ai, enz.).
- **Nieuw:** `packages/domain` bevat gedeelde, gevalideerde domeincontracten (data-shapes, geen tradinglogica).
- **Nieuw:** `packages/portfolio` bevat paper accounting helperberekeningen (puur, deterministisch, Decimal-only).
- **Opslag:** PostgreSQL placeholder via Docker Compose; nog geen businessmodellen/migraties.
- **Infra (infra/docker):** Docker Compose-gedreven development setup en portabiliteit.

## Lokale development (technische skeleton)

### API
```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn portfolio_outlook_api.main:app --reload --app-dir src
```

### Worker
```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python src/portfolio_outlook_worker/main.py
```

### Web
```bash
cd apps/web
npm install
npm run dev
```

### Docker Compose
```bash
cd infra/docker
docker compose up --build
```

## No-live-trading principe
De applicatie mag in versie 1 geen echte broker-orders uitvoeren, geen live-accounts aansturen en geen real-money transacties automatiseren.

## Eenvoudige Nederlandse UI-principe
Alle hoofdschermen, labels, waarschuwingen en acties moeten begrijpelijk zijn voor niet-experts. Elke veldwaarde krijgt eenvoudige Nederlandse helptekst/tooltip.

- Nieuw in de paper-only foundation: contracten en berekeningshelpers voor **Mijn termijnrekeningen**.

- Nieuw: backend-foundation voor een paper-only asset capability registry met allowed/watch-only/blocked regels.
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.

## Task 17 update
De API bevat nu read-only, Nederlandstalig voorbereide status- en instellingen-samenvattingsendpoints voor de toekomstige web-UI, zonder secrets of externe runtime-calls.

- Nieuw: de webapp bevat nu een modern Nederlandstalig dashboard als veilige paper-only foundation.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.
