#!/bin/bash
set -e

echo "======================================================="
echo "Starting brand's Pizza Inventory"
echo "======================================================="

# Ensure log directory exists
mkdir -p logs

echo "Starting the application processes..."

# Kill existing processes if any (optional, to avoid port conflicts)
pkill -f "python services/ipc_worker.py" || true
# Kill existing uvicorn server processes for server:app
pkill -f "uvicorn server:app" || true

# Start background worker script
if [ -f "scripts/run_backup_worker.sh" ]; then
    bash scripts/run_backup_worker.sh > logs/backup_worker.log 2>&1 &
fi

# Start IPC worker in background
python3 services/ipc_worker.py > logs/ipc_worker.log 2>&1 &

# Start the main server
python3 server.py

echo "======================================================="
echo "Application stopped!"
echo "======================================================="
