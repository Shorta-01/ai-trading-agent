"""Export the FastAPI OpenAPI schema to a JSON file.

This snapshot is the single source of truth for the frontend's generated
TypeScript types (``apps/web/lib/api-types.ts``). Run ``make gen-api-types``
from the repo root to refresh both the snapshot and the types in one step.

No server or database is needed — ``app.openapi()`` only introspects the
registered routes.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from portfolio_outlook_api.main import app


def main() -> None:
    out = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / "openapi.json"
    )
    schema = app.openapi()
    out.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"Wrote {out} ({len(schema.get('paths', {}))} paths)")


if __name__ == "__main__":
    main()
