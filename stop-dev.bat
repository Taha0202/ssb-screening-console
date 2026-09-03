@echo off
echo ===================================================
echo Stopping SSB Document Screening System Processes
echo ===================================================

echo Terminating dev processes...
taskkill /FI "WINDOWTITLE eq SSB-Backend*" /T /F 2>nul
taskkill /FI "WINDOWTITLE eq SSB-Frontend*" /T /F 2>nul
taskkill /F /IM uvicorn.exe /T 2>nul
taskkill /F /IM node.exe /T 2>nul

echo All screening workstation development servers stopped cleanly.
echo ===================================================
