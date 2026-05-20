# Version 1 Backlog (operational source of truth)

Zie ook de einddoelarchitectuur in `docs/product/final-solution-vision.md`.

## A) Completed foundations

- repository/API/worker/web/docker/CI skeleton
- settings/status foundations
- system events foundation
- IBKR contracts/placeholders
- research source archive storage/API/UI
- safe upload
- TXT/MD/CSV extraction
- deterministic classification
- prompt-injection scan status storage/API
- source credibility status storage/API
- source evidence item storage/API
- probabilistic asset outlook doctrine
- CI quality rules
- asset master identity foundation (Task 71 storage/API, referentie/status-only)

## B) Still missing for Research Library

- PDF/DOCX/XLSX/PPTX extraction
- OCR (indien nodig)
- URL fetching + veilige snapshotting
- echte prompt-injection analysis engine
- echte source credibility scoring engine
- Evidence Ledger API/linking
- evidence review UI
- source conflict detection runtime
- source freshness/runtime validation
- asset detection from sources
- source-to-asset linking
- watchlist proposal flow met user confirmation
- multi-year report comparison runtime

## C) Still missing for core product

- asset master runtime verdieping (advanced identity validation/mapping)
- market data storage
- adjusted/unadjusted historical price data
- corporate actions
- FX rates + freshness
- market calendar runtime
- feature store
- forecast target definitions
- probabilistic baseline model
- backtesting/walk-forward validation
- probability calibration
- model registry/model risk controls
- scenario engine
- portfolio-level probability/risk
- suggestion engine runtime
- portfolio grid
- watchlist grid
- action badges + explanation panel
- IBKR read-only integration
- account mode verification
- broker snapshots
- reconciliation
- toekomstige paper-only IBKR action grid
- user-confirmed paper submission (pas na alle gates)
- audit viewer
- AI event intelligence
- OpenAI usage/cost dashboard
- Belgian tax/compliance support
- deployment/backups/restore testing

## D) Future but not Version 1

- live trading
- real-money execution
- automatic orders
- options
- futures
- leverage
- short selling
- crypto
- penny stocks
- CFDs
- complex derivatives
- high-frequency trading

- Task 68 completed: Evidence Ledger API/linking foundation voor research source evidence (audit-only, geen suggestion unlock).
- Task 69 completed: gate outcome + freshness policy foundation als storage/API basis (audit/status-only, geen suggestion unlock).
- Task 69B completed: repair op Task 69 met CI terug groen en zonder runtimegedrag te wijzigen.


- Task 70 completed: source conflict detection foundation (storage/API) als audit/status records; geen suggestion unlock.


## E) Post-Task 70/70B sync status

- Task 70: source conflict detection **foundation exists** (storage/API, audit/status-only).
- Task 70B: repair afgerond; CI groen; geen runtimegedrag gewijzigd.
- Source conflict detection runtime/analysis engine: **runtime pending**.
- Source conflict findings: **blocked for suggestions**.
- Source-to-asset linking: **runtime pending**.
- Asset master identity foundation: **implemented** (storage/API, referentie/status-only; suggestion-blocking).
- Asset master runtime verdieping (advanced identity validation/mapping): **runtime pending**.
- Source-to-asset linking foundation: **next missing foundation**.
- Market data/freshness/runtime validation: **runtime pending**.
- Suggestion engine runtime: **runtime pending**.
- Probabilistic forecast runtime: **runtime pending**.
- IBKR runtime: **runtime pending**.
