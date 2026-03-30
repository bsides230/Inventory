@echo off
echo =======================================================
echo Falcone's Pizza Inventory - Windows Installer
echo =======================================================

echo Checking for Python installation...
python --version >nul 2>&1
IF %ERRORLEVEL% NEQ 0 (
    echo Python is not installed. Please install Python 3.12 or later.
    pause
    exit /b 1
)

echo Installing required Python dependencies...
python -m pip install -r requirements.txt
IF %ERRORLEVEL% NEQ 0 (
    echo Error installing dependencies.
    pause
    exit /b 1
)

echo Starting the application...
call start.bat

echo =======================================================
echo Application successfully installed and started!
echo You can access it at http://localhost
echo =======================================================
pause
