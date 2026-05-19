# API (FastAPI skeleton)

> Waarschuwing: versie 1 is strikt paper-only. Geen live trading, geen brokerkoppeling en geen echte orders.

## Lokaal starten

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn portfolio_outlook_api.main:app --reload --app-dir src
```

## Tests en checks

```bash
cd apps/api
pytest
ruff check .
mypy src
```
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.

## Read-only status/settings API foundation (Task 17)

Nieuwe read-only endpoints voor de toekomstige web-UI:
- `GET /system/status`
- `GET /settings/summary`
- `GET /usage/ai/summary`
- `GET /integrations/summary`
- `GET /ui/dutch-labels`

Eigenschappen:
- Geeft alleen veilige placeholder-data terug.
- Geeft geen geheimen terug.
- Leest of bewaart geen geheime waarden.
- Maakt geen IBKR-calls of OpenAI-calls.
- Maakt geen database-calls.
- Start geen worker jobs of scheduler.
- Alle UI-gerichte labels/hulpteksten zijn Nederlandstalig.
\n## Storage foundation update\nOpslagreadiness-contracten toegevoegd; opslag is nog niet ingesteld en setup/transacties worden nog niet bewaard. Backup blijft onveilig tot hersteltest slaagt.


## Database status clarification (Task 22)
- The API does not connect to PostgreSQL yet.
- The storage status remains planned/not active.
- Database connection and write-path implementation are later tasks.

## Task 31 storage configuration foundation
- API settings now include typed `storage` fields (`database_url`, `enabled`, `writes_enabled`).
- Safe default remains: no storage configured, no connection attempt, writes blocked.
- This task does not add database runtime wiring, engine/session creation, or persistence.
- Runtime readiness and write-path implementation will be added in a later task.

## Online opslagreadiness (Task 32)
- `GET /storage/status` blijft een offline/contract-check zonder databaseverbinding.
- `GET /storage/status/online` doet een expliciete, tijdelijke read-only databasecheck als storage is ingeschakeld én een database-url is ingesteld.
- De API maakt nog geen databaseverbinding bij startup en heeft nog geen globale engine/session.
- Deze check schrijft niets en zet writes niet aan.
- Writes blijven geblokkeerd tenzij migratiereadiness veilig is.
