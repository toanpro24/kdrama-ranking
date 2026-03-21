#!/bin/bash
echo "============================================"
echo "  K-Drama Actress Ranking - Project Launcher"
echo "============================================"
echo

# Check for Python
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "[ERROR] Python is not installed."
    echo "        Download it from https://www.python.org/downloads/"
    exit 1
fi
PYTHON=$(command -v python3 || command -v python)

# Check for Node
if ! command -v node &> /dev/null; then
    echo "[ERROR] Node.js is not installed."
    echo "        Download it from https://nodejs.org/"
    exit 1
fi

# Check for MongoDB
if ! command -v mongod &> /dev/null; then
    echo "[WARNING] mongod not found in PATH."
    echo "          Make sure MongoDB is running on localhost:27017"
    echo
fi

DIR="$(cd "$(dirname "$0")" && pwd)"

# Install backend dependencies
echo "[1/3] Installing Python dependencies..."
cd "$DIR/backend"
$PYTHON -m pip install -r requirements.txt --quiet
echo "      Done."
echo

# Install frontend dependencies
echo "[2/3] Installing frontend dependencies..."
cd "$DIR/frontend"
if [ ! -d "node_modules" ]; then
    npm install --silent
fi
echo "      Done."
echo

# Launch servers
echo "[3/3] Starting servers..."
echo
echo "  Backend  : http://localhost:8000"
echo "  Frontend : http://localhost:5173"
echo "  API Docs : http://localhost:8000/docs"
echo
echo "  Press Ctrl+C to stop."
echo "============================================"

# Start backend in background
cd "$DIR/backend"
$PYTHON -m uvicorn main:app --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 3

# Start frontend
cd "$DIR/frontend"
npm run dev &
FRONTEND_PID=$!

# Open browser
sleep 3
if command -v open &> /dev/null; then
    open http://localhost:5173
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
fi

# Cleanup on Ctrl+C
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null; exit" INT
wait
