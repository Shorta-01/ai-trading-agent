# Task 181

Slice 26 — V1.1 feedback loop + auto-weighted ensemble. The
slice that closes the predictor-quality feedback loop the Slice 22
audit identified as V1.1's biggest single lever.

Scope:
- Extend the Prediction Diary to track per-predictor outcomes
  (currently only the ensemble outcome is persisted). Storage
  migration `0042_prediction_diary_per_predictor` adds a child
  table `prediction_diary_predictor_contributions` keyed on
  `(diary_entry_id, model_code)` with the per-predictor
  outcome label + the predicted/realised return spread.
- Helper `compute_per_predictor_outcomes(...)` in
  `packages/portfolio` consumes the Slice 15 `EnsembleResult`
  + the realised price series and emits one row per
  contribution.
- Helper `compute_inverse_brier_weights(history, *, clip=(0.05, 0.40))`
  reads the persisted backtest rows from Slice 24 and produces a
  `{model_code: Decimal}` weighting dict by inverse-Brier-score
  normalised + clipped to the per-predictor band. Missing /
  blocked-only history defaults to the equal-weight strategy.
- Ensemble combiner gains a `weight_strategy: "equal_weight" | "auto"`
  argument. `auto` runs `compute_inverse_brier_weights` against
  a provided weight-history loader and falls back to equal-weight
  on insufficient data — the chain never goes dark.
- `forecast_sync` orchestrator threads the new strategy from a
  setting `ensemble_weight_strategy` (default `equal_weight`).
- New route `GET /predictor/leaderboard` returns the rolling
  per-predictor Brier-score + the corresponding auto-weight.
- Tests cover: per-predictor outcome computation correctness;
  inverse-Brier weighting math (zero clip, max clip, all-equal
  fallback); strategy switch on the combiner; route gating + Dutch
  copy.

Manual approval gate stays. AI is still one vote in the ensemble;
the auto-weight strategy may down-weight it but never silence it.
Safety booleans hard-False on every persisted record.

When Slice 26 ships, the predictor refactor work (Slices 27 + 28)
is unblocked.
