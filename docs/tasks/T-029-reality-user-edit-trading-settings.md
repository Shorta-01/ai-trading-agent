```yaml
id: T-029
title: Write reality doc for user-edit-trading-settings workflow
phase: P1
status: in-progress
source: brainstorm
owner: claude
created: 2026-05-27
intent_ref: docs/intent/_phase-1-charter.md
decision_ref: docs/decisions/0001-phase-1-charter.md
pr_url: https://github.com/Shorta-01/ai-trading-agent/pull/474
```

## Audit (steps 1–5; recorded per `_audit-discipline.md`)

- **Step 1 (read all files in touch scope before editing any of them):** the one target file `docs/reality/workflows/user-edit-trading-settings.md` does not exist (verified). Every code site is already cited in T-006 + T-061 reality docs:
  - T-006 `api-infrastructure-and-ai.md` — settings API surface.
  - T-061 `settings-and-credentials-infrastructure.md` — the 5-category settings inventory; Category 1 (credentials) + Category 2 (trading) + Category 3 (thresholds) + Category 4 (notifications) + Category 5 (on-demand triggers) split.
  - `apps/web/app/instellingen/page.tsx:1-171` (THE Instellingen page — 171 LOC; the only frontend surface for editing settings).
  - `apps/api/src/portfolio_outlook_api/trading_settings.py:1-198` (builder + update handler with full read-modify-write).
  - `apps/api/src/portfolio_outlook_api/status_routes.py:244` (`GET /settings/trading`) + `:410` (`PUT /settings/trading`).
  - `packages/domain/src/portfolio_outlook_domain/settings.py:130-182` (`AllowedUniverseSettings` + `UserStrategySettings` Pydantic models; 11+ fields in the user-strategy alone).
- **Step 2 (one-line per touched file):** the one target file does not exist; it holds the **user-action workflow** narrative for editing trading settings.
  - `user-edit-trading-settings.md` — user-perspective trace: user navigates to `/instellingen` → sees a SINGLE editable field (`user_buffer_eur` cashbuffer) → types a number → clicks "Opslaan" → client-side validates `numeric < 0` → PUT `/settings/trading` with full read-modify-write payload + hard-coded `reason_nl="Cashbuffer voor actiedrafts aangepast."` → server upserts `trading_settings` row → page re-fetches and renders success message. The dominant finding: the domain model defines 11+ user-strategy fields; the UI exposes 1 (Cashbuffer). The page docstring promises "a read-only summary of the other user-strategy settings" — but the page doesn't render one.
- **Step 3 (one-line change):** write one user-action workflow reality doc tracing the cashbuffer edit ritual + surface the 1-of-11 UI gap.
- **Step 4 (measurable):** yes — seven acceptance criteria: file exists; user journey enumerated (4-step narrative); 1-editable-field-of-11 gap surfaced as dominant finding; hard-coded `reason_nl` overrides any user intent documented (intent §4 audit-log mandate); read-modify-write pattern + last-writer-wins risk documented; Category split (T-061) re-confirmed (only Category 2 partial); ≥ 7 Phase 1c findings; no source modification.
- **Step 5 (out-of-scope does not block goal):** confirmed — credentials infrastructure (T-061 — merged sibling, covers API keys + budgets), settings ingest mechanism (T-061 §2).

## Goal

Produce one user-action workflow reality doc narrating the cashbuffer edit ritual from the user's perspective — `/instellingen` arrival → single field input → Opslaan click → server upsert → success message. The dominant finding is the **10-of-11 invisible fields**: the user can change `user_buffer_eur` via the UI, but `portfolio_goal`, `risk_level`, `asset_mix_preference`, `preferred_regions`, `preferred_sectors`, `avoided_sectors`, `max_position_pct`, `min_cash_reserve_pct`, `currency_preference`, `prefer_simple_belgian_tax_admin` are all silently passed through unchanged via read-modify-write. The user has no way to view OR change them in the UI.

## Context

`depends_on:` T-006. T-006 covered the API infrastructure including the settings routes; T-061 (already merged) did the deep settings + credentials inventory. T-029 stitches them at the user-action layer and surfaces the 1-of-11 UI exposure gap.

## Touch scope

Create:
- `docs/reality/workflows/user-edit-trading-settings.md`

Read: T-006 + T-061 reality docs + `/instellingen/page.tsx` + `trading_settings.py` + `settings.py` (domain models).

## Acceptance criteria

- [ ] Output file exists.
- [ ] User journey enumerated (4-step narrative: navigate → enter buffer → save → see success).
- [ ] Single-editable-field documented; full inventory of 11 user-strategy fields cited from `domain/settings.py:142-159`.
- [ ] Read-modify-write pattern documented; `next_user_strategy = {...data.user_strategy, user_buffer_eur}` at `instellingen/page.tsx:62-65`.
- [ ] Hard-coded `reason_nl` documented (`"Cashbuffer voor actiedrafts aangepast."` at `:69`); intent §4 audit-log "audit-logged with the user's reason" gap surfaced.
- [ ] Client-side validation enumerated (`numeric < 0` only at `:54-58`); server-side validators cited from domain.
- [ ] Category split re-confirmed per T-061: only Category 2 partial; Categories 1, 3, 4, 5 absent from UI.
- [ ] ≥ 7 Phase 1c findings on the user-action surface.
- [ ] No source modification.

## Out of scope

- Credentials infrastructure (T-061 — merged sibling; covers Category 1 API keys + budget caps).
- Settings ingest mechanism (T-061 §2 — how `.env` vars flow through Pydantic).
- Reconciliation thresholds (T-020 §10.3 — Category 3 also absent from UI; cross-referenced).
- AI provider budget cap settings (T-023 — Category 1; cross-referenced).
- Speculative classification thresholds (T-022 §10.7 — Category 3; cross-referenced).

## Verification

- File exists.
- `UserStrategySettings` 11-field inventory cited.
- Page's 1-field exposure documented with grep.
- Hard-coded `reason_nl` cited.
- ≥ 7 Phase 1c findings.

## Notes

T-029 is the 5th of 11 Track 1a Reality Workflows. The dominant finding pattern continues from T-027 + T-028: a user-facing surface that LOOKS operational at first glance but exposes only a fraction of the underlying domain model. The page itself is intellectually honest — the docstring (`page.tsx:6-13`) explicitly acknowledges "the only editable field added here is `user_buffer_eur`. Other fields... can be wired through later UI work; the page currently shows the buffer + a read-only summary of the other user-strategy settings." But even the promised "read-only summary" is not rendered. Phase 1c may want to either (a) build out the rest of the editable surface or (b) at minimum render the read-only summary so users can see what they're inheriting from defaults.
