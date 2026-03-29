#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
ORDERS_DIR="${ORDERS_DIR:-/app/orders}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
TARGET_DIR="${BACKUP_DIR}/${TIMESTAMP}"

mkdir -p "${TARGET_DIR}"

if [[ -d "${ORDERS_DIR}" ]]; then
  tar -czf "${TARGET_DIR}/orders.tar.gz" -C "${ORDERS_DIR}" .
fi

find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime +"${RETENTION_DAYS}" -exec rm -rf {} +

echo "backup completed: ${TARGET_DIR}"
