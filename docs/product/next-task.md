# Task 172

Slice 17 — Universe scan. Wires the daily scan that populates the
`asset_fundamentals_snapshots` table for the QVM predictor (Slice 16)
and surfaces ranked candidates in the daily briefing.

Scope:
- New `universe_registry` module in `apps/api` listing the V1 locked
  universe: Bel20, AEX, CAC40, DAX, STOXX 600, S&P 500, NASDAQ-100
  (~5 000 tickers). Each ticker carries its EODHD symbol, sector and
  the index it belongs to. Static Python tables — no dynamic load.
- New `universe_scan_sync` orchestrator that, per ticker:
  * fetches the latest bars via `EodhdClient.fetch_eod_bars`
  * fetches fundamentals via `EodhdClient.fetch_fundamentals`
  * persists an `AssetFundamentalsSnapshotRecord`
  * computes a per-asset QVM score against the running universe snapshot
- Storage migration `0039_universe_scan_runs` adds a small
  `universe_scan_runs` table with one row per scan invocation
  (started_at, finished_at, status, scanned_count, persisted_count,
  failed_count, ranked_count, error_text). Safety booleans hard-False.
- New route `POST /universe/scan/run` gated on
  `universe_scan_sync_enabled` (default False) + writable storage +
  EODHD configured. Returns a structured summary.
- New route `GET /universe/scan/runs/latest` returns the most recent
  audit row.

Disabled-by-default; no broker action; safety booleans remain hard-False.
