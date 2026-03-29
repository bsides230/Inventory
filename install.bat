@echo off
echo =======================================================
echo Falcone's Pizza Inventory - Windows Installer
echo =======================================================

echo Checking for Docker installation...
docker --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Docker is not installed.
    echo Opening Docker Desktop download page...
    start https://www.docker.com/products/docker-desktop/
    echo Please install Docker Desktop and restart your computer if necessary.
    echo Once Docker is installed and running, re-run this script or run start.bat.
    pause
    exit /b 1
)

echo Docker is installed. Checking if Docker daemon is running...
docker info >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Docker daemon is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Building and starting the application...
docker compose up -d --build
IF %ERRORLEVEL% NEQ 0 (
    echo Error starting the application. Please check the logs above.
    pause
    exit /b 1
)

echo =======================================================
echo Application successfully installed and started!
echo You can access it at http://localhost
echo =======================================================
pause
