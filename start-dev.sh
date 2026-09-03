#!/usr/bin/env bash
# ==============================================================================
# SSB Document Screening System — Development Launcher (macOS / Linux)
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "==================================================="
echo "  Starting SSB Document Screening System (Dev Mode)"
echo "==================================================="

# Check for virtual environment
if [ ! -f "$PROJECT_ROOT/venv/bin/python" ]; then
    echo "ERROR: Virtual environment not found at $PROJECT_ROOT/venv."
    echo "Please create it using: python3 -m venv venv && ./venv/bin/pip install -r backend/requirements.txt"
    exit 1
fi

# 1. Launch FastAPI Backend
echo "[1/2] Launching FastAPI Backend on http://localhost:8000 ..."
(
    cd "$PROJECT_ROOT/backend" || exit 1
    exec "$PROJECT_ROOT/venv/bin/uvicorn" app.main:app --host 0.0.0.0 --port 8000 --reload
) > "$PROJECT_ROOT/.backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$PROJECT_ROOT/.backend.pid"

# 2. Launch Vite Frontend
echo "[2/2] Launching Frontend on http://localhost:5173 ..."
(
    cd "$PROJECT_ROOT/frontend" || exit 1
    exec npm run dev
) > "$PROJECT_ROOT/.frontend.log" 2>&1 &
FRONTEND_PID=$!
echo "$FRONTEND_PID" > "$PROJECT_ROOT/.frontend.pid"

echo ""
echo "==================================================="
echo "  Both services are running in the background:"
echo "  - Backend API:    http://localhost:8000"
echo "  - Swagger Docs:   http://localhost:8000/docs"
echo "  - Frontend UI:    http://localhost:5173"
echo "  - Backend Log:    tail -f .backend.log"
echo "  - Frontend Log:   tail -f .frontend.log"
echo ""
echo "  To terminate both servers, run: ./stop-dev.sh"
echo "==================================================="
