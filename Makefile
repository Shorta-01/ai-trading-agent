.PHONY: test lint typecheck web-build gen-api-types

test:
	cd apps/api && pytest
	cd apps/worker && pytest

# Refresh the OpenAPI snapshot + the frontend's generated TypeScript types.
# Run after changing any API response model so the two stay in sync.
gen-api-types:
	cd apps/api && python scripts/export_openapi.py
	cd apps/web && npm run gen:api-types

lint:
	cd apps/api && ruff check .
	cd apps/worker && ruff check .
	cd apps/web && npm run lint

typecheck:
	cd apps/api && mypy src
	cd apps/worker && mypy src

web-build:
	cd apps/web && npm run build
