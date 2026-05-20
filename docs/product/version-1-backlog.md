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
- source-to-asset linking foundation (Task 72 storage/API, audit/reference/status-only, blocked for suggestions)

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
- source-to-asset linking runtime/detection/matching beyond foundation (Task 72 foundation completed; audit/reference-only, blocked for suggestions)
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
- portfolio grid (read-only snapshot UI toegevoegd in Task 77; verdere runtime-verdieping pending)
- watchlist grid
- action badges + explanation panel
- IBKR read-only integration (positions/cash/open orders/executions snapshots foundation toegevoegd in Task 75/76; echte connectieruntime pending)
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


## E) Post-Task 72/72B/72C sync status

- Task 72: source-to-asset linking **foundation exists** (storage/API, audit/reference-only).
- Task 72B: storage mypy row-to-record typing en API pytest 503 failures gerepareerd; geen runtimegedrag gewijzigd.
- Task 72C: resterende API pytest source-link create→list fake repository persistence failure gerepareerd; geen runtimegedrag gewijzigd.
- CI-status na Task 72C: **groen**.
- Source-to-asset links: **audit/reference/status-only**.
- Source-to-asset links: **blocked for suggestions**.
- Asset detection from sources: **runtime pending**.
- Watchlist proposal/user-confirm flow: **runtime pending**.
- Market data/freshness/runtime validation: **runtime pending**.
- Suggestion engine runtime: **runtime pending**.
- Probabilistic forecast runtime: **runtime pending**.
- IBKR runtime: **runtime pending**.


## F) Release 1 functional workflow capabilities (locked, not implemented yet)

Volgende capabilities zijn verplicht voor Release 1 volgens `docs/product/release-1-functional-workflow-blueprint.md` en zijn momenteel **niet geïmplementeerd**:

- IBKR sync engine (positions, cash, orders, executions/fills, timestamps)
- market data engine (freshness + recalculation inputs)
- Decision Package storage/API/UI
- Suggestions-grid (Actief / Verlopen / Historiek)
- IBKR Action Center (Te keuren / Actief bij IBKR / Historiek)
- actie-draft workflow (prefill, edit, approval, submit, lock, status-follow-up)
- safety checks + instellingen (draft en backend hard checks)
- usable-cash berekening voor buy-readiness
- AI-analytics modules + schema-valid, versioned signal outputs
- daily portfolio/watchlist briefing
- user upload → recalculation/revalidation triggers
- Release 1 end-to-end acceptance workflow

Belangrijk: dit zijn functionele werkitems voor toekomstige implementatietaken; deze PR voegt geen runtimecode toe.


## G) Task 74 update

- Moderne GUI shell + dashboard foundation is toegevoegd.
- Dashboard gebruikt veilige empty states: geen fake portfolio-/broker-/suggestiedata en geen fake chartwaarden.
- Navigatie-shell voor Release 1 workflow bestaat (Dashboard, Portefeuille, Volglijst, Suggesties, IBKR Acties, Onderzoek, Historiek, Instellingen).
- Geen IBKR runtime, market-data runtime, suggestion runtime, AI runtime of ordergedrag toegevoegd.

- [x] Task 75 — IBKR portfolio sync engine foundation (read-only status + portfolio snapshots + API basis).
- [x] Task 76 — IBKR executions/open-orders sync foundation (read-only snapshots + API; geen ordersubmission/-wijziging/-cancel, geen action drafts/suggesties/Decision Packages/AI/market-data/forecast runtime, geen fake broker/order/execution data).
- [x] Task 76B / PR #153 — API mypy repair op sync run count typing (`int`), CI terug groen, geen runtimewijziging.
- [x] Task 77 — Read-only Portefeuille-grid UI vanuit bestaande IBKR snapshot-endpoints (`/ibkr/sync/status`, `/ibkr/portfolio/positions`, `/ibkr/account/cash`, `/ibkr/orders/open`, `/ibkr/executions`), zonder ordergedrag/suggesties/AI/market-data/forecast of fake data.
