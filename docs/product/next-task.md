# Task 158

Slice 3 — Baseline forecast engine (V1.1 stage), end-to-end. Add a pure
Python baseline forecaster that consumes the persisted market-data snapshots
and emits a probabilistic outlook per position: p10/p50/p90 ranges,
P(gain)/P(loss), expected volatility, downside risk, and explicit horizon
(initial: 1-month). No AI, no live fetch — historical-vol + drift baseline
only, deterministic, fully tested. Persist forecasts as a new
`AssetForecastRecord` so the Portefeuille and Volglijst pages can show a
read-only "Verwachte richting" badge per asset. Disabled-by-default; no
suggestions, no action drafts, no orders.
