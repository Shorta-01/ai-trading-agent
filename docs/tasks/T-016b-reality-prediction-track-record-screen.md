```yaml
id: T-016b
title: Write reality doc for prediction-track-record-screen functionality
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/prediction-diary-and-calibration.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url:
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/functionality/prediction-track-record-screen.md` does not exist (verified). Investigated whether the screen exists:
  - Frontend pages: `apps/web/app/` has 12 routed pages; **none is a prediction-track-record screen** (grep for `track` / `diary` / `prediction` in `apps/web/app` + `apps/web/components` returns zero matches).
  - Backend: `GET /prediction-diary` (`status_routes.py:2568`) + `POST /prediction-diary/evaluate` (`:2476`) + `SqlAlchemyPredictionDiaryRepository` exist.
  - Frontend consumers of `/prediction-diary`: **zero** (grep returns no matches).
  - Intent: `predictor-lifecycle.md:56` references the screen as the leaderboard's host; `prediction-diary-and-calibration.md` covers the architecture not the screen spec.
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the prediction-track-record-screen functionality reality doc.
  - `prediction-track-record-screen.md` — documents that the screen is **absent** (backend `/prediction-diary` data exists; no frontend screen consumes it; intent spec of filters-by-predictor/asset/window + aggregate views + drill-downs unimplemented); the only adjacent surface is `<CalibrationCoverageBadge>` (a badge, not the screen); parallels T-024 §10.7 (leaderboard UI also absent — the screen would HOST the leaderboard per intent).
- **Step 3 (one-line change):** write one functionality-level reality doc documenting the screen's absence + the backend data that exists behind it.
- **Step 4 (measurable):** yes — six acceptance criteria: file exists; screen spec documented (filters + aggregate views + drill-downs per queue.md T-016b); implementation status = absent documented; backend `/prediction-diary` data that exists documented; the screen-hosts-leaderboard relationship (T-024 cross-ref) documented; Phase 1c gap entry framing; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — T-016 calibration deep dive (merged); T-024 leaderboard (merged); T-021b performance review (last functional-review addition).

## Goal

Produce one functionality-level reality doc documenting the prediction-track-record-screen specification + its current implementation status. Per queue.md T-016b: "Documents the screen specification (filters by predictor / asset / window, aggregate views, drill-downs) and current implementation status." The answer: **the screen does not exist** — backend prediction-diary data is present, no frontend screen consumes it. This becomes a Phase 1c missing-feature gap entry.

## Context

`depends_on:` T-008 (frontend pages), T-016 (calibration + prediction diary). T-016 documented the diary backend; T-016b documents the absent frontend screen the functional review specified.

## Touch scope

Create:
- `docs/reality/functionality/prediction-track-record-screen.md`

Read: T-008 + T-016 reality docs + `status_routes.py` diary routes + frontend page inventory + intent.

## Acceptance criteria

- [ ] Output file exists at `docs/reality/functionality/prediction-track-record-screen.md`.
- [ ] Screen spec documented (filters by predictor/asset/window + aggregate views + drill-downs).
- [ ] Implementation status = absent documented (frontend grep proof).
- [ ] Backend `/prediction-diary` data that exists documented.
- [ ] Screen-hosts-leaderboard relationship cited (T-024 §3.5 + §10.7 + T-044 §4).
- [ ] Phase 1c gap entry framing.
- [ ] No source modification.

## Out of scope

- T-016 calibration + diary backend deep dive (merged sibling).
- T-024 leaderboard API + UI gap (merged sibling).
- T-044 leaderboard UI missing-feature entry (merged).
- T-021b performance review screen (last functional-review addition).

## Verification

- File exists.
- Screen spec documented.
- Absence proven via frontend grep.
- Leaderboard-host relationship cited.

## Notes

T-016b is the 4th of 5 functional-review additions. Like T-011b (hourly refresh absent), the answer is "the queried thing doesn't exist". But unlike T-011b, the BACKEND data is fully present — `/prediction-diary` returns deterministically-classified diary entries (T-016). The gap is purely the frontend screen. This pairs with T-024 §10.7 (leaderboard UI absent) + T-044 §4 (leaderboard as a missing feature) — the prediction-track-record screen would host the leaderboard, so both are absent UI surfaces over existing backend data.
