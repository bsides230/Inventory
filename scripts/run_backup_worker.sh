#!/bin/bash
set -e

BACKUP_INTERVAL_SECONDS=${BACKUP_INTERVAL_SECONDS:-3600}

echo "Starting backup worker. Interval: ${BACKUP_INTERVAL_SECONDS} seconds."

while true; do
    ./scripts/backup.sh || true
    sleep $BACKUP_INTERVAL_SECONDS
done
