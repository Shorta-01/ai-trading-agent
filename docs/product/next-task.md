# Task 168

Slice 13 — Doctrine relock + scheduler skeleton. This slice
implements the doctrine relocks captured in
`version-1-product-experience-locks.md §21` after the owner brainstorm
that followed Slice 12.

Scope:
- Relax `paper_only_mode` + `ibkr_expected_environment` from
  "blocks order" to "reports the mode the connected IBKR account is in".
  Add a dashboard `PAPER` / `LIVE` badge that surfaces the account mode
  IBKR reports; the runtime is identical for both.
- Drop the `account_mode_mismatch` dry-run failure code.
- Add APScheduler in-process (FastAPI lifespan-wired). New settings
  `scheduler_enabled` (default `False`) and `daily_briefing_cron`
  (default `0 30 6 * * *` Europe/Brussels). When enabled, the schedule
  triggers the existing daily briefing endpoint.
- Storage migration adding `scheduler_runs` table (one row per
  scheduled run: job name, scheduled_at, started_at, finished_at,
  status, error_text, safe booleans hard-False) so the audit chain
  records every automatic invocation.
- New routes `GET /scheduler/jobs` (read which jobs are registered) and
  `GET /scheduler/runs/latest` (read the most recent run).
- Web update: add the `PAPER` / `LIVE` badge on the Portefeuille page
  header and a small "Scheduler" panel showing the last run + next-fire
  time.

Disabled-by-default; manual approval gate stays; safety booleans
hard-False on every record and every response. No new predictors yet —
this slice clears the runway for slices 14–22.
