# Anti-Patterns — populated in Phase 1d

## FIND-BANDIT-001 — `assert` used for type-narrowing in production paths (20 occurrences across 8 files)

- **Tool:** `bandit 1.9.4`, test `B101 assert_used`, severity LOW (bandit's rating). Raw output `/tmp/bandit-low-and-up.json` (T-053).
- **Pattern:** every B101 site is a post-validation type-narrowing `assert x is not None` that follows an explicit `if x is None: _raise_*(...)` or framework-raise. The assert exists to satisfy mypy's narrowing in strict mode, not as an invariant guard.

### Inventory (file:line)

| File | Lines | Note |
|---|---|---|
| `apps/api/src/portfolio_outlook_api/action_draft.py` | `:260, :498, :499, :500, :501, :502, :503, :504, :505` | 9 asserts; eight (`:498-505`) narrow user-supplied draft fields after a missing-field guard at `:489-495` |
| `packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py` | `:278, :279, :295, :296` | 4 asserts inside `_sum_positions` / `_sum_cash`; already documented in `docs/reality/components/portfolio-money-and-accounting.md` ("uses bare `assert` for `None` checks inside the summation helpers") |
| `apps/worker/src/portfolio_outlook_worker/ibkr_submission/submission_sweep.py` | 2 lines | sweep-tick null guards |
| `apps/api/src/portfolio_outlook_api/ibkr_submission.py` | 1 line | |
| `apps/api/src/portfolio_outlook_api/predictor_backtest_orchestrator.py` | 1 line | |
| `apps/api/src/portfolio_outlook_api/reconciliation.py` | 1 line | |
| `apps/worker/src/portfolio_outlook_worker/forecasting/asset_universe_resolver.py` | 1 line | |
| `packages/storage/src/ai_trading_agent_storage/sql_repositories.py` | 1 line | |

### Evidence

```python
# apps/api/src/portfolio_outlook_api/action_draft.py:256-262
def _storage_provider() -> StorageConnectionProvider:
    storage = settings.storage
    if not storage.enabled or not storage.database_url:
        _raise_storage_unavailable()
    assert storage.database_url is not None  # _raise_storage_unavailable raises above
    return StorageConnectionProvider(...)
```

```python
# packages/portfolio/src/portfolio_outlook_portfolio/valuation_conversion_totals.py:275-285
for position in positions:
    assert position.native_market_value is not None
    assert position.source_currency is not None
    if position.source_currency == base_currency:
        total += position.native_market_value
        continue
    ...
```

### Why it matters (plain English)

`assert` is removed by `python -O`. In every B101 site here, removal is **safe today** because the prior validation (`_raise_*`, `HTTPException`, or an explicit `if missing: raise`) raises first; the assert only narrows the type for mypy. The risk is **documentation drift**: a future refactor that removes the prior raise without noticing would silently turn the assert into the sole guard, then have that guard vanish under `python -O`. AGENTS.md ("Every decision must be logged") favors an explicit raise even where mypy can be satisfied with `assert`.

### Fix approach

Replace each site with one of:
- `if x is None: raise RuntimeError("invariant violated: ...")` — explicit invariant check; survives `-O`.
- `typing.cast(T, x)` — pure type-narrowing without runtime cost or `-O` sensitivity.

The choice per-site depends on whether the assertion is documenting an internal invariant (use `cast`) or a true post-validation guarantee (use explicit `raise`).

### Complexity / severity

- Complexity: **small**. Each site is a one-line swap; no behaviour change.
- Severity: **low**. No runtime vulnerability today; the surrounding validation already raises. Risk is purely future-refactor-fragility.

### Related findings

None directly; the B110/B112 `try/except/pass(continue)` patterns inventoried in `_dismissed.md` under T-053 are documented boundary catches, not the same family.
