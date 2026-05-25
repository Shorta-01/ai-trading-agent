- V1.1 scope locked via owner sign-off after V1 ship. Locked decisions:
  - Heavy dependency lock relaxed: `numpy` + `pandas` + `statsmodels` allowed inside `packages/portfolio`; `packages/storage` stays stdlib + SQLAlchemy + Alembic; `apps/api` is unchanged.
  - AI provider budget locked at €20–€50/mo via `CLAUDE_AI_BUDGET_MONTHLY_EUR` (default `50`); daily-morning-chain only, no on-demand AI; prompt-caching mandatory; default Claude Haiku for explanations + smaller Claude tier for forecasts.
  - Conditional order vocabulary extends to the full IBKR condition set (price + time + margin + volume + execution); TIF extends to `{DAY, GTC, OPG, IOC}`.
  - Universe-set operator-selectable via `UNIVERSE_SET` env var with three locked sets: `SP500`, `EU600`, `ALL_5K`.
  - Feedback loop + auto-weighted ensemble: ensemble combiner gains `weight_strategy=equal_weight | auto`; `auto` weights by inverse-Brier-score over rolling 90d, clipped to [0.05, 0.40] per predictor.

Out of scope (confirmed not in V1.1, deferred to a later widening):
- Multi-account portfolios.
- Mobile app.
- Real-time intraday predictor evaluation (V1.1 stays daily, scheduler-driven).
- Briefing item source distinction (portfolio / watchlist / universe_scan_candidate flow through the existing suggestion-row path).
- Real money: V1.1 still ships paper-first; the live path needs a separate scope discussion before any real-money slice.
- New predictor families beyond the V1 five (volatility-as-prediction, options-implied probs, sentiment-from-research-as-predictor, PEAD post-earnings-drift) — deferred to V1.2 once V1.1's feedback loop measures the existing five.
- Backtest persistence beyond audit rows (V1.1 keeps the backtest leaderboard computed on demand; persisted historical backtest results land in a later slice if needed).
- AI provider redundancy / fallback chain (V1.1 ships Anthropic Claude only; multi-provider routing is post-V1.1).
- Cloud deployment (V1.1 stays on the Raspberry Pi 5 + NVMe + Docker Compose target locked in `docs/deployment.md`).
