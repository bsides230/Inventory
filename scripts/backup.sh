#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/app/backups}"
APP_DIR="${APP_DIR:-/app}"
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-14}"
TIMESTAMP="$(date -u +"%Y%m%dT%H%M%SZ")"
TARGET_DIR="${BACKUP_DIR}/${TIMESTAMP}"

mkdir -p "${TARGET_DIR}"

for dir in config data drafts orders ipc logs; do
  if [[ -d "${APP_DIR}/${dir}" ]]; then
    tar -czf "${TARGET_DIR}/${dir}.tar.gz" -C "${APP_DIR}/${dir}" .
  fi
done

# create checksums
cd "${TARGET_DIR}"
shopt -s nullglob
tar_files=(*.tar.gz)
if [ ${#tar_files[@]} -gt 0 ]; then
  sha256sum "${tar_files[@]}" > checksums.txt
fi
shopt -u nullglob

find "${BACKUP_DIR}" -mindepth 1 -maxdepth 1 -type d -mtime +"${RETENTION_DAYS}" -exec rm -rf {} +

echo "backup completed: ${TARGET_DIR}"
