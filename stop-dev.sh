#!/usr/bin/env bash
# ==============================================================================
# SSB Document Screening System — Development Stopper (macOS / Linux)
# ==============================================================================

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_ROOT" || exit 1

echo "==================================================="
echo "  Stopping SSB Document Screening System Processes"
echo "==================================================="

# 1. Stop backend if PID file exists
if [ -f "$PROJECT_ROOT/.backend.pid" ]; then
    PID=$(cat "$PROJECT_ROOT/.backend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping FastAPI backend (PID: $PID)..."
        kill -TERM "$PID" 2>/dev/null
    fi
    rm -f "$PROJECT_ROOT/.backend.pid"
fi

# 2. Stop frontend if PID file exists
if [ -f "$PROJECT_ROOT/.frontend.pid" ]; then
    PID=$(cat "$PROJECT_ROOT/.frontend.pid")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Stopping Vite frontend (PID: $PID)..."
        kill -TERM "$PID" 2>/dev/null
    fi
    rm -f "$PROJECT_ROOT/.frontend.pid"
fi

# 3. Clean up any remaining uvicorn or vite processes on dev ports (8000, 5173)
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:5173 | xargs kill -9 2>/dev/null || true

echo "All development server processes stopped."
echo "==================================================="
