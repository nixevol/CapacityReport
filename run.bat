@echo off
chcp 65001 >nul
title CapacityReport v2.0.1 [自动重启模式]

echo ========================================
echo   CapacityReport - 容量报表处理程序
echo   自动重启模式
echo ========================================
echo.

cd /d "%~dp0"

:: 检查 Python 环境
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到 Python，请先安装 Python 3.8+
    pause
    exit /b 1
)

:: 检查依赖
pip show fastapi >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖...
    pip install -r requirements.txt
)

:loop
echo.
echo [%date% %time%] 启动服务...
echo [启动] 服务地址: http://localhost:9081
echo [提示] 关闭此窗口可完全停止服务
echo.

python -m app.main

echo.
echo [%date% %time%] 服务已停止，3秒后自动重启...
timeout /t 3 /nobreak >nul
goto loop
