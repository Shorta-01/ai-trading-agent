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
- **API-backend (apps/api):** domeinlogica, validatie, audit, policy-handhaving.
- **Workers (apps/worker):** geplande analyses, dataverwerking en monitoringjobs.
- **Pakketten (packages/*):** domeinmodules (risk, portfolio, tax, audit, ai, enz.).
- **Opslag:** PostgreSQL/TimescaleDB + immutable raw archief + research/audit archief.
- **Infra (infra/docker):** Docker Compose-gedreven deployment en portabiliteit.

## Lokale development (placeholder)
Definitieve setup-instructies volgen in een volgende fase. Deze repository bevat nu bewust alleen fundament, documentatie en mappenstructuur.

## No-live-trading principe
De applicatie mag in versie 1 geen echte broker-orders uitvoeren, geen live-accounts aansturen en geen real-money transacties automatiseren.

## Eenvoudige Nederlandse UI-principe
Alle hoofdschermen, labels, waarschuwingen en acties moeten begrijpelijk zijn voor niet-experts. Elke veldwaarde krijgt eenvoudige Nederlandse helptekst/tooltip.
