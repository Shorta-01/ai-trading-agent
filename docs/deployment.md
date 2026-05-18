# Deployment

## Startplatform
Eerste deploymentdoel: Raspberry Pi 5 + NVMe SSD + Docker Compose + bedraad netwerk + actieve koeling + externe backups.

## Migratiepad
Latere migratie naar mini PC/zwaardere server zonder code rewrite.

## Verplichte principes
- Docker Compose als standaard runtime.
- Portabiliteit naar linux/arm64 en linux/amd64.
- Gebruik van env-files en named volumes.
- Geen hardcoded lokale paden.
- Geen secrets in code.

## Backups en restore
Dagelijkse backups + periodieke restore-tests; een backup geldt pas als betrouwbaar na geslaagde restore-test.
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## Database deployment planning (Task 21)
- PostgreSQL deployment is planned via Docker Compose in a later implementation task.
- Raspberry Pi 5 deployments must use portable Linux ARM64 images where practical, while keeping Linux AMD64 compatibility.
- No hardcoded local filesystem paths are allowed for persistence services.
- Connection strings must come from environment variables or secret references, never hardcoded in code.
- Database backups must be encrypted.
- Trusted-backup status requires a successful restore test, not only a backup file.


## PostgreSQL development service foundation (Task 22)
- A local PostgreSQL development service is now available in Docker Compose.
- Production and Raspberry Pi deployments must use safe env vars or secret references (no committed passwords).
- Named volumes holding persistence data must be backed up.
- Backups must be encrypted.
- Backup trust requires restore tests before being marked reliable.
- Deployment remains portable across `linux/arm64` and `linux/amd64` where practical.
- No Raspberry Pi-specific application logic may be introduced.
