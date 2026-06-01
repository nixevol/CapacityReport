@echo off
setlocal
title CapacityReport Debug

cd /d "%~dp0"

set PYTHON_EXE=.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    echo [ERROR] Python virtual environment not found: %PYTHON_EXE%
    echo [HINT] Run this command in the project root first: uv venv
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import fastapi, uvicorn, pandas, openpyxl, pymysql, chardet" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing or repairing Python dependencies...
    uv pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install Python dependencies.
        pause
        exit /b 1
    )
)

where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm not found. Install Node.js first.
    pause
    exit /b 1
)

pushd frontend
if not exist "node_modules" (
    echo [INFO] Installing frontend dependencies...
    call npm ci
    if errorlevel 1 (
        echo [ERROR] Failed to install frontend dependencies.
        popd
        pause
        exit /b 1
    )
)
popd

echo ========================================
echo   CapacityReport - debug mode
echo ========================================
echo [INFO] Backend:  http://127.0.0.1:9081
echo [INFO] Frontend: http://127.0.0.1:5173
echo [INFO] Close both debug windows to stop.
echo.

start "CapacityReport Backend" cmd /k ""%PYTHON_EXE%" -m app.main --host 127.0.0.1 --port 9081"
start "CapacityReport Frontend" cmd /k "pushd "%~dp0frontend" && npm run dev -- --host 127.0.0.1 --port 5173"

echo [OK] Debug services are starting.
pause
