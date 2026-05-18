.PHONY: test lint typecheck web-build

test:
	cd apps/api && pytest
	cd apps/worker && pytest

lint:
	cd apps/api && ruff check .
	cd apps/worker && ruff check .
	cd apps/web && npm run lint

typecheck:
	cd apps/api && mypy src
	cd apps/worker && mypy src

web-build:
	cd apps/web && npm run build
