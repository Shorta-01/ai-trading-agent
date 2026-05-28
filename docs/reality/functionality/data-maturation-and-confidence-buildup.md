# Data Maturation and Confidence Buildup

**Scope.** Functionality-level reality doc answering the question: **how do the system's suggestions evolve from day 1 (low data, low confidence) to mature operation?** Per the queue.md T-012b spec: "If no explicit maturation logic exists, the file says so and the finding becomes a Phase 1c gap entry."

**Answer**: explicit maturation logic **DOES exist** — this is not a pure gap. The system has a genuine sample-size-driven confidence-buildup mechanism + per-predictor minimum-history gates + a calibration-coverage surface. The mechanism has limitations worth surfacing (bound to the single shipped predictor; sample-size proxy not deployment-age), but the core "more data → more confidence, gated below a minimum" logic is implemented.

**Carry-forward task** from the 2026-05-26 functional review.

## 0. TL;DR — the maturation mechanism

| Mechanism | Where | What it does |
|-----------|-------|--------------|
| Minimum-bars gate | `baseline_forecast.py:36` `MINIMUM_BARS_REQUIRED = 60` | No forecast produced below 60 bars (~3 months) |
| Sample-size confidence curve | `baseline_forecast.py:193-204` `_confidence_from_sample_size` | 0.40 at 60 bars → 0.95 at 252 bars (1 year), linear ramp between |
| Per-predictor min-bars | `BASELINE_FORECAST_MIN_BARS` / `MOMENTUM_MIN_BARS` / `MEAN_REVERSION_MIN_BARS` / `QVM_MIN_BARS` | Each predictor has its own minimum-history floor |
| Calibration coverage surface | `/calibration/coverage?window_days=90` + `<CalibrationCoverageBadge>` | 3-state: healthy / warning / insufficient (diary empty) |
| Confidence label derivation | `forecasting_step.py:329` `derive_confidence` | Maps the numeric confidence to Hoog / Gemiddeld / Laag |

**The "day 1 → mature" story IS implemented** via the bar-count proxy: a freshly-tracked asset with 60 bars gets 0.40 confidence; the same asset at 252 bars gets 0.95. As the system accumulates EOD bars per asset, confidence ramps.

## 1. The minimum-bars gate

`packages/portfolio/src/portfolio_outlook_portfolio/baseline_forecast.py:36`:

```python
MINIMUM_BARS_REQUIRED: Final[int] = 60
```

A forecast cannot be produced for an asset with fewer than 60 historical bars (~3 trading months). Below this, the forecast is blocked (one of the 5 block reasons documented in T-015 §5 — "insufficient history").

On **day 1** of tracking a new asset: if the asset has < 60 bars of EOD history available from EODHD (T-014), no forecast is generated. The user sees a blocked/empty state with a Dutch explanation.

