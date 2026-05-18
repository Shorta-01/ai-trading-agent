# API (FastAPI skeleton)

> Waarschuwing: versie 1 is strikt paper-only. Geen live trading, geen brokerkoppeling en geen echte orders.

## Lokaal starten

```bash
cd apps/api
python -m venv .venv
source .venv/bin/activate
pip install -e .[dev]
uvicorn portfolio_outlook_api.main:app --reload --app-dir src
```

## Tests en checks

```bash
cd apps/api
pytest
ruff check .
mypy src
```
