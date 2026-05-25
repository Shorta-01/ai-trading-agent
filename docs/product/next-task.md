# V1.1 complete — fresh scope discussion needed for V1.2

**V1.1 is feature-complete.** Slices 23-34 have all shipped, the V1.1
expansion queue is closed, and the V1.1 acceptance test pins the
combined V1+V1.1 scorecard into the ready-for-production
configuration.

No coded slice is queued. The next task requires an owner-driven
scope discussion before any code lands. V1.2 candidate themes
(documented across `version-1-backlog.md`, `version-1-1-backlog.md`,
and the §22 scope register but **not yet committed**):

- **Predictor families** — new predictors beyond the V1 five
  (volatility-as-prediction, options-implied probabilities,
  sentiment-from-research-as-predictor, PEAD post-earnings drift).
  V1.1's auto-weighted ensemble + leaderboard make adding a sixth
  vote mechanically straightforward; what's locked is *which*
  family to add first.
- **Real-money path** — the live-money slice. V1.1 stays paper-first
  by doctrine; any real-money work needs its own scope discussion +
  separate manual-approval doctrine + a deeper compliance review.
- **Multi-account portfolios** — operator manages > 1 IBKR account
  from one cockpit. Requires storage refactor (account_id on every
  audit row + cross-account reconciliation rules).
- **Mobile app** — Next.js → React Native or PWA. UX panels from
  Slice 33's API contract are mobile-friendly but the layout work
  is post-V1.1.
- **Full ~5 000-ticker universe materialisation** — replaces the
  Slice 31 representative ALL_5K extras with the EODHD bulk-list
  endpoint. Operator-side rate-limit work + per-set cache TTL
  tuning.
- **Real TimesFM / Chronos / Lag-Llama clients** — Slice 30 declared
  the operator surface but only wired the Anthropic Claude TS
  provider. Each additional provider is a focused slice plus a
  budget-routing decision.
- **ibapi `Order.conditions` + extended `Order.tif` submission-client
  extension** — Slice 32 locked the data model + dry-run + storage
  shape; the actual TWS submission needs an end-to-end test against
  a real paper account.
- **Next.js UX panels** — Slice 33 shipped the API contract; the
  browser-side rendering layer is post-V1.1.
- **Real-time intraday predictor evaluation** — V1.1 stays daily,
  scheduler-driven.

Before any of the above starts, please discuss scope and lock the
selected theme(s) into `version-1-product-experience-locks.md`
§23. A new backlog file (`version-1-2-backlog.md`) + scope register
(`version-1-2-scope-register.md`) will replace this `next-task.md`
once the first V1.2 slice is committed.

Until then, the daily morning chain (`GET /v1/release-readiness`
should report `status="ready"` once every locked env-var is set)
continues to run on V1.1 with the §22 rebuild knobs operator-toggled.
