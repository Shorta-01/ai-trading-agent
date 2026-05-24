# Task 167

Slice 12 — Daily briefing + alert digest. The V1 product locks describe
a once-per-day Dutch briefing that summarises (a) the user's
portfolio status (positions, cash, FX freshness), (b) any new
suggestions / Decision Packages / action drafts produced since the last
briefing, (c) any prediction-diary outcomes that closed since the last
briefing, and (d) any critical action-draft state events.

Scope:
- Storage migration adding `daily_briefings` table (one row per
  briefing) and `briefing_alerts` (append-only items the briefing
  references).
- Pure-Python `daily_briefing` module in `packages/portfolio` that takes
  the typed inputs (positions, suggestions, drafts, diary entries,
  events) and returns a deterministic Dutch summary + structured alert
  list. AI never authors the briefing.
- New routes `POST /briefings/daily/compute` (gated on
  `daily_briefing_sync_enabled` + writable storage) and
  `GET /briefings/daily/latest`.
- Web "Dagbriefing" panel on the Portefeuille page surfacing the latest
  briefing and unread critical alerts.

Disabled-by-default; no broker execution; safety booleans remain
hard-False; no auto-execution from a briefing.
