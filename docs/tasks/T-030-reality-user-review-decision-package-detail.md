```yaml
id: T-030
title: Write reality doc for user-review-decision-package-detail workflow
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/475
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/user-review-decision-package-detail.md` does not exist (verified). Every code site is already cited in T-017 + T-023 + T-008 reality docs:
  - T-017 `decision-package-composition.md` — full functionality doc (composer + 5 gates + deterministic Dutch template + SHA-256 hash chain).
  - T-023 `ai-explanation-and-budget.md` — LLM explanation surface (lives separately from DP detail per finding).
  - T-008 `web-components-feature-grids.md` — `<ForecastExplanationPanel>` entry point.
  - `apps/web/app/decision-package/[id]/page.tsx:1-76` (thin client page with `useParams`).
  - `apps/web/components/DecisionPackageDetail.tsx:1-440` (the 7-section view).
  - `apps/web/components/ForecastExplanationPanel.tsx:248` (the SINGLE entry point linking to `/decision-package/[id]`).
  - `apps/api/src/portfolio_outlook_api/decision_package_routes.py` (the GET DP route consumed).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **user-action workflow** narrative for reviewing a Decision Package detail.
  - `user-review-decision-package-detail.md` — user-perspective trace: user on `/volglijst` opens `<ForecastExplanationPanel>` for an asset → clicks the "Decision Package" link → navigates to `/decision-package/{id}` → page does single `getDecisionPackage(id)` fetch → renders 7 locked Dutch sections (Header / Voorspelling / Huidige situatie / Gate-uitkomsten / Bewijsbronnen / Onderbouwing (deterministic template — NOT LLM) / Audit) → optionally "Maak actie" button (only for Kopen / Verminderen / Verkopen labels) → click creates an action draft and navigates to `/ibkr-acties?new={id}`. Distinct from T-017 (which covered composer mechanics) and T-023 (which covered the separately-located LLM explanation surface).
- **Step 3 (one-line change):** write one user-action workflow reality doc tracing the DP review ritual end-to-end.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; 7-section layout enumerated; deterministic-vs-LLM explanation split documented (DP detail uses `deterministic_dutch_explanation`; LLM `explanation_nl` is on `/portefeuille` not here); single entry point (`<ForecastExplanationPanel>`) documented; `ACTIONABLE_LABELS = {Kopen, Verminderen, Verkopen}` gate cited; `audit_trail_hash.slice(0, 12)` truncation + "Toon volledig" toggle cited; 404+503 collapsed to single Dutch fallback noted; ≥ 7 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — DP composition mechanics (T-017 — merged sibling), LLM explanation surface (T-023 — merged sibling; documented separately on /portefeuille), action draft creation flow (T-018 — merged sibling).

## Goal

Produce one user-action workflow reality doc narrating the DP-detail review ritual from the user's perspective — entry via `<ForecastExplanationPanel>` → page load → read through 7 locked Dutch sections → optionally "Maak actie" → navigate to draft. Focus on the user-visible structure of the page, the truncate-with-toggle hash pattern, the asymmetry where the LLM explanation lives elsewhere, and the "Maak actie" label-gate.

## Context

`depends_on:` T-017. T-017 covered the composer (decision package creation); T-030 covers the user's review surface for an existing DP — the read-side counterpart.

## Touch scope

Create:
- `docs/reality/workflows/user-review-decision-package-detail.md`

Read: T-017 + T-023 + T-008 reality docs + DP detail page + DP detail component + forecast explanation panel entry point.

## Acceptance criteria

- [ ] Output file exists.
- [ ] 7-section layout enumerated (Header / Voorspelling / Huidige situatie / Gate-uitkomsten / Bewijsbronnen / Onderbouwing / Audit + optional Actie).
- [ ] Deterministic-vs-LLM explanation split documented — DP detail uses `pkg.deterministic_dutch_explanation` (the worker template per T-017 §6); LLM `explanation_nl` is on `/portefeuille` per T-023 § not on this page.
- [ ] Single entry point documented — `<ForecastExplanationPanel>` at `ForecastExplanationPanel.tsx:248`; no top-nav, no breadcrumb, no dashboard widget link.
- [ ] `ACTIONABLE_LABELS = {Kopen, Verminderen, Verkopen}` cited (`DecisionPackageDetail.tsx:69-73`); Houden / Bekijken get no "Maak actie" button.
- [ ] `audit_trail_hash.slice(0, 12)` truncation + "Toon volledig" toggle cited (`:85, :345-357`); `previous_package_hash` chain visibility documented.
- [ ] 404+503 collapsed to single Dutch fallback noted (`page.tsx:43-47`).
- [ ] ≥ 7 Phase 1c findings.
- [ ] No source modification.

## Out of scope

- DP composer mechanics (T-017 — merged sibling).
- LLM explanation surface (T-023 — merged sibling; lives on /portefeuille).
- Action draft creation flow (T-018 — merged sibling; downstream of the "Maak actie" click).
- 5 composition gates deep dive (T-017 §3 — referenced from the rendered gate-outcomes table).
- Predictor backtest / leaderboard (T-024 — merged sibling).

## Verification

- File exists.
- 7-section layout enumerated.
- LLM-vs-deterministic explanation split surfaced.
- Single entry point documented with grep proof.
- ≥ 7 Phase 1c findings.

## Notes

T-030 is the 6th of 11 Track 1a Reality Workflows. The most surprising finding is the **explanation surface fragmentation**: the DP detail page shows the deterministic template Dutch text (`pkg.deterministic_dutch_explanation`); the LLM-generated explanation (`explanation_nl` from `decision_package_explanations` cache) lives separately on `/portefeuille` per T-023 §6.1. A user reading a DP at `/decision-package/{id}` cannot see the LLM paraphrase. The two surfaces show **different Dutch text for the same DP** with no cross-link. Phase 1c may want to unify them.
