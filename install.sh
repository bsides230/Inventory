#!/bin/bash
set -e

echo "======================================================="
echo "Falcone's Pizza Inventory - macOS/Linux Installer"
echo "======================================================="

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Docker is not installed."
    OS="$(uname -s)"

    if [ "$OS" = "Linux" ]; then
        echo "Attempting to install Docker for Linux..."
        # Official convenience script for Linux
        curl -fsSL https://get.docker.com -o get-docker.sh
        sudo sh get-docker.sh
        rm get-docker.sh

        # Give user permission to use docker without sudo if possible
        if ! groups | grep -q docker; then
            echo "Adding current user to the 'docker' group..."
            sudo usermod -aG docker "$USER"
            echo "You may need to log out and log back in for group changes to take effect."
        fi
    elif [ "$OS" = "Darwin" ]; then
        echo "Please install Docker Desktop for Mac."
        echo "Opening Docker download page..."
        open https://www.docker.com/products/docker-desktop/
        echo "Once installed and running, run this script again or run start.sh."
        exit 1
    else
        echo "Unsupported OS: $OS"
        exit 1
    fi
fi

# Check if docker daemon is running
if ! docker info &> /dev/null; then
    echo "Docker is installed but the daemon is not running. Please start Docker."
    exit 1
fi

echo "Building and starting the application..."
docker compose up -d --build

echo "======================================================="
echo "Application successfully installed and started!"
echo "You can access it at http://localhost"
echo "======================================================="
