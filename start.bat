@echo off
echo =======================================================
echo Starting Falcone's Pizza Inventory
echo =======================================================

if not exist logs mkdir logs

echo Starting the application processes...

start /B python services\ipc_worker.py > logs\ipc_worker.log 2>&1

python server.py

echo =======================================================
echo Application stopped!
echo =======================================================
pause
