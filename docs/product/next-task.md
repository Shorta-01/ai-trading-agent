# Next Recommended Task

## Task 65: Add prompt-injection runtime scan contract wiring for research sources

### Why this is next

- Task 64 delivers deterministic classification foundation, but sources remain blocked.
- The next required safety gate is prompt-injection runtime scan status flow.
- This keeps the Onderzoeksbibliotheek safe without AI analysis or suggestion runtime.
- It also preserves the probabilistic outlook rule: no source can influence forecasts or suggestions until all gates exist.

### Scope summary (kort)

- Add runtime contract wiring for prompt-injection scan results per source.
- Persist scan status and blocker reasons auditable.
- Keep the hard gate active: scanned sources remain blocked for suggestions until credibility, evidence, freshness and risk gates exist.
- Add simple Dutch status/help text where the API or UI exposes status.
- Do not add AI advice, suggestion engine behavior, IBKR actions or orders.

### Forecasting doctrine lock

- Future quant and suggestion work must follow `docs/product/probabilistic-asset-outlook-doctrine.md`.
- Forecasts are probability/range outputs, not exact price predictions.
- Python/model code calculates. AI explains.
- Forecasts are not orders and not IBKR actions.

### Alternative if team skips prompt-injection scan

- Add source credibility runtime foundation before any evidence/suggestion work.
