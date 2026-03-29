@echo off
echo =======================================================
echo Starting Falcone's Pizza Inventory
echo =======================================================

echo Checking for Docker daemon...
docker info >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Docker daemon is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

echo Starting the application containers...
docker compose up -d
IF %ERRORLEVEL% NEQ 0 (
    echo Error starting the application.
    pause
    exit /b 1
)

echo =======================================================
echo Application started successfully!
echo Access the application at http://localhost
echo =======================================================
pause
