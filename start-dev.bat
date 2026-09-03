@echo off
echo ===================================================
echo Starting SSB Document Screening System (Dev Mode)
echo ===================================================

echo [1/2] Launching FastAPI Backend on http://localhost:8000 ...
start "SSB-Backend" cmd /k "cd backend && ..\venv\Scripts\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

echo [2/2] Launching Frontend on http://localhost:5173 ...
start "SSB-Frontend" cmd /k "cd frontend && npm run dev"

echo.
echo ===================================================
echo Both services are starting in separate windows:
echo - Backend API:  http://localhost:8000
echo - Swagger Docs: http://localhost:8000/docs
echo - Frontend UI:  http://localhost:5173
echo.
echo To terminate both servers, run: stop-dev.bat
echo ===================================================
