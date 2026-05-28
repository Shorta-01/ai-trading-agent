# Docker Compose (development skeleton)

Deze map bevat een lokale development-skeleton voor AI-Trading-Agent.

## Services
- `api`: FastAPI shell
- `worker`: worker shell zonder jobs
- `web`: eenvoudige Next.js UI
- `postgres`: lokale PostgreSQL development service (infrastructure only)

> TimescaleDB is bewust uitgesteld naar een latere taak om de foundation eenvoudig en stabiel te houden.

## Local PostgreSQL setup (development only)

1. Copy env example to a local env file:

```bash
cd infra/docker
cp .env.example .env
```

2. Set a local password in `.env`:

```bash
POSTGRES_PASSWORD=<your-local-dev-password>
```

Rules:
- `.env` is local-only and must never be committed.
- Replace the placeholder password before running PostgreSQL.
- Never use placeholder credentials in production.

3. Start PostgreSQL only:

```bash
docker compose up -d postgres
```

4. Check service health:

```bash
docker compose ps
```

Optional in-container readiness check:

```bash
docker compose exec postgres pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB"
```

5. Stop services:

```bash
docker compose down
```

6. Intentionally remove local database data:

```bash
docker compose down -v
```

⚠️ `down -v` removes the `postgres_data` volume and deletes local development database data.

## Backups & restore-test

Encrypted PostgreSQL backups (see `docs/deployment.md` for the full runbook):

```bash
# Configure BACKUP_DIR + BACKUP_GPG_PASSPHRASE_FILE in infra/docker/.env first.
make backup        # pg_dump → gzip → AES256 (GPG) → $BACKUP_DIR, prunes old files
make restore-test  # restores the latest backup into a throwaway container + verifies
```

A backup is only TRUSTED once `restore-test` passes against it. The scripts
live in `infra/docker/scripts/`.

## Grenzen van deze fase
- Geen live trading
- Geen brokerkoppeling
- Geen AI-calls
- Geen externe marktdata-calls
- Geen database-integratie in API/worker runtime
- Geen migraties
- Geen portfolio/setup persistence

PostgreSQL can run locally for infrastructure preparation, but the application does **not** write to it yet.

## Task 23 storage/migration note
- PostgreSQL container blijft beschikbaar voor toekomstige migraties.
- Alembic skeleton staat klaar in `packages/storage`.
- Draai nog geen migraties: er bestaat nog geen schema/migratie-revisie.
