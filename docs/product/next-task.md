# V1 expansion queue: complete

Slices 13–22 are merged. V1 is feature-complete. The morning chain
runs end-to-end (06:30 Europe/Brussels), the manual approval gate
remains the only order-authorisation surface, every persisted record
keeps `safe_for_*=False`, and `GET /v1/release-readiness` reports
whether the operator's environment is V1-ready.

## What ships in V1

- **Foundation** (Slices 1–12): paper portfolio + audit base, IBKR
  read-only sync, market-data + EODHD, forecast engine, suggestion
  labels, Decision Packages, action drafts + dry-run safety, paper
  order submission, reconciliation + Prediction Diary, Research Desk,
  AI explanation layer, Belgian TOB, daily briefing.
- **§21 doctrine relock + scheduler skeleton** (Slice 13).
- **Ensemble predictors** (Slices 14–18): PredictorProtocol + GBM,
  Momentum, Mean-Reversion, QVM, AI foundation TS-model.
- **Universe scan** (Slice 17).
- **Fractional Kelly + risk-parity sizing** (Slice 19).
- **Full IBKR order vocabulary** (Slice 20): LMT, MKT, STP, STP_LMT,
  TRAIL, TRAIL_LMT, BRACKET.
- **Morning chain orchestrator** (Slice 21): the 06:30 cron drives
  market-data → forecast → suggestions → Decision Packages → action
  drafts → daily briefing.
- **V1 release readiness** (Slice 22): deterministic scorecard
  endpoint, env-var checklist + operator runbook, end-to-end
  acceptance test.

## Out of V1 scope (post-V1 widening)

- Full ~5 000-ticker universe-scan expansion.
- Real TimesFM / Chronos / Lag-Llama provider clients.
- IBKR conditional orders + GTC/OPG TIF variants.
- Multi-account portfolios.
- Mobile app.
- Briefing item source distinction
  (portfolio / watchlist / universe_scan_candidate).
- Persisted per-leg morning-chain outcomes (V1 keeps only the
  failed-leg summary on the audit row's `error_text`).

The next chat/session should pick a post-V1 widening from the list
above or start a fresh V1.1 scope discussion with the owner before
opening a new task ticket.
