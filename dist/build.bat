@echo off
chcp 65001 >nul
REM CapacityReport 镜像构建和导出脚本 (Windows)
REM 在有外网的 Windows 机器上运行此脚本，生成离线部署包
@REM set http_proxy=http://127.0.0.1:7897
@REM set https_proxy=http://127.0.0.1:7897
setlocal enabledelayedexpansion

set SCRIPT_DIR=%~dp0
set "PROJECT_ROOT=%~dp0..\"
set DIST_DIR=%~dp0
REM 规范化路径（去掉末尾的反斜杠，如果有的话）
if "%PROJECT_ROOT:~-1%"=="\" set "PROJECT_ROOT=%PROJECT_ROOT:~0,-1%"

echo ==========================================
echo CapacityReport 离线部署包构建脚本
echo ==========================================
echo.

REM 清理旧的构建文件
echo 清理旧的构建文件...
if exist "%DIST_DIR%images\capacity-images.tar" (
    del /f /q "%DIST_DIR%images\capacity-images.tar"
    echo   - 已删除旧镜像文件
)
if exist "%DIST_DIR%Configure.json" (
    del /f /q "%DIST_DIR%Configure.json"
    echo   - 已删除旧 Configure.json
)
if exist "%DIST_DIR%ReportScript.sql" (
    del /f /q "%DIST_DIR%ReportScript.sql"
    echo   - 已删除旧 ReportScript.sql
)
if exist "%DIST_DIR%mysql\conf.d\custom.cnf" (
    del /f /q "%DIST_DIR%mysql\conf.d\custom.cnf"
    echo   - 已删除旧 mysql\conf.d\custom.cnf
)
if exist "%DIST_DIR%mysql\init\01-init-db.sql" (
    del /f /q "%DIST_DIR%mysql\init\01-init-db.sql"
    echo   - 已删除旧 mysql\init\01-init-db.sql
)
echo 清理完成
echo.

REM 检查 Docker 是否安装
where docker >nul 2>&1
if %errorlevel% neq 0 (
    echo 错误: 未检测到 Docker，请先安装 Docker Desktop
    exit /b 1
)

REM 检查 Docker Compose 是否安装
docker compose version >nul 2>&1
if %errorlevel% neq 0 (
    docker-compose version >nul 2>&1
    if %errorlevel% neq 0 (
        echo 错误: 未检测到 Docker Compose，请先安装 Docker Compose
        exit /b 1
    )
)

echo 步骤 1: 拉取基础镜像...
REM 检查 Dockerfile 中的 Python 版本
set PYTHON_TAG=
for /f "tokens=2 delims=:" %%a in ('findstr /R "^FROM python:" "!PROJECT_ROOT!\Dockerfile"') do (
    set "PYTHON_TAG=%%a"
    goto :found_python
)
:found_python
if defined PYTHON_TAG (
    REM 去掉可能的空格
    for /f "tokens=1 delims= " %%b in ("!PYTHON_TAG!") do (
        set "PYTHON_TAG=%%b"
    )
    echo 从 Dockerfile 检测到 Python 镜像标签: !PYTHON_TAG!
) else (
    echo 错误: 无法从 Dockerfile 中找到 Python 镜像标签
    echo 请确保 Dockerfile 中包含 "FROM python:xxx" 行
    exit /b 1
)

REM 检查 Python 镜像是否已存在
docker images --format "{{.Repository}}:{{.Tag}}" | findstr /C:"python:!PYTHON_TAG!" >nul
if %errorlevel% equ 0 (
    echo Python 镜像 python:!PYTHON_TAG! 已存在，跳过拉取
) else (
    echo 正在拉取 python:!PYTHON_TAG!...
    docker pull python:!PYTHON_TAG!
    if %errorlevel% neq 0 (
        echo 错误: 拉取 Python 镜像失败
        echo 提示: 如果遇到网络问题，请检查网络连接或稍后重试
        echo 镜像标签: python:!PYTHON_TAG!
        exit /b 1
    )
)

REM 检查 MySQL 镜像是否已存在
docker images --format "{{.Repository}}:{{.Tag}}" | findstr /C:"mysql:8.0.44" >nul
if %errorlevel% equ 0 (
    echo MySQL 镜像 mysql:8.0.44 已存在，跳过拉取
) else (
    echo 正在拉取 mysql:8.0.44...
    docker pull mysql:8.0.44
    if %errorlevel% neq 0 (
        echo 错误: 拉取 MySQL 镜像失败
        exit /b 1
    )
)

echo.
echo 步骤 2: 构建应用镜像...
cd /d "!PROJECT_ROOT!"
docker build -t capacity-report-app:latest -f Dockerfile .
if %errorlevel% neq 0 (
    echo 错误: 构建应用镜像失败
    exit /b 1
)

