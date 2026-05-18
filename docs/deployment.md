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
