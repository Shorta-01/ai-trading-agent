# Docker Compose (development skeleton)

Deze map bevat alleen een lokale development-skeleton.

## Services
- `api`: FastAPI shell
- `worker`: worker shell zonder jobs
- `web`: eenvoudige Next.js UI
- `postgres`: infrastructurele placeholder voor latere persistente opslag

> TimescaleDB is bewust uitgesteld naar een latere taak om de skeleton eenvoudig en stabiel te houden.

## Starten

```bash
cd infra/docker
docker compose up --build
```

## Grenzen van deze fase
- Geen live trading
- Geen brokerkoppeling
- Geen AI-calls
- Geen externe marktdata-calls
- Database nog niet gekoppeld aan businessmodellen
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
