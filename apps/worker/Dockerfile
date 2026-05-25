# Task 126: build context is the monorepo root. The worker needs
# domain + storage (and portfolio for parity with the API image so
# any shared dataclass changes don't break the worker build).

FROM python:3.12-slim

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

CMD ["python", "-m", "portfolio_outlook_worker.main"]
