@echo off
title K-Drama Actress Ranking - Launcher
echo ============================================
echo   K-Drama Actress Ranking - Project Launcher
echo ============================================
echo.

:: Check for Python
where python >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download it from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Check for Node
where node >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] Node.js is not installed or not in PATH.
    echo         Download it from https://nodejs.org/
    pause
    exit /b 1
)

:: Check for MongoDB
where mongod >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARNING] mongod not found in PATH.
    echo          Make sure MongoDB is running on localhost:27017
    echo.
)

:: Install backend dependencies
echo [1/3] Installing Python dependencies...
cd /d "%~dp0backend"
pip install -r requirements.txt --quiet
if %errorlevel% neq 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b 1
)
echo       Done.
echo.

:: Install frontend dependencies
echo [2/3] Installing frontend dependencies...
cd /d "%~dp0frontend"
if not exist node_modules (
    npm install --silent
    if %errorlevel% neq 0 (
        echo [ERROR] Failed to install frontend dependencies.
        pause
        exit /b 1
    )
)
echo       Done.
echo.

:: Launch backend and frontend
echo [3/3] Starting servers...
echo.
echo   Backend  : http://localhost:8000
echo   Frontend : http://localhost:5173
echo   API Docs : http://localhost:8000/docs
echo.
echo   Press Ctrl+C in each window to stop.
echo ============================================

:: Start backend in a new terminal
start "K-Drama Backend" cmd /k "cd /d %~dp0backend && python -m uvicorn main:app --reload"

:: Wait a moment for the backend to start
timeout /t 3 /nobreak >nul

:: Start frontend in a new terminal
start "K-Drama Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

:: Open browser after a short delay
timeout /t 4 /nobreak >nul
start http://localhost:5173

echo Servers launched. You can close this window.
