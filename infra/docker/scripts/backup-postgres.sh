#!/usr/bin/env bash
#
# Encrypted PostgreSQL backup for the AI Trading Agent home deployment
# (Raspberry Pi 5 + Docker Compose, per docs/deployment.md).
#
# Dumps the compose Postgres, gzip-compresses, AES256-encrypts with GPG,
# writes a timestamped file to an off-Pi backup directory, and prunes old
# backups. Encryption is mandatory — the script refuses to run without a
# passphrase. A backup is only considered TRUSTED after restore-test.sh
# passes against it (AGENTS.md mandate: "a backup is not trusted until
# restore is tested").
#
# Intended to run from host cron, e.g. daily at 02:00:
#   0 2 * * *  /path/to/repo/infra/docker/scripts/backup-postgres.sh >> /var/log/ai-trading-backup.log 2>&1
#
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"   # infra/docker
COMPOSE_FILE="${COMPOSE_DIR}/docker-compose.yml"

# Load local env (POSTGRES_*, BACKUP_*) if present.
if [[ -f "${COMPOSE_DIR}/.env" ]]; then
  set -a
  # shellcheck disable=SC1091
  . "${COMPOSE_DIR}/.env"
  set +a
fi

POSTGRES_DB="${POSTGRES_DB:-ai_trading_agent}"
POSTGRES_USER="${POSTGRES_USER:-ai_trading_agent}"
BACKUP_DIR="${BACKUP_DIR:-/mnt/backups/ai-trading-agent}"
BACKUP_RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
PASS_FILE="${BACKUP_GPG_PASSPHRASE_FILE:-}"

if [[ -z "${PASS_FILE}" || ! -r "${PASS_FILE}" ]]; then
  echo "ERROR: BACKUP_GPG_PASSPHRASE_FILE must point to a readable passphrase file." >&2
  echo "       Backups must be encrypted (docs/deployment.md). Aborting." >&2
  exit 1
fi
command -v gpg  >/dev/null 2>&1 || { echo "ERROR: gpg not installed."  >&2; exit 1; }
command -v gzip >/dev/null 2>&1 || { echo "ERROR: gzip not installed." >&2; exit 1; }

mkdir -p "${BACKUP_DIR}"
ts="$(date -u +%Y%m%d-%H%M%SZ)"
out="${BACKUP_DIR}/ai-trading-agent-${ts}.sql.gz.gpg"
# Temp file on the same filesystem so the final mv is atomic.
tmp="$(mktemp "${BACKUP_DIR}/.backup.XXXXXX")"
trap 'rm -f "${tmp}"' EXIT

echo "Dumping database '${POSTGRES_DB}' → ${out}"
docker compose -f "${COMPOSE_FILE}" exec -T postgres \
  pg_dump --clean --if-exists -U "${POSTGRES_USER}" -d "${POSTGRES_DB}" \
  | gzip -9 \
  | gpg --batch --yes --symmetric --cipher-algo AES256 \
        --passphrase-file "${PASS_FILE}" -o "${tmp}"

mv "${tmp}" "${out}"
trap - EXIT
chmod 600 "${out}"

echo "OK: wrote ${out} ($(du -h "${out}" | cut -f1))"

# Prune encrypted backups older than the retention window.
find "${BACKUP_DIR}" -name 'ai-trading-agent-*.sql.gz.gpg' -type f \
  -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete \
  | sed 's/^/Pruned: /' || true
echo "Done. Remember: run restore-test.sh to mark this backup TRUSTED."
