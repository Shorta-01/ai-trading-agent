#!/usr/bin/env bash
#
# Restore-test for an encrypted PostgreSQL backup (AGENTS.md mandate:
# "a backup is not trusted until restore is tested"). This NEVER touches
# the production database — it restores the backup into a throwaway
# Postgres container, verifies the schema + data are present, then tears
# the container down.
#
# Usage:
#   restore-test.sh [path/to/backup.sql.gz.gpg]
# With no argument it picks the most recent backup in BACKUP_DIR.
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"   # infra/docker

if [[ -f "${COMPOSE_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  . "${COMPOSE_DIR}/.env"
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-ai_trading_agent}"
POSTGRES_USER="${POSTGRES_USER:-ai_trading_agent}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/backups/ai-trading-agent}"
PASS_FILE="${BACKUP_GPG_PASSPHRASE_FILE:-}"
PG_IMAGE="${RESTORE_TEST_PG_IMAGE:-postgres:16.4}"
CONTAINER="ai-trading-agent-restore-test"

if [[ -z "${PASS_FILE}" || ! -r "${PASS_FILE}" ]]; then
  echo "ERROR: BACKUP_GPG_PASSPHRASE_FILE must point to a readable passphrase file." >&2
  exit 1
fi

backup_file="${1:-}"
if [[ -z "${backup_file}" ]]; then
  backup_file="$(ls -1t "${BACKUP_DIR}"/ai-trading-agent-*.sql.gz.gpg 2>/dev/null | head -1 || true)"
fi
if [[ -z "${backup_file}" || ! -f "${backup_file}" ]]; then
  echo "ERROR: no backup file found (looked in ${BACKUP_DIR})." >&2
  exit 1
fi
echo "Restore-testing: ${backup_file}"

docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true
docker run -d --name "${CONTAINER}" \
  -e POSTGRES_PASSWORD=restore-test-throwaway \
  -e POSTGRES_USER="${POSTGRES_USER}" \
  -e POSTGRES_DB="${POSTGRES_DB}" \
  "${PG_IMAGE}" >/dev/null
trap 'docker rm -f "${CONTAINER}" >/dev/null 2>&1 || true' EXIT

echo -n "Waiting for throwaway Postgres"
for _ in $(seq 1 30); do
  if docker exec "${CONTAINER}" pg_isready -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null 2>&1; then
    echo " ready."
    break
  fi
  echo -n "."
  sleep 1
done

echo "Decrypting + restoring…"
gpg --batch --yes --decrypt --passphrase-file "${PASS_FILE}" "${backup_file}" \
  | gunzip \
  | docker exec -i "${CONTAINER}" \
      psql -v ON_ERROR_STOP=1 -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" >/dev/null

q() {
  docker exec "${CONTAINER}" psql -tAX -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" -c "$1"
}

alembic_ver="$(q "SELECT version_num FROM alembic_version" 2>/dev/null || true)"
table_count="$(q "SELECT count(*) FROM information_schema.tables WHERE table_schema='public'" 2>/dev/null || echo 0)"

if [[ -z "${alembic_ver}" ]]; then
  echo "FAIL: alembic_version is empty — the dump did not restore a migrated schema." >&2
  exit 1
fi
if [[ "${table_count}" -lt 1 ]]; then
  echo "FAIL: no public tables after restore." >&2
  exit 1
fi

echo "PASS: restored to alembic revision '${alembic_ver}' with ${table_count} public tables."
echo "This backup is now RESTORE-VERIFIED (trusted)."
