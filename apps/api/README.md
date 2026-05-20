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

## Task 36 API first-run paper setup persistence
- `POST /portfolio/setup/preview` valideert eerst de paper-only invoer en probeert daarna de eerste paper setup op te slaan.
- Persistency blijft strikt paper-only; geen broker-sync, geen IBKR, geen OpenAI en geen echte trading.
- Writes zijn alleen toegestaan als storage aan staat, `database_url` is gezet en migratie-readiness veilig is.
- De API gebruikt een expliciete tijdelijke checked connection per request (geen startup connectie).
- Er is geen globale engine/session/sessionmaker en geen databaseconnectie bij import of startup.
- Bij blokkades geeft de endpoint een veilige, eenvoudige Nederlandse foutmelding.

## Task 38 API system event recorder helper
- De API bevat nu een helper om systeemmeldingen veilig op te slaan via het storage package.
- Deze helper is strikt storage-readiness-gated: alleen write bij storage aan, database-url gezet en veilige migratie-readiness.
- De helper gebruikt per call een expliciete checked connection (`require_writable=True`).
- Er is nog steeds geen startup databaseconnectie, geen globale engine/session en geen sessionmaker.
- Er zijn nog geen GUI-overzichten, event-list endpoints, archive/resolve routes of hard delete gedrag toegevoegd.
- Er is nog geen globale exception middleware en geen automatische logging door de hele API.
- Er is geen broker/IBKR/OpenAI-gedrag toegevoegd in deze taak.

## Task 39 actieve systeemmeldingen endpoint
- `GET /system/events/active` toegevoegd als read-only endpoint voor open/actieve systeemmeldingen.
- Endpoint is storage-readiness-aware en gebruikt alleen een expliciete tijdelijke checked connection per request (`require_writable=False`) als storage is ingeschakeld en `database_url` aanwezig is.
- Geen startup databaseconnectie, geen globale engine/session en geen sessionmaker.
- Endpoint doet geen writes: geen create/update/resolve/archive/delete.
- Er is nog geen GUI-overzicht voor systeemmeldingen.
- Er zijn nog geen resolve/archive-routes, geen hard delete en geen automatische globale exception middleware.

## Task 44 trading instellingen read-only uit opslag
- `GET /settings/trading` probeert opgeslagen trading instellingen te lezen als storage is ingeschakeld en `database_url` aanwezig is.
- Endpoint gebruikt per request een expliciete checked connection met `require_writable=False` (geen writes).
- Als opslag niet beschikbaar is, geen rij bestaat, of een veilige storagefout optreedt, valt de response terug op veilige domein-standaardinstellingen.
- Dit blijft read-only: er is nog geen update-endpoint, geen UI-scherm, en geen IBKR/OpenAI-gedrag.

## Task 45 trading instellingen beheren
- `GET /settings/trading` en `PUT /settings/trading` ondersteunen nu laden en veilig opslaan van trading instellingen.
- `Toegestane beleggingen` blijft de harde veiligheidsfilter.
- `Mijn strategie` blijft voorkeur/ranking en kan veiligheidsblokkeringen niet opheffen.
- Versie 1 geblokkeerde asset types blijven read-only zichtbaar.
- Geen IBKR/OpenAI/trading-uitvoering toegevoegd in deze taak.

## Task 48 IBKR status en non-secret configuratie
- `GET /broker/ibkr/status` geeft nu een Nederlandstalige placeholder-status op basis van lokale API-configuratie.
- Endpoint doet geen IBKR netwerkcalls, geen SDK-client creatie, geen databasewrites en geen credentialtoegang.
- Nieuwe non-secret settings in API-configuratie: `ibkr_enabled`, `ibkr_expected_environment`, `ibkr_account_id_hint`, `ibkr_gateway_url`, `ibkr_connection_timeout_seconds`, `ibkr_status_check_enabled`.
- Standaardwaarden blijven veilig: koppeling uit, verwacht `paper`, geen account/gateway hints, timeout 10 seconden, statuscheck uit.
- Credentials worden niet opgeslagen en orders blijven geblokkeerd (`can_submit_orders=false`, `blocks_orders=true`).
- Er is in deze taak geen `PUT /broker/ibkr/settings`; opslaguitbreiding voor IBKR-configuratie volgt in een latere storage-taak.
- Ai Trading Agent blijft een volledig tradingplatform met paper-only IBKR-account in versie 1.


## Task 59 veilige onderzoeksbron-bestandupload API
- `POST /research/sources/{library_source_id}/upload-file` toegevoegd als veilige upload-foundation.
- Upload slaat raw bestand lokaal op in gecontroleerde archiefmap (`API_RESEARCH_UPLOAD__ARCHIVE_DIR`).
- SHA-256 hash wordt berekend tijdens schrijven en als metadata opgeslagen.
- Upload slaat bronmetadata + bestandsmetadata + processing-status op.
- Geen parsing, OCR, tekstextractie, AI-analyse of samenvatting in deze stap.
- Geen OpenAI-calls, geen IBKR-calls, geen suggesties/watchlist/orders.
- Uploads zijn bewijs voor later onderzoek, geen handelsinstructie.

## Task 61B deterministische tekstextractie (TXT/MD/CSV)
- `POST /research/sources/{library_source_id}/extract-text` extraheert deterministisch tekst uit alleen `.txt`, `.md`, `.csv`.
- Extractie gebruikt UTF-8/UTF-8-SIG, normaliseert regeleinden naar `\n`, berekent SHA-256, en slaat genormaliseerde tekst op in gecontroleerde archiefmap (`API_RESEARCH_EXTRACTION__EXTRACTED_TEXT_ARCHIVE_DIR`).
- Metadata (hash, preview, karakter- en regeltelling, status) wordt opgeslagen in `research_extracted_texts`.
- Extractie blijft metadata-only: geen AI-analyse, geen credibility scoring, geen prompt-injection scanning, geen suggesties/watchlist/orders.
- PDF/DOCX/XLSX/PPTX parsing en OCR zijn nog niet geïmplementeerd.
- Geëxtraheerde tekst blijft geblokkeerd voor suggesties tot latere veiligheidscontroles bestaan.
