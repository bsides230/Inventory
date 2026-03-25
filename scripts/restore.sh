#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_timestamp_dir>"
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
ORDERS_DIR="${ORDERS_DIR:-/app/orders}"
SOURCE_DIR="${BACKUP_DIR}/$1"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Backup directory does not exist: ${SOURCE_DIR}"
  exit 1
fi

if [[ -f "${SOURCE_DIR}/orders.tar.gz" ]]; then
  mkdir -p "${ORDERS_DIR}"
  tar -xzf "${SOURCE_DIR}/orders.tar.gz" -C "${ORDERS_DIR}"
fi

if [[ -f "${SOURCE_DIR}/postgres_data.tar.gz" ]]; then
  echo "Postgres data archive found at ${SOURCE_DIR}/postgres_data.tar.gz"
  echo "Restore into postgres_data volume with the DB service stopped."
fi

echo "restore completed from: ${SOURCE_DIR}"
