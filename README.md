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
