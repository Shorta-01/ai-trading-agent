# Prediction Track Record Screen — Specification vs Implementation Status

**Scope.** Functionality-level reality doc documenting the prediction-track-record-screen specification + current implementation status. Per queue.md T-016b: "Documents the screen specification (filters by predictor / asset / window, aggregate views, drill-downs) and current implementation status."

**Answer**: the screen **does not exist**. The backend prediction-diary data is fully present (`GET /prediction-diary` returns deterministically-classified entries per T-016); **no frontend screen consumes it**. This becomes a Phase 1c missing-feature gap entry, paired with the absent predictor leaderboard UI (T-024 §10.7 + T-044 §4) — the prediction-track-record screen is intended to HOST the leaderboard.

**Carry-forward task** from the 2026-05-26 functional review.

## 0. TL;DR

| Element | Status |
|---------|--------|
| Backend prediction-diary data | **Present** — `GET /prediction-diary` + `POST /prediction-diary/evaluate` + `SqlAlchemyPredictionDiaryRepository` |
| Frontend prediction-track-record screen | **Absent** — no page in `apps/web/app/` consumes `/prediction-diary` |
| Screen spec (filters / aggregate views / drill-downs) | **Unimplemented** |
| The leaderboard the screen would host (intent) | **Absent** (T-024 §10.7) — backend API exists, UI doesn't |
| Adjacent surface | `<CalibrationCoverageBadge>` (a dashboard badge, NOT the screen) |

**Net**: backend ready, screen entirely absent. This is a clean missing-feature gap — distinct from T-012b (where the maturation mechanism existed) and closer to T-011b (where the queried thing was absent).

## 1. The intended screen specification

Per queue.md T-016b spec + intent cross-references:

### 1.1 Filters (per queue.md spec)
- **By predictor** — filter the diary to a single predictor's track record.
- **By asset** — filter to a single asset's prediction history.
- **By window** — time-window selection (matching the calibration window: 6 / 12 months per `prediction-diary-and-calibration.md` §3).

### 1.2 Aggregate views (per queue.md spec)
- Per-predictor hit rate, average return, calibration status over the window.
- Cross-predictor comparison (this is where the leaderboard lives — see §3).

