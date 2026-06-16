# Task 126: build context is the monorepo root so the API image can
# install the workspace packages editable. `docker compose` is wired
# to pass the repo root as context — see infra/docker/docker-compose.yml.

FROM python:3.12-slim

# §CB.3 audit-correctie 2026-06-16: non-root runtime user. Containers
# die als root draaien zijn een onnodig veiligheidsrisico bij een
# eventuele code-execution exploit; een dedicated user met geen sudo
# rechten beperkt de blast-radius. UID 1000 is gangbaar zodat
# bind-mounted volumes leesbaar blijven voor host-side tooling.
RUN groupadd --system --gid 1000 appgroup \
    && useradd --system --uid 1000 --gid appgroup --create-home appuser

WORKDIR /app

# Workspace packages first so editable installs resolve against the
# real source trees the API depends on.
COPY packages/domain ./packages/domain
COPY packages/storage ./packages/storage
COPY packages/portfolio ./packages/portfolio
RUN pip install --no-cache-dir \
    -e ./packages/domain \
    -e ./packages/storage \
    -e ./packages/portfolio

# Then the API itself.
COPY apps/api/pyproject.toml ./apps/api/pyproject.toml
COPY apps/api/src ./apps/api/src
RUN pip install --no-cache-dir ./apps/api

# Geef de runtime user eigenaarschap over /app zodat editable installs
# en eventuele log/temp files niet als root worden geschreven.
RUN chown -R appuser:appgroup /app
USER appuser

EXPOSE 8000
CMD ["uvicorn", "portfolio_outlook_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
