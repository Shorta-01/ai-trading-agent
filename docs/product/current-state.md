# Current State (na Task 66)

## 1) Current status summary

- Repository-status: Task 64 PR CI was green before merge; no failing status is attached to the merge commit.
- Projectstatus: nog foundation-heavy, geen complete Version 1 applicatie.
- Meest volwassen deel: Onderzoeksbibliotheek / Research Source Archive.
- Echte Suggestion Engine runtime, probabilistische forecast-runtime en IBKR runtime zijn nog niet voltooid.
- De probabilistische asset-outlook doctrine is vastgelegd in `docs/product/probabilistic-asset-outlook-doctrine.md`.
- `docs/product/next-task.md` wijst nu naar Task 67: evidence extraction foundation voor research-bronnen.

## 2) Implemented foundations

### Core foundation

- Repositorystructuur, API skeleton, worker skeleton, web skeleton, Docker Compose skeleton en CI-basis zijn aanwezig.
- Gedeelde `packages` voor domein/storage/audit/portfolio/enz. bestaan.
- Decimal-gebaseerde financiële primitieve contracten zijn aanwezig.
- Paper-only domeinconstraints zijn vastgelegd in contracts/guardrails.

### Settings / system status

- Settings foundation is aanwezig.
- Storage status/readiness checks bestaan.
- Systeem-events/foutenlogboek foundation bestaat.
- Resolve/archive event flow is als foundation voorzien.

### IBKR foundation

- IBKR research notes + ADR’s aanwezig (`docs/adr`).
- IBKR adaptercontracten bestaan.
- Niet-geheime configuratiebasis bestaat.
- Veilig placeholder endpoint `/broker/ibkr/status` bestaat.
- Account mode blijft unknown tot echte verificatie.
- Geen echte IBKR calls.
- Geen order submission.

### Research/Suggestion foundations

- Contracts aanwezig voor Research en Suggestion Engine.
- Suggestion lifecycle contracts aanwezig.
- Suggestion validity window concepten aanwezig.
- Blocked/conditional suggestion concepten aanwezig als contract/lock.
- Action suggestion concepten aanwezig.
- Evidence/audit concepten aanwezig.
- Data freshness contracts aanwezig.
- Source credibility contracts aanwezig.
- Prompt-injection defense contracts aanwezig.
- Market calendar/trading-hours contracts aanwezig.
- AI Event Intelligence contracts aanwezig.
- Quant research/model contracts aanwezig.
- Probabilistische asset-outlook doctrine is productmatig vastgelegd, maar nog niet als runtime geïmplementeerd.

### Onderzoeksbibliotheek / Research Source Archive

- Migratie `0010_research_source_archive` is toegevoegd.
- Storage DTO’s/contracts en repository foundation bestaan.
- Metadata-only API foundation bestaat.
- Nederlandse UI foundation bestaat.
- Veilige file upload API bestaat.
- File upload UI bestaat.
- Gecontroleerde archive storage bestaat.
- SHA-256 hashing bestaat.
- File type/size/filename validatie bestaat.
- Path traversal rejection bestaat.
- Uploaded-file metadata wordt opgeslagen.
- Processing status blokkeert suggesties.

### Extracted text foundation

- Migratie `0011_research_extracted_text` is toegevoegd.
- `research_extracted_texts` tabel bestaat.
- `ResearchExtractedTextRecord` bestaat.
- Repository methods bestaan.
- Deterministische TXT/Markdown/CSV extractie-runtime bestaat.
- Extracted text archive storage bestaat.
- Extracted text hash/preview/metadata bestaat.
- Onderzoeksbibliotheek UI kan tekstextractie starten voor ondersteunde TXT/MD/CSV uploads.
- UI toont extractiestatus en metadata, inclusief ondersteuning, karakters, regels, preview en tijdstip indien beschikbaar.
- Extracted text blijft geblokkeerd voor suggesties.
- Geen PDF/DOCX/XLSX/PPTX extractie.
- Geen OCR.
- Geen AI-analyse.
- Geen evidence extractie-runtime.

### Deterministische documentclassificatie foundation

- Deterministische documentclassificatie contracts en runtime foundation bestaan.
- Categorieën bestaan voor annual_report, quarterly_report, investor_presentation, etf_factsheet, news_article, broker_report, user_note, market_data_export en unknown.
- API endpoint `POST /research/sources/{library_source_id}/classify-deterministic` bestaat.
- Classificatie gebruikt metadata, bestandsnaam en bestaande extracted-text preview.
- Classificatie slaat een classificatierecord en processing-status op.
- Classificatie blijft metadata-only en blokkeert suggesties expliciet.
- Geen AI-analyse.
- Geen source credibility runtime scoring.
- Geen prompt-injection runtime scan.
- Geen evidence extractie-runtime.
- Geen watchlist/IBKR/order-acties.

## 3) Current non-complete areas

Nog niet compleet / runtime pending:

- geen echte Suggestion Engine runtime
- geen probabilistische forecast-runtime
- geen asset-master runtime
- geen market-data ingestie
- geen feature-store runtime
- geen forecast target engine
- geen backtesting/walk-forward runtime
- geen probability calibration runtime
- geen echte OpenAI/AI research runtime
- geen AI Event Intelligence runtime
- geen deep search agent
- geen volledige prompt-injection runtime analyse (wel scanstatus-opslag)
- geen source credibility runtime scoring-engine (wel status-opslag/API foundation)
- geen evidence extractie-runtime
- geen complete watchlist runtime/grid
- geen complete portfolio runtime/grid
- geen IBKR read-only verbinding
- geen IBKR order submission
- geen reconciliatie-runtime
- geen quant model execution-runtime
- geen Belgische tax/compliance runtime
- geen production backup/restore systeem

## 4) Current safe posture

- Geüploade bestanden zijn evidence, geen instructies.
- Extracted text is evidence, geen instructies.
- Deterministische classificatie is evidence metadata, geen advies.
- Alles blijft geblokkeerd voor suggesties tot toekomstige validatiegates bestaan.
- Upload/extractie/classificatie mag geen watchlist-entry, suggestie, IBKR actie of order aanmaken.
- Toekomstige forecasts zijn probability/range outputs, geen zekere prijsvoorspellingen en geen orders.

- Task 65 afgerond: prompt-injection runtime scanstatus wiring toegevoegd (opslaan + latest ophalen), met conservatieve blokkade voor suggesties in alle gevallen.
- Task 66 afgerond: source credibility assessment status wiring toegevoegd (opslaan + latest ophalen), met conservatieve blokkade voor suggesties in alle gevallen.

Task 67 afgerond: evidence extraction foundation toegevoegd (opslag + API). Evidence-items blijven geblokkeerd voor suggesties; geen AI-analyse, geen watchlist/IBKR/order-gedrag.