### 1.3 Drill-downs (per queue.md spec)
- Individual prediction → realised outcome pairs.
- Hit / miss / partial / inconclusive classification (T-016 §2's 4 outcomes).
- Per-prediction evidence: which predictor, what forecast, what realised.

### 1.4 The leaderboard host relationship

`docs/intent/predictor-lifecycle.md:56`:

> "A read-only screen, linked from the prediction track record screen (T-016b — `docs/reality/functionality/prediction-track-record-screen.md`). Not a separate top-level entry."

The leaderboard (7 columns: hit rate, average return, Sharpe, max drawdown, calibration status, ensemble weight, last-backtest score — intent §3) is **linked from** the prediction track record screen, not a standalone page. So the track-record screen is the parent surface; the leaderboard is a child view. Both are absent.

## 2. The backend that exists

The prediction-diary backend is fully present (T-016 documented it):

### 2.1 `GET /prediction-diary` (`status_routes.py:2568`)

```python
@router.get("/prediction-diary")
def read_prediction_diary() -> dict[str, object]:
    """Return all Prediction Diary entries (most recent first)."""
    base = {
        "items": [],
        "help_nl": (
            "Prediction Diary entries zijn deterministisch geclassificeerd. "
            "Geen AI-scoring, geen silent self-learning."
        ),
        "safe_for_self_learning": False,
        "safe_for_model_retraining": False,
    }
    ...
    diary_repo = SqlAlchemyPredictionDiaryRepository(...)
    result = diary_repo.list_prediction_diary_entries()
    return base | {"status": "ok", ...}
```

The route returns ALL diary entries most-recent-first. **No filtering** — no `?predictor=`, no `?asset=`, no `?window_days=` query params. The spec's filters (§1.1) are not even at the API level; the route is a flat list-all.

### 2.2 `POST /prediction-diary/evaluate` (`status_routes.py:2476`)

Triggers the evaluation pass that marks expired forecasts hit/miss (T-016 §2). This is the diary's write-side closeout.

### 2.3 `SqlAlchemyPredictionDiaryRepository`

`list_prediction_diary_entries()` — the read method. Per `prediction-diary-and-calibration.md` §1, the diary is an event-sourced materialised view derived from the audit log — rebuildable byte-for-byte.

### 2.4 The safety flags

The route returns `safe_for_self_learning: False` + `safe_for_model_retraining: False` — the AGENTS.md "AI may not override risk rules" + "no silent self-learning" doctrine. The diary is read-only diagnostic data; it never feeds model retraining. This discipline is present even without a UI.

## 3. The leaderboard — also absent (cross-reference)

T-024 §3.5 documented the leaderboard backend: `GET /predictor/leaderboard` (`status_routes.py:3704`) + 3 backtest routes. T-024 §10.7 documented the leaderboard UI is absent. T-044 §4 recorded it as a missing feature (Should, Medium effort).

Since the prediction-track-record screen is intended to HOST the leaderboard (§1.4), building the track-record screen + the leaderboard are naturally paired Phase 2 work. Both consume existing backend data; both need a frontend.

## 4. The only adjacent surface

The closest existing frontend surface to "prediction track record" is `<CalibrationCoverageBadge>` (T-012b §4 + T-011c §2.1):
- Reads `GET /calibration/coverage?window_days=90`.
- Renders 3 states: healthy / warning / insufficient.
- Mounted on the dashboard top row.

But this is a **badge** (a single aggregate health indicator), not the **screen** (a filterable, drill-down-able track-record view). It tells the user "how's the calibration overall?" not "show me predictor X's track record on asset Y over the last 6 months". The screen the functional review specified is entirely absent.

## 5. Why the gap exists

The pattern matches the dashboard finding (T-011c §4): the backend data layer was built (diary repository, evaluation pass, deterministic classification, safety flags) but the frontend screen was never wired. The diary is queryable via API; no page queries it.

This is consistent with the broader audit pattern (T-043 §1 asymmetric discipline): the data + audit layer is rigorous (event-sourced, rebuildable, deterministically classified, safety-flagged), while the user-facing surface is absent. The prediction track record is forensically complete in storage + invisible to the user.

## 6. Phase 1c gap entry

This finding is a **missing-feature gap** belonging to T-044's category. Recording it here for the functional-review ledger:

- **Name**: Prediction track record screen (with predictor/asset/window filters + aggregate views + drill-downs, hosting the leaderboard).
- **Why it matters**: The user has no way to see "how accurate have my predictors been?" — the diary data exists but is unreachable from the UI. Combined with the absent leaderboard (T-024 §10.7), the entire predictor-evaluation surface is invisible. Without it, the user cannot make informed predictor promotion/retirement decisions (which intent §4-§5 of `predictor-lifecycle.md` surface as system-decision items).
- **Where it would live**: New page `apps/web/app/track-record/page.tsx` (or `/admin/predictors/`) + `apps/web/components/PredictionTrackRecord*.tsx`. Backend needs filter params added to `/prediction-diary` (currently list-all per §2.1). The leaderboard (T-044 §4) is the child view.
- **Effort**: **Large** — new screen + filter API extension + aggregate-view computation + drill-down + leaderboard child view. The diary data is present; everything UI-side + the filter API is new.
- **Dependency**: T-044 §4 (leaderboard UI — the child view). Backend filter params on `/prediction-diary`.
- **MoSCoW**: Should — the user-facing evaluation surface is important for predictor lifecycle decisions but not critical to per-order trading. Bundles naturally with T-044 §4 (leaderboard UI) + T-046 §6-§9 (shadow/observation/retirement infrastructure).
- **Originating reality**: T-016b (this doc) + T-016 (diary backend) + T-024 §10.7 (leaderboard UI absent).

This gap should be cross-referenced into the Track 1c T-044 missing-features ledger as a companion to T-044 §4.

## 7. Out of scope

- T-016 calibration + diary backend deep dive (merged sibling).
- T-024 leaderboard API + UI gap (merged sibling).
- T-044 §4 leaderboard UI missing-feature entry (merged — companion to this).
- Performance review screen (T-021b — separate functional-review addition; a DIFFERENT screen showing portfolio performance, not predictor track record).

## 8. References

- `apps/api/src/portfolio_outlook_api/status_routes.py:2476` (`POST /prediction-diary/evaluate`), `:2568` (`GET /prediction-diary`)
- `SqlAlchemyPredictionDiaryRepository` (the read repository)
- `apps/web/app/` (12 pages; none is a prediction-track-record screen)
- `apps/web/components/CalibrationCoverageBadge.tsx` (the only adjacent surface — a badge, not the screen)
- `docs/intent/prediction-diary-and-calibration.md` §1 (event-sourced diary architecture)
- `docs/intent/predictor-lifecycle.md:56` (the leaderboard-hosted-by-track-record-screen relationship)
- T-008 `web-pages.md` (frontend page inventory — confirms screen absent)
- T-016 `forecast-calibration-and-prediction-diary.md` (diary backend reality)
- T-024 `predictor-backtest-and-leaderboard.md` §3.5 (leaderboard API) + §10.7 (leaderboard UI absent)
- T-044 `01-missing-features.md` §4 (predictor leaderboard UI as missing feature — companion)
- T-046 `03-quant-and-forecasting-gaps.md` §6-§9 (shadow/observation/retirement — predictor lifecycle infra)
- T-012b `data-maturation-and-confidence-buildup.md` §4 (CalibrationCoverageBadge — the adjacent surface)
- T-011c `dashboard-composition.md` §4 (same backend-present-frontend-absent pattern)
