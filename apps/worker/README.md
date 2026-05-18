# Worker (placeholder)

> Waarschuwing: deze worker is alleen een technische skeleton. Geen schedulerjobs, geen marktdata, geen brokercalls, geen AI-calls.

## Lokaal starten

```bash
cd apps/worker
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
python src/portfolio_outlook_worker/main.py
```

## Tests en checks

```bash
cd apps/worker
pytest
ruff check .
mypy src
```
