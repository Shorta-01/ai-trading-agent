# Worker (placeholder)

> Waarschuwing: deze worker is alleen een technische skeleton. Geen schedulerjobs, geen marktdata, geen brokercalls, geen AI-calls.

## Lokaal starten

```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python src/portfolio_outlook_worker/main.py
```

## Tests en checks

```bash
cd apps/worker
pytest
ruff check .
mypy src
```
\n\n## Runtime update\nContract-only update for backend runtime/service topology added in domain models for coordinated startup, health gating, and queue-first heavy workloads (no runtime implementation in this PR).
\n## Scheduler and background job planning\nContracts define planning only: plan -> eligibility -> skip/block/run status -> audit trace. Suggestion jobs require gezonde services en verse data; geen job voert trades uit. Zware AI/research taken horen in queue of externe worker, niet als onbeperkte Raspberry Pi scan.

## Task 16 foundation update
Settings/secrets metadata and OpenAI usage-cost budget contracts are added as domain-only foundations without real API calls or secret storage.

## Task 31 storage configuration foundation
- Worker settings now include typed `storage` fields (`database_url`, `enabled`, `writes_enabled`).
- Safe default remains: no storage configured, no connection attempt, writes blocked.
- This task does not add database runtime wiring, engine/session creation, or persistence.
- Runtime readiness and write-path implementation will be added in a later task.

## Task 33 worker storage readiness helper
- Worker heeft nu een expliciete read-only storage readiness helper (`build_worker_storage_readiness`).
- Bij startup gebeurt geen databaseverbinding.
- Er bestaat geen globale SQLAlchemy engine/session/sessionmaker in worker runtime.
- Runtime persistence is nog niet geïmplementeerd.
- Toekomstige worker-jobs moeten deze readiness eerst controleren voor storage writes.
- Writes blijven geblokkeerd tenzij migration readiness veilig is voor writes.
