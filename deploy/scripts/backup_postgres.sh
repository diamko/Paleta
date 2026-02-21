#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="${PROJECT_DIR:-/opt/paleta}"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_DIR/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

if ! command -v pg_dump >/dev/null 2>&1; then
  echo "pg_dump is not installed. Install client package first (postgresql-client)." >&2
  exit 1
fi

if [ -f "$PROJECT_DIR/.env.prod" ]; then
  # shellcheck disable=SC1090
  set -a; . "$PROJECT_DIR/.env.prod"; set +a
fi

if [ -z "${DATABASE_URL:-}" ]; then
  echo "DATABASE_URL is not set. Provide PostgreSQL DSN in .env.prod or environment." >&2
  exit 1
fi

PG_DSN="$DATABASE_URL"
if [[ "$PG_DSN" == postgresql+*://* ]]; then
  PG_DSN="$(printf '%s' "$PG_DSN" | sed -E 's#^postgresql\+[^:]+://#postgresql://#')"
fi

mkdir -p "$BACKUP_DIR"
TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_FILE="$BACKUP_DIR/paleta_pg_${TIMESTAMP}.dump"

pg_dump "$PG_DSN" --format=custom --file="$BACKUP_FILE"
find "$BACKUP_DIR" -type f -name 'paleta_pg_*.dump' -mtime +"$RETENTION_DAYS" -delete

echo "Backup created: $BACKUP_FILE"
