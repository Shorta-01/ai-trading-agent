```yaml
id: T-024
title: Write reality doc for predictor backtest + leaderboard
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/predictor-lifecycle.md
decision_ref: docs/decisions/0014-predictor-lifecycle.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/predictor-backtest-and-leaderboard.md` does not exist (verified). Pure synthesis — every code site is cited in T-002 + T-007 + T-015 + T-016 reality docs or being inventoried via the background exploration agent:
  - T-002 `portfolio-predictors.md` — covered the portfolio-side predictor stubs.
  - T-007 `worker-forecasting-and-decision-package.md` — covered the per-asset block-bootstrap forecasting; ADR-0003 1-of-7-predictors gap originating finding.
  - T-015 `forecast-generation-and-labelling.md` — re-confirmed ADR-0003 gap for 4th time + documented `historical_bootstrap_v1` as the sole shipped predictor.
  - T-016 `forecast-calibration-and-prediction-diary.md` — covered the calibration + prediction-diary path (where shadow predictions would write).
  - T-022 `belgian-tax-computation.md` (just merged) — TOB computes are the only transaction-cost primitive available for backtest simulation.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the predictor lifecycle (backtest harness + shadow → promotion + retirement) + leaderboard surface workflow doc.
  - `predictor-backtest-and-leaderboard.md` — backtest harness presence/absence + walk-forward + look-ahead bias prevention + transaction cost simulation; backtest report storage; CI gate on predictor merge; leaderboard UI + API; 4-stage entry path; shadow-mode infrastructure; 3-month observation tracking; user-decision promotion + retirement surfaces; weight floor/ceiling enforcement.
- **Step 3 (one-line change):** write one cited workflow reality doc tracing predictor lifecycle end-to-end + the leaderboard surface.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; backtest harness presence/absence documented (with grep proof); leaderboard UI + API presence/absence documented; predictor registry enumerated (the 1 of 7 shipped — `historical_bootstrap_v1`); 4-stage entry path coverage documented; shadow-mode infrastructure documented; weight floor 10% / ceiling 40% implementation status documented; ≥ 10 Phase 1c findings incl. ADR-0003 re-confirmation (5th time); no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — AI explanation (T-023 — merged sibling), market data pipeline (T-014 — merged sibling). Architecture review (Track 1b T-036…T-043) and gap analysis (Track 1c T-044…T-049) are downstream consumers of this doc, not dependencies.

## Goal

Produce one workflow reality doc tracing the predictor lifecycle end-to-end — from backtest harness (if any) through shadow-mode (if any) to active ensemble inclusion (where the 1 shipped predictor lives) to retirement (if any). Also documents the leaderboard surface (UI + API) — whether the intent's 7-column read-only screen exists or is entirely absent. The doc surfaces the largest cumulative drift in the audit: intent §1-§7 lock a sophisticated walk-forward backtest + shadow infrastructure + leaderboard; reality is likely a single bootstrap predictor with no harness, no shadow, no leaderboard. ADR-0003 1-of-7-predictors gap gets its 5th re-confirmation.

## Context

`depends_on:` T-002 (portfolio predictors at module level), T-005 (API forecast routes). T-024 stitches the predictor inventory (T-015 §1-§2) with the calibration/diary surface (T-016 §3-§4) and the absent leaderboard/backtest surface to produce the end-to-end "from intent-§1 walk-forward harness to a sortable leaderboard table" story.

## Touch scope

Create:
- `docs/reality/workflows/predictor-backtest-and-leaderboard.md`

Read: T-002 + T-005 + T-007 + T-015 + T-016 reality docs + predictor-lifecycle intent + grep across `apps/`, `packages/`, `scripts/`, `notebooks/` for backtest/leaderboard sites.

## Acceptance criteria

- [ ] Output file exists at the locked filename.
- [ ] Backtest harness presence/absence documented (with grep proof — `backtest` / `walk_forward` / `rolling_window` / `historical_simulation` literals + any standalone backtest script).
- [ ] Predictor registry documented — the 1 shipped (`historical_bootstrap_v1`) vs the 7 mandated by ADR-0003 (5th time re-confirmation).
- [ ] Leaderboard UI presence/absence documented — frontend page/component grep.
- [ ] Leaderboard data API presence/absence documented — API route grep.
- [ ] 4-stage entry path coverage documented per intent §4 (backtest CI gate + shadow merge + 3-month observation + user-decision promotion).
- [ ] Shadow-mode infrastructure documented — any predictor table column for status/mode/shadow.
- [ ] Weight floor 10% / ceiling 40% enforcement documented per intent §6.
- [ ] ≥ 10 Phase 1c findings incl. ADR-0003.
- [ ] No source modification.

## Out of scope

- AI explanation surface (T-023 — merged sibling).
- Market data pipeline (T-014 — merged sibling; though backtest would consume from `market_data_latest_snapshots`).
- Architecture review (Track 1b future).
- Gap analysis (Track 1c future).

## Verification

- File exists.
- Grep proof for backtest harness presence/absence cited.
- Predictor registry inventory cited (file paths).
- Leaderboard surface presence/absence cited.
- ≥ 10 Phase 1c findings.

## Notes

T-024 closes Track 1a Reality Functionality (T-011…T-024). It is the final workflow-functionality doc before the 11 user/system workflow docs (T-025…T-035) and the Track 1b architecture review (T-036…T-043) begin. Expected: this doc surfaces the largest single concentration of intent-vs-reality drift in the audit so far — the predictor lifecycle as specified in intent (walk-forward backtest + 4-stage entry + leaderboard + retirement) is essentially absent in v1 reality, which ships 1 of 7 predictors with neither harness nor leaderboard nor shadow infrastructure. Phase 1c is likely to recommend either (a) a major Phase 4 buildout or (b) amending intent to reflect a much smaller predictor-lifecycle scope.