As the system (or EODHD's backfill) accumulates bars, the asset crosses the 60-bar threshold and forecasts begin.

## 2. The sample-size confidence curve

`baseline_forecast.py:193-204`:

```python
def _confidence_from_sample_size(n: int) -> float:
    """Bounded confidence score: 0.4 at the minimum sample, asymptotes to 0.95
    at one year, capped there. Purely a heuristic — communicates "more bars,
    more confidence" without overclaiming."""

    if n <= MINIMUM_BARS_REQUIRED:
        return 0.40
    if n >= DEFAULT_TRADING_DAYS_PER_YEAR:
        return 0.95
    span = DEFAULT_TRADING_DAYS_PER_YEAR - MINIMUM_BARS_REQUIRED
    progress = (n - MINIMUM_BARS_REQUIRED) / span
    return 0.40 + 0.55 * progress
```

The curve:
- **At 60 bars** (the minimum): confidence = 0.40.
- **At 252 bars** (`DEFAULT_TRADING_DAYS_PER_YEAR`, 1 trading year): confidence = 0.95 (capped).
- **Between**: linear ramp — `0.40 + 0.55 × (n - 60) / (252 - 60)`.

The docstring is explicit about the intent: "communicates 'more bars, more confidence' **without overclaiming**." The 0.95 cap is deliberate — even at infinite data, the heuristic never claims certainty. This is the codebase's explicit data-maturation model.

**This is a genuine, well-reasoned maturation mechanism.** It directly answers the functional-review question: a day-1 asset (60 bars) is at minimum confidence; a 1-year-tracked asset is at maximum.

## 3. Per-predictor minimum-bars gates

Per T-046 §1, the portfolio package defines 6 predictor modules. Each has its own minimum-bars constant (exported from `packages/portfolio/src/portfolio_outlook_portfolio/__init__.py`):
- `BASELINE_FORECAST_MIN_BARS`
- `MOMENTUM_MIN_BARS`
- `MEAN_REVERSION_MIN_BARS`
- `QVM_MIN_BARS`

Each predictor refuses to forecast below its own history floor. A momentum predictor needs more bars than a baseline; a QVM factor predictor needs even more (it consumes fundamental + value + momentum signals).

**Limitation**: per T-046 §1 (ADR-0003 1-of-7), only `historical_bootstrap_v1` runs in production. The per-predictor min-bars for the 5 unwired predictors (`momentum`, `mean_reversion`, `qvm`, `ai_ts`, `gbm`) are **defined but unused** — they only matter once those predictors are wired (T-046 §1 Must). §6.1.

## 4. The calibration coverage surface

`apps/web/components/CalibrationCoverageBadge.tsx` reads `GET /calibration/coverage?window_days=90` (`apps/api/src/portfolio_outlook_api/forecast_routes.py:467`) and renders 3 locked states:

| State | Colour | Condition |
|-------|--------|-----------|
| `healthy` | green | Sufficient forecasts evaluated + hit-rate within band |
| `warning` | yellow | Some evaluation but below health threshold |
| `insufficient` | grey | Diary empty (0 evaluated in window) |

The badge text (`:114-115`):
- Empty: "Geen voorspellingen geëvalueerd in laatste {window_days} dagen."
- Populated: "{forecasts_evaluated} voorspellingen geëvalueerd in laatste {window_days} dagen; {hit_rate}% binnen p10–p90 band."

This is the **system-level maturation surface** — distinct from per-asset confidence (§2). It tells the user "how much has the calibration loop learned yet?". On day 1: `insufficient` (grey, diary empty). As the prediction diary accumulates evaluated forecasts (T-016), it moves to `warning` then `healthy`.

The badge is mounted on the dashboard top row (T-011c §2.1) — making calibration maturity visible at a glance.

## 5. The confidence label derivation

`apps/worker/src/portfolio_outlook_worker/forecasting/forecasting_step.py:329`:

```python
confidence = derive_confidence(...)
```

The numeric confidence score (§2) maps to the locked 3-level Dutch label (Hoog / Gemiddeld / Laag) via `derive_confidence` (T-015 §3 documented the label vocabulary). At `:417`, the blocked-forecast path hard-codes `confidence_level="Laag"` — a blocked or insufficient forecast is always low confidence.

The chain: bars → `_confidence_from_sample_size` → numeric score → `derive_confidence` → Hoog/Gemiddeld/Laag label → surfaced on the decision package (T-017 §3.1 confidence badge) + action draft.

## 6. Limitations (Phase 1c surface)

The maturation logic exists but has 5 limitations worth surfacing:

1. **Bound to the single shipped predictor** (§3) — the per-predictor min-bars for 5 of 6 modules are defined-but-unused because only `historical_bootstrap_v1` runs (ADR-0003 1-of-7, T-046 §1). Until the ensemble is closed, maturation only operates on one predictor's view.
2. **Sample-size proxy, not deployment-age** (§2) — confidence ramps with bar count, NOT with how long the system has been live. An asset with 252 historical bars from EODHD backfill gets 0.95 confidence on day 1 of the system's operation, even though the system itself has zero track record on that asset. The confidence reflects data availability, not the system's demonstrated accuracy.
3. **Calibration coverage is separate from per-asset confidence** (§2 vs §4) — the per-asset confidence curve (§2) and the system-level calibration coverage (§4) are two independent maturation signals that aren't combined into one "is this suggestion trustworthy yet?" composite. The trust signal intent (dashboard §4.1 per T-011c) wanted a converged cue; reality has two separate surfaces.
4. **No shadow-mode observation maturation** (T-046 §6-§7 cross-ref) — intent §4 of `predictor-lifecycle.md` mandates a 3-month observation period where a new predictor's LIVE accuracy is measured before promotion. That's the deployment-age maturation the bar-count proxy doesn't capture. It's absent (T-046 §6-§7).
5. **The 0.95 cap is a global constant** — `_confidence_from_sample_size` asymptotes to 0.95 regardless of the asset's actual realised hit rate. A predictor that's been wrong 60% of the time on an asset still gets 0.95 confidence if it has a year of bars. Calibration (T-016) is the corrective layer, but it feeds predictor weights (T-024 §6) rather than per-asset confidence directly.

## 7. Verdict on the investigative question

The queue.md T-012b spec asked: "Documents (or explicitly notes as gap) how the system's suggestions evolve from day 1 to mature operation. If no explicit maturation logic exists, the file says so and the finding becomes a Phase 1c gap entry."

**The finding is NOT a pure gap.** Explicit maturation logic exists:
- Per-asset confidence ramps with sample size (§2) — well-reasoned, "no overclaiming" curve.
- Minimum-history gates prevent forecasting on thin data (§1, §3).
- System-level calibration coverage surface shows learning progress (§4).
- Confidence labels propagate to the user-facing decision package (§5).

The **partial-gaps** (§6) are:
- Maturation is sample-size-proxy not deployment-age (§6.2).
- Per-asset confidence + calibration coverage aren't composited (§6.3).
- Shadow-mode observation maturation absent (§6.4 → T-046 §6-§7).
- Confidence cap ignores realised accuracy (§6.5).

These partial-gaps map to existing Track 1c entries (T-046 §6-§7 predictor lifecycle) rather than introducing new ones. The core mechanism is sound; the refinements are Phase 4 candidates.

## 8. Out of scope

- T-015 forecast-generation deep dive (merged sibling).
- T-016 calibration + prediction-diary deep dive (merged sibling).
- ADR-0003 predictor ensemble gap (T-046 §1 — merged; cross-ref only).
- Shadow-mode + observation-period maturation (T-046 §6-§7 — merged).
- Prediction track record screen (T-016b — next functional-review addition).

## 9. References

- `packages/portfolio/src/portfolio_outlook_portfolio/baseline_forecast.py:36` (`MINIMUM_BARS_REQUIRED = 60`), `:193-204` (`_confidence_from_sample_size`)
- `packages/portfolio/src/portfolio_outlook_portfolio/__init__.py` (per-predictor min-bars exports)
- `apps/worker/src/portfolio_outlook_worker/forecasting/forecasting_step.py:329` (`derive_confidence`), `:417` (blocked → Laag)
- `apps/web/components/CalibrationCoverageBadge.tsx` (3-state maturity surface)
- `apps/api/src/portfolio_outlook_api/forecast_routes.py:467` (`/calibration/coverage`)
- T-005 `api-forecasting-and-market-data.md` (forecast routes)
- T-007 `worker-forecasting-and-decision-package.md` (forecasting step)
- T-014 `market-data-pipeline.md` (EODHD bar availability)
- T-015 `forecast-generation-and-labelling.md` §3 (confidence labels) + §5 (block reasons)
- T-016 `forecast-calibration-and-prediction-diary.md` (calibration loop)
- T-017 `decision-package-composition.md` §3.1 (confidence badge surfacing)
- T-046 `03-quant-and-forecasting-gaps.md` §1 (ADR-0003), §6-§7 (shadow + observation maturation)
- T-011c `dashboard-composition.md` §2.1 (CalibrationCoverageBadge on dashboard)
