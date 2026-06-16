# Task 126: build context is the monorepo root. The worker needs
# domain + storage (and portfolio for parity with the API image so
# any shared dataclass changes don't break the worker build).

FROM python:3.12-slim

# §CB.3 audit-correctie 2026-06-16: non-root runtime user.
RUN groupadd --system --gid 1000 appgroup \
    && useradd --system --uid 1000 --gid appgroup --create-home appuser

WORKDIR /app

COPY packages/domain ./packages/domain
COPY packages/storage ./packages/storage
COPY packages/portfolio ./packages/portfolio
RUN pip install --no-cache-dir \
    -e ./packages/domain \
    -e ./packages/storage \
    -e ./packages/portfolio

COPY apps/worker/pyproject.toml ./apps/worker/pyproject.toml
COPY apps/worker/src ./apps/worker/src
RUN pip install --no-cache-dir ./apps/worker

RUN chown -R appuser:appgroup /app
USER appuser

CMD ["python", "-m", "portfolio_outlook_worker.main"]