echo.
echo 步骤 3: 标记 MySQL 镜像...
docker tag mysql:8.0.44 capacity-mysql:8.0.44
if %errorlevel% neq 0 (
    echo 错误: 标记 MySQL 镜像失败
    exit /b 1
)

echo.
echo 步骤 4: 导出镜像到 dist 目录...
if not exist "%DIST_DIR%images" mkdir "%DIST_DIR%images"
echo 正在导出镜像到单个 tar 文件:
echo   - capacity-report-app:latest (应用镜像)
echo   - capacity-mysql:8.0.44 (MySQL 镜像)
docker save capacity-report-app:latest capacity-mysql:8.0.44 -o "%DIST_DIR%images\capacity-images.tar"
if %errorlevel% neq 0 (
    echo 错误: 导出镜像失败
    exit /b 1
)
echo 镜像导出完成: %DIST_DIR%images\capacity-images.tar
echo 注意: 此文件包含应用镜像和 MySQL 镜像，部署时会自动加载所有镜像

echo.
echo 步骤 5: 复制必要文件到 dist 目录...
REM 创建必要的目录结构
if not exist "%DIST_DIR%mysql\conf.d" mkdir "%DIST_DIR%mysql\conf.d"
if not exist "%DIST_DIR%mysql\init" mkdir "%DIST_DIR%mysql\init"

REM 复制配置文件
echo 正在复制配置文件...
if exist "!PROJECT_ROOT!\Configure.json" (
    copy "!PROJECT_ROOT!\Configure.json" "!DIST_DIR!" >nul
    echo   - Configure.json 已复制
    REM 更新为 Docker 环境配置
    echo 正在更新 Configure.json 为 Docker 环境配置...
    powershell -NoProfile -Command "$json = Get-Content \"%DIST_DIR%Configure.json\" -Raw -Encoding UTF8 | ConvertFrom-Json; $json.MySQL_DBInfo.host = 'capacity-mysql'; $json.MySQL_DBInfo.port = 3306; $json.MySQL_DBInfo.user = 'root'; $json.MySQL_DBInfo.passwd = 'gmcc123'; $json.MySQL_DBInfo.dbname = 'CapacityReport'; $json | ConvertTo-Json -Depth 10 | Set-Content \"%DIST_DIR%Configure.json\" -Encoding UTF8"
    if %errorlevel% equ 0 (
        echo   - 已更新数据库配置: host=capacity-mysql, port=3306, user=root, passwd=gmcc123
    ) else (
        echo 警告: 无法自动更新 Configure.json，请手动修改数据库配置
    )
) else (
    echo 警告: Configure.json 不存在: !PROJECT_ROOT!\Configure.json
)

if exist "!PROJECT_ROOT!\ReportScript.sql" (
    copy "!PROJECT_ROOT!\ReportScript.sql" "!DIST_DIR!" >nul
    echo   - ReportScript.sql 已复制
) else (
    echo 警告: ReportScript.sql 不存在: !PROJECT_ROOT!\ReportScript.sql
)

if exist "!PROJECT_ROOT!\mysql\conf.d\custom.cnf" (
    copy "!PROJECT_ROOT!\mysql\conf.d\custom.cnf" "!DIST_DIR!mysql\conf.d\" >nul
    echo   - mysql\conf.d\custom.cnf 已复制
) else (
    echo 警告: mysql\conf.d\custom.cnf 不存在: !PROJECT_ROOT!\mysql\conf.d\custom.cnf
)

if exist "!PROJECT_ROOT!\mysql\init\01-init-db.sql" (
    copy "!PROJECT_ROOT!\mysql\init\01-init-db.sql" "!DIST_DIR!mysql\init\" >nul
    echo   - mysql\init\01-init-db.sql 已复制
) else (
    echo 警告: mysql\init\01-init-db.sql 不存在: !PROJECT_ROOT!\mysql\init\01-init-db.sql
)

echo.
echo 步骤 6: 计算文件大小...
for %%A in ("%DIST_DIR%images\capacity-images.tar") do (
    set SIZE=%%~zA
    set /a SIZE_MB=!SIZE!/1024/1024
    echo 镜像文件大小: !SIZE_MB! MB
)

echo.
echo 步骤 7: 清理临时目录...
if exist "%DIST_DIR%cache" (
    rd /s /q "%DIST_DIR%cache" 2>nul
    echo   - 已删除 cache 目录
)
if exist "%DIST_DIR%logs" (
    rd /s /q "%DIST_DIR%logs" 2>nul
    echo   - 已删除 logs 目录
)

echo.
echo ==========================================
echo 构建完成！
echo ==========================================
echo.
echo 离线部署包位置: %DIST_DIR%
echo.
echo 部署步骤:
echo 1. 将整个 dist 目录传输到目标 Linux 机器
echo 2. 在目标机器上执行: sh dist/deploy.sh
echo.
echo 端口映射:
echo   - 应用端口: 19081 (原 9081)
echo   - MySQL 端口: 13306 (原 3306)
echo.

endlocal
