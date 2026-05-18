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
