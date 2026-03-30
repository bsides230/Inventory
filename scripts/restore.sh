#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <backup_timestamp_dir>"
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
APP_DIR="${APP_DIR:-/app}"
SOURCE_DIR="${BACKUP_DIR}/$1"

if [[ ! -d "${SOURCE_DIR}" ]]; then
  echo "Backup directory does not exist: ${SOURCE_DIR}"
  exit 1
fi

# verify checksums
cd "${SOURCE_DIR}"
if [[ -f "checksums.txt" ]]; then
  if ! sha256sum -c checksums.txt; then
    echo "Checksum validation failed!"
    exit 1
  fi
  echo "Checksum validation passed."
fi

for dir in config data drafts orders ipc logs; do
  if [[ -f "${SOURCE_DIR}/${dir}.tar.gz" ]]; then
    echo "Restoring ${dir}..."
    mkdir -p "${APP_DIR}/${dir}"
    tar -xzf "${SOURCE_DIR}/${dir}.tar.gz" -C "${APP_DIR}/${dir}"
  fi
done

echo "restore completed from: ${SOURCE_DIR}"
