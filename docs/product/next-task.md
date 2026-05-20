# Next Recommended Task

## Task 64: Add deterministic document classification contracts/runtime foundation

### Why this is next

- Task 63 is merged: the Onderzoeksbibliotheek UI can now start deterministic TXT/MD/CSV extraction and show extracted-text status/metadata.
- The next safe research-library step is deterministic document classification.
- Classification prepares sources for later credibility, prompt-injection, evidence and asset-linking gates.
- This remains foundation work only: no AI analysis, no suggestion runtime, no IBKR runtime and no order/action creation.

### Scope summary (kort)

- Add typed deterministic classification contracts for research sources/extracted text.
- Add conservative classification categories such as annual report, quarterly report, investor presentation, ETF factsheet, news article, broker report, user note, market data export and unknown.
- Keep all classified sources blocked for suggestions until future validation gates exist.
- Update planning docs so Task 63 is no longer shown as active.

### Forecasting doctrine lock

- Future quant and suggestion work must follow `docs/product/probabilistic-asset-outlook-doctrine.md`.
- The system must calculate probability/range-based asset outlooks, not fake exact future prices.
- Python calculates probabilities, ranges and risk. AI explains and interprets evidence.
- Forecasts are not orders and not IBKR actions.

### Alternative if team skips classification

- Add asset-master and market-data foundation planning docs before starting forecast runtime.
