@echo off
title CapacityReport v3.0.0

echo ========================================
echo   CapacityReport - report service
echo ========================================
echo.

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

if not exist "frontend\dist\index.html" (
    echo [INFO] Frontend build output not found. Building frontend...
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

    call npm run build
    if errorlevel 1 (
        echo [ERROR] Failed to build frontend.
        popd
        pause
        exit /b 1
    )
    popd
)

:loop
echo.
echo [%date% %time%] Starting service...
echo [INFO] Frontend: http://localhost:9081
echo [INFO] Close this window to stop the service.
echo.

"%PYTHON_EXE%" -m app.main

echo.
echo [%date% %time%] Service stopped. Restarting in 3 seconds...
timeout /t 3 /nobreak >nul
goto loop
