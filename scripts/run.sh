#!/usr/bin/env bash
#
# LENS Launcher for Linux and macOS
#
set -e

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "=========================================="
echo "      LENS: AI-Powered File Discovery     "
echo "=========================================="

VENV_PYTHON="$PROJECT_ROOT/venv/bin/python"
if [ ! -f "$VENV_PYTHON" ]; then
    echo "Virtual environment not detected at ./venv. Creating one..."
    python3 -m venv "$PROJECT_ROOT/venv"
    "$VENV_PYTHON" -m pip install --upgrade pip
    "$VENV_PYTHON" -m pip install -r "$PROJECT_ROOT/requirements.txt"
fi

# Verify frontend build
DIST_INDEX="$PROJECT_ROOT/frontend/dist/index.html"
if [ ! -f "$DIST_INDEX" ]; then
    echo "Compiling frontend distribution..."
    cd "$PROJECT_ROOT/frontend"
    npm install
    npm run build
    cd "$PROJECT_ROOT"
fi

echo "Starting LENS Server on http://127.0.0.1:8000..."
echo "Press Ctrl+C to stop."

# Open browser if possible
if command -v xdg-open > /dev/null; then
    (sleep 2 && xdg-open "http://127.0.0.1:8000") &
elif command -v open > /dev/null; then
    (sleep 2 && open "http://127.0.0.1:8000") &
fi

exec "$VENV_PYTHON" -m uvicorn backend.api.app:app --host 127.0.0.1 --port 8000
