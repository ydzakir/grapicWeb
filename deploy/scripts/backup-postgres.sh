#!/usr/bin/env bash
set -eo pipefail

TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="${BACKUP_DIR:-/backups}"
CONTAINER_NAME="${POSTGRES_CONTAINER:-infra_postgres}"
DB_NAME="${POSTGRES_DB:-monitoring_db}"
DB_USER="${POSTGRES_USER:-monitoring_admin}"

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="${BACKUP_DIR}/postgres_backup_${DB_NAME}_${TIMESTAMP}.sql.gz"

echo "[$(date)] Starting PostgreSQL database backup for '${DB_NAME}'..."
docker exec -t "$CONTAINER_NAME" pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$BACKUP_FILE"

echo "[$(date)] Backup completed successfully: ${BACKUP_FILE}"
