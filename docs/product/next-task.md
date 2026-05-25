# Task 176

Slice 21 — Scheduler-driven 07:00 morning chain. Replaces the Slice
13 daily-briefing skeleton with the full orchestrator chain so the
06:30 Brussels cron pre-computes the 07:00 briefing without
operator intervention.

Scope:
- New `morning_chain` orchestrator in `apps/api` that wires the
  existing slice runtimes in sequence:
  market-data sync → ensemble forecast → asset suggestions →
  Decision Packages → action drafts → daily briefing. Each leg
  short-circuits with a stable failure code if its predecessor
  fails; nothing crashes the scheduler.
- Replace the skeleton `run_daily_briefing_job(...)` callable
  registered in Slice 13's APScheduler with a thin wrapper that
  invokes the morning chain and captures the per-leg outcome on
  the `scheduler_runs` audit row.
- Briefing surfaces the universe-scan candidates beside portfolio
  + watchlist rows. The briefing item now distinguishes
  `source = "portfolio" | "watchlist" | "universe_scan_candidate"`.
- Settings `scheduler_enabled` stays default False; the morning
  chain is invokable manually from a new
  `POST /scheduler/runs/morning-chain` route for the V1
  release-readiness slice to exercise it end-to-end.
- Manual approval gate stays; no draft auto-submits.
- Tests cover: chain stops cleanly on a leg failure (with the
  stable code on the run row); briefing items include the new
  source; manual route runs the chain once.

No new persisted records beyond the existing `scheduler_runs`
audit table; the morning-chain row carries the per-leg outcomes in
its `details_json` payload.
