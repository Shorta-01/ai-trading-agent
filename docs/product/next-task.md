# Task 186

Slice 31 — V1.1 universe scan expansion + operator-selectable
universe set. Lifts the locked universe registry from the V1
hand-curated ~325 set to three operator-selectable sets per the
§22.4 lock.

Scope:
- Extend `universe_registry` in `apps/api` with two new
  registries:
  - **`EU600`** — Stoxx Europe 600 constituents
    (Bel20 + AEX + CAC40 + DAX40 + IBEX35 + FTSE MIB + Stoxx
    Nordic 30 + Swiss SLI + UK FTSE 100 mid-caps);
    estimated ~600 EODHD symbols deduplicated.
  - **`ALL_5K`** — S&P 500 + S&P 400 mid-cap + S&P 600 small-
    cap + Russell 1000 ex-S&P + NASDAQ-100 + Stoxx 600 + Bel20
    + AEX + CAC40 + DAX40 + UK FTSE 100. Roughly ~5 000
    tickers after de-duplication.
- `UniverseEntry` gains an optional `country_code` field so the
  Stoxx 600 path can carry country tags; `locked_universe(set_code)`
  returns the deduped set for the operator's selected code.
- `apps/api/config.py` setting `universe_set` (already declared in
  Slice 23 with default `SP500`) is now consumed by
  `universe_scan_sync.scan_universe(...)`.
- **Per-set EODHD caching**: each universe set has its own
  `asset_fundamentals_snapshots` cache layer — the scan walks the
  set and only re-fetches an entry when the cached snapshot is
  older than the universe-scan cache TTL (new setting,
  default 24h). Reduces EODHD call volume from N calls/day to
  ~N/N_TTL — material for the 5K set.
- Storage paging on `list_latest_universe_snapshots(...)` so the
  briefing surface doesn't load the full 5K rows when only the
  top-N candidates are needed; new `limit` + `min_factor_count`
  parameters.
- Operator-facing read route: `GET /universe/registry?set=SP500`
  returns the deduplicated registry for the requested set so the
  Slice 33 UX upgrade can render a chooser.
- Tests cover: deduplication across overlapping indices; each
  universe-set returns a sane minimum size; `scan_universe(...)`
  honours `universe_set`; paging boundary; cache TTL skip.

Manual approval gate stays; safety booleans hard-False on every
persisted record.

When Slice 31 ships, Slice 32 (conditional orders + GTC/OPG/IOC)
is unblocked.
