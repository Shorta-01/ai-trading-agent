# Hourly Decision Refresh — Intent vs Reality

**Scope.** Functionality-level reality doc clarifying what the "hourly decision refresh" feature actually does. **Short answer**: nothing substantive. T-033 `system-hourly-delta-runs.md` already documented the gap in depth; T-011b closes the functional-review-additions ledger by recording the canonical filename and pointing at T-033 + T-046 for the full picture.

**Carry-forward task** from the 2026-05-26 functional review. The review flagged that the audit needed a doc at this specific path to address "how does the system keep the action list current between 07:00 evaluations?". The answer turns out to be: it doesn't.

## 1. Intent

Per queue.md T-011b spec: **"Documents the lighter hourly run that keeps the action list current between 07:00 evaluations."**

The expected functionality: between 07:00 (`morning_briefing`) and the next day's 07:00, the system should periodically re-evaluate predictions, re-compose Decision Packages where relevant, and surface fresh action drafts to the user. The cron is in place (`hour="7-21"` per `apps/worker/src/portfolio_outlook_worker/scheduler.py:151-158`); the implied behavior is intra-day refresh.

## 2. Reality — per T-033

T-033 §3 grep-proved: **all 4 sub-step gates in the worker orchestrator EXCLUDE `run_type="hourly_delta"`**:

| Gate | File:line | Condition | Behavior at hourly_delta |
|------|-----------|-----------|--------------------------|
| Market-data | `orchestrator.py:321` | `run_type in ("pre_briefing", "morning_briefing")` | SKIPS |
| Forecasting | `orchestrator.py:337` | `run_type == "morning_briefing"` | SKIPS |
| DP composition | `orchestrator.py:358` | `run_type == "morning_briefing"` | SKIPS |
| Calibration | `orchestrator.py:377` | `run_type == "pre_briefing"` | SKIPS |

The hourly_delta tick fires 14 times daily (08:00 through 21:00 — the 07:00 fire is relabelled to `morning_briefing` per T-032 §2's `_relabel_morning_briefing` clever) and **does no substantive work**. Per T-033 §4:

- Acquires the single-flight lock.
- Runs connectivity probe (skips on disconnect).
- Runs cold-start detection (the 2 SQL COUNT queries — same 2 queries 16× per day per account).
- Optionally fires the seed_runner if the account flipped to `cold_start` mid-day (T-012 cross-reference).
- Writes an empty-payload `worker_run_audit` row.

That's the full list. **The intended "lighter hourly run that keeps the action list current" does not exist in the codebase.**

## 3. The intent-vs-reality gap

T-033 §6 verdicted this as the dominant finding for the hourly_delta workflow: **name-vs-behavior mismatch**. The name "hourly delta" suggests intra-day data refresh + delta computation; reality is 14 essentially-empty fires per day.

Reasonable operator reading the codebase + the cron + the `RunType = Literal["pre_briefing", "morning_briefing", "hourly_delta"]` would assume:
- Fresh market data fetched hourly. **It isn't** (T-033 §3.1 — comment explicit: "Hourly delta fires never re-fetch — EOD prices don't change intraday").
- Fresh forecasts computed against new data. **They aren't** (T-033 §3.2).
- Fresh DPs against fresh forecasts. **They aren't** (T-033 §3.3).
- The dashboard updates throughout the day. **It doesn't** — all output is from 07:00 (T-032).

**Reality**: at 09:00, 10:00, ..., 21:00, the user's dashboard shows the same 07:00 outputs. The only intra-day mutation is via the user's own actions (approve / dismiss / delete drafts per T-026 / T-027 / T-028).

## 4. Why the gap exists per code comments

`apps/worker/src/portfolio_outlook_worker/orchestrator.py:313-316`:

> "Only on normal fires that are also pre_briefing or morning_briefing. Hourly delta fires never re-fetch — EOD prices don't change intraday. The runner returns a small dict folded into the audit row."

The comment is **technically correct** for EODHD EOD data (T-014 §3 confirms EODHD is end-of-day-only). It does NOT address:
- IBKR live mid-prices (which DO change intraday — T-014 §6 documented the live-quote-on-demand path).
- Fresh predictions against newer information (post-market-open news, dividend events, etc.).
- Re-evaluation of safety gates based on changing market conditions.

The architectural rationale (avoid double-running expensive ops, keep batched morning chain deterministic) is defensible. The naming (`hourly_delta` suggesting intra-day delta computation) is misleading.

## 5. Cross-references

| Concern | Where it's documented |
|---------|------------------------|
| Worker orchestrator + scheduler fundamentals | T-007 component reality |
| 14-fire daily cadence | T-033 §1 + §6 (full coverage) |
| Empty `worker_run_audit` payload pattern | T-033 §4.6 |
| `_relabel_morning_briefing` clever | T-032 §2 |
| No live mid-price for sizing | T-017 §4 + T-021 §10.9 (intent §4 mandate) |
| Phase 1c gap: name-vs-behavior mismatch | T-033 §10 + T-046 §11 (monthly rebacktest gap) |

## 6. Phase 1c surface — already-captured gaps

T-011b doesn't add new findings. The gap surface is fully covered:

- **T-033 §10**: 10 findings on the hourly_delta tick (name-vs-behavior mismatch, gate exclusions, cold-start SQL repetition, audit-row accumulation, lock contention).
- **T-046 §11**: monthly scheduled rebacktest absent (Could — the closest analog to "regularly refresh predictor evaluations").
- **T-044 §5**: live mid-price for sizing context (Must — the closest analog to "refresh decision inputs intra-day").

If Phase 2 wants to honor the intent of "hourly decision refresh", the closest implementation paths are:
1. **T-044 §5 (live mid-price)**: refresh sizing context on user-initiated draft creation rather than batch hourly.
2. **T-046 §11 (monthly rebacktest)**: longer cadence; not intra-day but periodic.
3. **A new Phase 4 work item**: actually implement intra-day delta computation if the intent stays — requires removing the gate exclusions per T-033 §3 + sourcing fresher data (probably IBKR live quotes per T-014 §6).

## 7. Out of scope

- The 14-fire empty-tick pattern is fully T-033's territory.
- Quant/forecasting gaps are T-046's territory.
- User-facing trading-quality features (performance review, live mid-price) are T-044's territory.

## 8. References

- `apps/worker/src/portfolio_outlook_worker/scheduler.py:151-158` (the cron that fires 14× daily without producing decisions)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:178` (`_relabel_morning_briefing` — only hour=7 becomes morning_briefing)
- `apps/worker/src/portfolio_outlook_worker/orchestrator.py:321, :337, :358, :377` (the 4 sub-step gates that exclude hourly_delta)
- T-007 `worker-orchestration-and-scheduling.md`
- T-014 `market-data-pipeline.md` §3 (EODHD EOD-only) + §6 (IBKR live mid available but unused)
- T-031 `system-morning-pre-briefing-06-00.md` (06:00 sibling)
- T-032 `system-morning-briefing-07-00.md` (07:00 sibling; relabel)
- **T-033 `system-hourly-delta-runs.md`** (full coverage of the hourly_delta tick)
- T-044 `01-missing-features.md` §5 (live mid-price for sizing — closest user-facing gap)
- T-046 `03-quant-and-forecasting-gaps.md` §11 (monthly rebacktest — closest cadence gap)
