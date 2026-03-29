#!/bin/bash
set -e

echo "======================================================="
echo "Starting Falcone's Pizza Inventory"
echo "======================================================="

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    echo "Docker is installed but the daemon is not running. Please start Docker."
    exit 1
fi

echo "Starting the application containers..."
docker compose up -d

echo "======================================================="
echo "Application started successfully!"
echo "Access the application at http://localhost"
echo "======================================================="
