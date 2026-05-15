@echo off
chcp 65001 >nul
title CapacityReport v2.0.2

echo ========================================
echo   CapacityReport - 容量报表处理程序
echo ========================================
echo.

cd /d "%~dp0"

set PYTHON_EXE=.venv\Scripts\python.exe
if not exist "%PYTHON_EXE%" (
    echo [错误] 未找到 uv 创建的虚拟环境: %PYTHON_EXE%
    echo [提示] 请先在项目根目录执行: uv venv
    pause
    exit /b 1
)

"%PYTHON_EXE%" -c "import fastapi, uvicorn, pandas, openpyxl, pymysql, sqlalchemy, chardet" >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装或补齐 Python 依赖...
    uv pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] Python 依赖安装失败
        pause
        exit /b 1
    )
)

if not exist "frontend\dist\index.html" (
    echo [提示] 前端构建产物不存在，请先执行:
    echo        cd frontend
    echo        npm install
    echo        npm run build
    pause
    exit /b 1
)

:loop
echo.
echo [%date% %time%] 启动服务...
echo [启动] 服务地址: http://localhost:9081
echo [提示] 关闭此窗口即可停止服务
echo.

"%PYTHON_EXE%" -m app.main

echo.
echo [%date% %time%] 服务已停止，3 秒后自动重启...
timeout /t 3 /nobreak >nul
goto loop
