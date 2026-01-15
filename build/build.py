#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CapacityReport 统一构建脚本
支持完整部署包和更新包的构建
"""

import os
import sys
import json
import shutil
import subprocess
import re
import tarfile
from pathlib import Path

# ============================================================================
# 配置常量 - 可根据需要修改
# ============================================================================

# 默认镜像版本
DEFAULT_MYSQL_VERSION = "8.0.44"
DEFAULT_PYTHON_VERSION = "3.13.11-slim"

# 版本要求
MYSQL_MIN_VERSION = (8, 0, 0)  # MySQL >= 8.0
MYSQL_MAX_VERSION = (9, 0, 0)  # MySQL < 9.0
PYTHON_MIN_VERSION = (3, 10, 0)  # Python >= 3.10
PYTHON_MAX_VERSION = (3, 14, 0)  # Python < 3.14

# 数据库配置
MYSQL_ROOT_USER = "root"
MYSQL_ROOT_PASSWORD = "gmcc123"
MYSQL_DATABASE = "CapacityReport"
MYSQL_HOST = "capacity-mysql"
MYSQL_PORT = 3306

# 应用端口映射
APP_PORT_HOST = 19081
APP_PORT_CONTAINER = 9081
MYSQL_PORT_HOST = 13306
MYSQL_PORT_CONTAINER = 3306

# ============================================================================
# 脚本目录配置
# ============================================================================

SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DIST_DIR = PROJECT_ROOT / "dist"
BUILD_DIR = PROJECT_ROOT / "build"
TEMP_BUILD_DIR = BUILD_DIR / "temp"

# 颜色输出（Windows 支持）
import platform
if platform.system() == 'Windows':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except:
        pass

class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    RESET = '\033[0m'

def print_step(msg):
    print(f"\n{Colors.GREEN}{msg}{Colors.RESET}")

def print_info(msg):
    print(f"  {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}警告: {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}错误: {msg}{Colors.RESET}")

def print_choice(msg):
    print(f"{Colors.BLUE}{msg}{Colors.RESET}")

def run_cmd(cmd, check=True, capture_output=False):
    """执行命令"""
    if isinstance(cmd, str):
        cmd = cmd.split()
    try:
        result = subprocess.run(
            cmd,
            check=check,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        if check:
            print_error(f"命令执行失败: {' '.join(cmd)}")
            sys.exit(1)
        return None
    except FileNotFoundError:
        print_error(f"命令未找到: {cmd[0]}")
        sys.exit(1)

def check_command(cmd):
    """检查命令是否存在"""
    try:
        if cmd == "docker":
            subprocess.run([cmd, "--version"], capture_output=True, check=True)
        elif cmd == "docker-compose":
            subprocess.run([cmd, "version"], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False

def parse_version(version_str):
    """解析版本字符串为元组，例如 '8.0.44' -> (8, 0, 44)"""
    parts = version_str.split('.')
    try:
        # 处理带后缀的版本，如 '3.13.11-slim' -> (3, 13, 11)
        base_version = parts[0] if len(parts) > 0 else '0'
        major = int(base_version)
        minor = int(parts[1]) if len(parts) > 1 else 0
        patch_str = parts[2] if len(parts) > 2 else '0'
        # 移除后缀，如 '11-slim' -> '11'
        patch = int(patch_str.split('-')[0])
        return (major, minor, patch)
    except (ValueError, IndexError):
        return None

def check_version_in_range(version_tuple, min_version, max_version):
    """检查版本是否在指定范围内 [min, max)"""
    if version_tuple is None:
        return False
    return min_version <= version_tuple < max_version

def get_python_tag_from_dockerfile():
    """从 Dockerfile 中提取 Python 镜像标签"""
    # 从 build 目录读取 Dockerfile
    dockerfile_path = BUILD_DIR / "Dockerfile"
    if not dockerfile_path.exists():
        print_error(f"Dockerfile 不存在: {dockerfile_path}")
        print_error("请确保 build/Dockerfile 文件存在")
        sys.exit(1)
    
    with open(dockerfile_path, 'r', encoding='utf-8') as f:
        for line in f:
            match = re.match(r'^FROM\s+python:(.+?)(?:\s|$)', line, re.IGNORECASE)
            if match:
                tag = match.group(1).strip()
                return tag
    
    print_error("无法从 Dockerfile 中找到 Python 镜像标签")
    print_error("请确保 Dockerfile 中包含 'FROM python:xxx' 行")
    sys.exit(1)

def check_and_get_python_image():
    """检查并获取符合要求的 Python 镜像"""
    dockerfile_tag = get_python_tag_from_dockerfile()
    dockerfile_version = parse_version(dockerfile_tag)
    
    # 检查 Dockerfile 中的版本是否符合要求
    if dockerfile_version and check_version_in_range(
        dockerfile_version, PYTHON_MIN_VERSION, PYTHON_MAX_VERSION
    ):
        print_info(f"Dockerfile 中的 Python 版本符合要求: {dockerfile_tag}")
        return f"python:{dockerfile_tag}"
    else:
        print_warning(f"Dockerfile 中的 Python 版本 {dockerfile_tag} 不符合要求")
        print_warning(f"要求: Python >= {'.'.join(map(str, PYTHON_MIN_VERSION))} < {'.'.join(map(str, PYTHON_MAX_VERSION))}")
        print_info(f"将使用默认版本: {DEFAULT_PYTHON_VERSION}")
        print_info(f"如果镜像不存在，将自动拉取: python:{DEFAULT_PYTHON_VERSION}")
        return f"python:{DEFAULT_PYTHON_VERSION}"

def check_and_get_mysql_image():
    """检查并获取符合要求的 MySQL 镜像"""
    # 检查默认版本是否符合要求
    default_version = parse_version(DEFAULT_MYSQL_VERSION)
    if default_version and check_version_in_range(
        default_version, MYSQL_MIN_VERSION, MYSQL_MAX_VERSION
    ):
        print_info(f"默认 MySQL 版本符合要求: {DEFAULT_MYSQL_VERSION}")
        return f"mysql:{DEFAULT_MYSQL_VERSION}"
    else:
        print_error(f"默认 MySQL 版本 {DEFAULT_MYSQL_VERSION} 不符合要求")
        print_error(f"要求: MySQL >= {'.'.join(map(str, MYSQL_MIN_VERSION))} < {'.'.join(map(str, MYSQL_MAX_VERSION))}")
        sys.exit(1)

def image_exists(image_name):
    """检查镜像是否已存在"""
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
            capture_output=True,
            text=True,
            check=True
        )
        return image_name in result.stdout
    except:
        return False

def format_size(size_bytes):
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"

def write_sh_script(file_path, content):
    """写入 shell 脚本，确保使用 LF 换行和 UTF-8 编码"""
    # 确保内容使用 LF 换行
    content = content.replace('\r\n', '\n').replace('\r', '\n')
    # 写入文件（二进制模式确保换行符不被转换）
    with open(file_path, 'wb') as f:
        f.write(content.encode('utf-8'))
    # 设置执行权限（在 Linux 上）
    if platform.system() != 'Windows':
        os.chmod(file_path, 0o755)

def get_deploy_sh():
    """生成 deploy.sh 脚本内容"""
    mysql_version = DEFAULT_MYSQL_VERSION
    return f'''#!/bin/bash
# CapacityReport Deployment Script
# Run this script on offline machine to import images and start services

set -e

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$SCRIPT_DIR"

# Set permissions automatically
chmod -R 0777 "$SCRIPT_DIR" 2>/dev/null || true
find "$SCRIPT_DIR" -type f \\( -name "*.sh" -o -name "*.py" \\) -exec chmod +x {{}} \\; 2>/dev/null || true

echo "=========================================="
echo "CapacityReport Deployment"
echo "=========================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found, please install Docker"
    exit 1
fi

# Check Docker Compose
DOCKER_COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "Error: Docker Compose not found, please install Docker Compose"
    exit 1
fi

# Check image file
if [ ! -f "images/capacity-images.tar" ]; then
    echo "Error: Image file not found: images/capacity-images.tar"
    exit 1
fi

echo "Step 1: Checking ports..."
check_port() {{
    local port=${{1}}
    local name=${{2}}
    local in_use=false
    
    if command -v lsof &> /dev/null; then
        if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            in_use=true
        fi
    elif command -v netstat &> /dev/null; then
        if netstat -tuln 2>/dev/null | grep -q ":$port "; then
            in_use=true
        fi
    elif command -v ss &> /dev/null; then
        if ss -tuln 2>/dev/null | grep -q ":$port "; then
            in_use=true
        fi
    fi
    
    if [ "$in_use" = true ]; then
        echo "Warning: Port $port ($name) is in use"
        read -p "Continue? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
{{}}

check_port {APP_PORT_HOST} "App"
check_port {MYSQL_PORT_HOST} "MySQL"

echo ""
echo "Step 2: Loading images..."
docker load -i images/capacity-images.tar >/dev/null 2>&1

echo ""
echo "Step 3: Verifying images..."
if docker images | grep -q "capacity-report-app.*latest"; then
    echo "  App image: OK"
else
    echo "  App image: FAILED"
    exit 1
fi

if docker images | grep -q "capacity-mysql.*{mysql_version}"; then
    echo "  MySQL image: OK"
else
    echo "  MySQL image: FAILED"
    exit 1
fi

echo ""
echo "Step 4: Creating directories..."
mkdir -p cache logs
chmod 777 cache logs 2>/dev/null || true

echo ""
echo "Step 5: Checking config..."
if [ ! -f "Configure.json" ]; then
    echo "  Creating default Configure.json..."
    cat > Configure.json << 'EOF'
{{
  "MySQL_DBInfo": {{
    "host": "{MYSQL_HOST}",
    "port": {MYSQL_PORT},
    "user": "{MYSQL_ROOT_USER}",
    "passwd": "{MYSQL_ROOT_PASSWORD}",
    "dbname": "{MYSQL_DATABASE}"
  }},
  "ExtractField": []
}}
EOF
else
    if command -v python3 &> /dev/null || command -v python &> /dev/null; then
        (command -v python3 >/dev/null && python3 || python) << 'PYEOF'
import json
import sys

try:
    with open('Configure.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    db_info = config.get('MySQL_DBInfo', {{}})
    needs_update = False
    
    if db_info.get('host') != '{MYSQL_HOST}':
        db_info['host'] = '{MYSQL_HOST}'
        needs_update = True
    
    if db_info.get('port') != {MYSQL_PORT}:
        db_info['port'] = {MYSQL_PORT}
        needs_update = True
    
    if db_info.get('user') != '{MYSQL_ROOT_USER}':
        db_info['user'] = '{MYSQL_ROOT_USER}'
        needs_update = True
    
    if db_info.get('passwd') != '{MYSQL_ROOT_PASSWORD}':
        db_info['passwd'] = '{MYSQL_ROOT_PASSWORD}'
        needs_update = True
    
    if db_info.get('dbname') != '{MYSQL_DATABASE}':
        db_info['dbname'] = '{MYSQL_DATABASE}'
        needs_update = True
    
    if needs_update:
        with open('Configure.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("  Updated Configure.json")
except:
    pass
PYEOF
    fi
fi

if [ ! -f "ReportScript.sql" ]; then
    touch ReportScript.sql
fi

echo ""
echo "Step 6: Starting services..."
$DOCKER_COMPOSE_CMD down 2>/dev/null || true
$DOCKER_COMPOSE_CMD up -d >/dev/null 2>&1

echo ""
echo "Step 7: Waiting for services..."
for i in {{1..30}}; do
    if docker exec capacity-mysql mysqladmin ping -h localhost -u {MYSQL_ROOT_USER} -p{MYSQL_ROOT_PASSWORD} --silent 2>/dev/null; then
        echo "  MySQL: Ready"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "  MySQL: Timeout"
        exit 1
    fi
    sleep 2
done

if command -v curl &> /dev/null; then
    for i in {{1..30}}; do
        if curl -f http://localhost:{APP_PORT_HOST}/health >/dev/null 2>&1; then
            echo "  App: Ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "  App: Timeout"
            echo "  Check logs: $DOCKER_COMPOSE_CMD logs capacity-app"
            exit 1
        fi
        sleep 2
    done
else
    for i in {{1..30}}; do
        if docker ps --filter "name=capacity-report-app" --filter "status=running" --format "{{.Names}}" | grep -q "capacity-report-app"; then
            if docker inspect capacity-report-app --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
                echo "  App: Ready"
                break
            elif [ $i -gt 10 ]; then
                echo "  App: Running"
                break
            fi
        fi
        if [ $i -eq 30 ]; then
            echo "  App: Timeout"
            exit 1
        fi
        sleep 2
    done
fi

echo ""
echo "=========================================="
echo "Deployment completed!"
echo "=========================================="
echo ""
echo "Access: http://localhost:{APP_PORT_HOST}"
echo ""
echo "Commands:"
echo "  Logs:    $DOCKER_COMPOSE_CMD logs -f"
echo "  Stop:    $DOCKER_COMPOSE_CMD down"
echo "  Restart: $DOCKER_COMPOSE_CMD restart"
echo "  Status:  $DOCKER_COMPOSE_CMD ps"
echo ""
echo "Database:"
echo "  Host:     localhost"
echo "  Port:     {MYSQL_PORT_HOST}"
echo "  User:     {MYSQL_ROOT_USER}"
echo "  Password: {MYSQL_ROOT_PASSWORD}"
echo "  Database: {MYSQL_DATABASE}"
echo ""
'''

def get_update_sh():
    """生成 update.sh 脚本内容"""
    return f'''#!/bin/bash
# CapacityReport Update Script
# Update application container without affecting database
# Run this script when you need to update the application

set -e

SCRIPT_DIR="$(cd "$(dirname "${{BASH_SOURCE[0]}}")" && pwd)"
cd "$SCRIPT_DIR"

# Set permissions automatically
chmod -R 0777 "$SCRIPT_DIR" 2>/dev/null || true
find "$SCRIPT_DIR" -type f \\( -name "*.sh" -o -name "*.py" \\) -exec chmod +x {{}} \\; 2>/dev/null || true

echo "=========================================="
echo "CapacityReport Application Update"
echo "=========================================="
echo ""

# Check Docker
if ! command -v docker &> /dev/null; then
    echo "Error: Docker not found, please install Docker"
    exit 1
fi

# Check Docker Compose
DOCKER_COMPOSE_CMD=""
if docker compose version &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker compose"
elif command -v docker-compose &> /dev/null; then
    DOCKER_COMPOSE_CMD="docker-compose"
else
    echo "Error: Docker Compose not found, please install Docker Compose"
    exit 1
fi

# Check if services are running
if ! docker ps --format "{{.Names}}" | grep -q "capacity-report-app"; then
    echo "Error: Application container is not running"
    echo "Please use deploy.sh for initial deployment"
    exit 1
fi

echo "Step 1: Checking current status..."
if docker ps --format "{{.Names}}" | grep -q "capacity-mysql"; then
    echo "  MySQL: Running"
else
    echo "  Warning: MySQL container is not running"
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

echo ""
echo "Step 2: Loading new application image..."
if [ -f "images/capacity-app-update.tar" ]; then
    echo "  Loading images from capacity-app-update.tar..."
    docker load -i images/capacity-app-update.tar >/dev/null 2>&1
    
    if docker images | grep -q "capacity-report-app.*latest"; then
        echo "  App image: Loaded"
    else
        echo "  App image: Not found in tar file"
        exit 1
    fi
else
    echo "  Error: Image file not found: images/capacity-app-update.tar"
    exit 1
fi

echo ""
echo "Step 3: Stopping application container..."
$DOCKER_COMPOSE_CMD stop capacity-app 2>/dev/null || true
$DOCKER_COMPOSE_CMD rm -f capacity-app 2>/dev/null || true
echo "  Application stopped"

echo ""
echo "Step 4: Updating configuration files..."
if [ -f "Configure.json" ]; then
    if command -v python3 &> /dev/null || command -v python &> /dev/null; then
        (command -v python3 >/dev/null && python3 || python) << 'PYEOF'
import json
import sys

try:
    with open('Configure.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    db_info = config.get('MySQL_DBInfo', {{}})
    needs_update = False
    
    if db_info.get('host') != '{MYSQL_HOST}':
        db_info['host'] = '{MYSQL_HOST}'
        needs_update = True
    
    if db_info.get('port') != {MYSQL_PORT}:
        db_info['port'] = {MYSQL_PORT}
        needs_update = True
    
    if needs_update:
        with open('Configure.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        print("  Updated Configure.json")
except:
    pass
PYEOF
    fi
else
    echo "  Warning: Configure.json not found, creating default..."
    cat > Configure.json << 'EOF'
{{
  "MySQL_DBInfo": {{
    "host": "{MYSQL_HOST}",
    "port": {MYSQL_PORT},
    "user": "{MYSQL_ROOT_USER}",
    "passwd": "{MYSQL_ROOT_PASSWORD}",
    "dbname": "{MYSQL_DATABASE}"
  }},
  "ExtractField": []
}}
EOF
fi

if [ ! -f "ReportScript.sql" ]; then
    touch ReportScript.sql
fi

mkdir -p cache logs
chmod 777 cache logs 2>/dev/null || true

echo ""
echo "Step 5: Starting application container..."
$DOCKER_COMPOSE_CMD up -d capacity-app >/dev/null 2>&1
echo "  Application started"

echo ""
echo "Step 6: Waiting for application to be ready..."
if command -v curl &> /dev/null; then
    for i in {{1..30}}; do
        if curl -f http://localhost:{APP_PORT_HOST}/health >/dev/null 2>&1; then
            echo "  App: Ready"
            break
        fi
        if [ $i -eq 30 ]; then
            echo "  App: Timeout (may still be starting)"
            echo "  Check logs: $DOCKER_COMPOSE_CMD logs capacity-app"
            exit 1
        fi
        sleep 2
    done
else
    for i in {{1..30}}; do
        if docker ps --filter "name=capacity-report-app" --filter "status=running" --format "{{.Names}}" | grep -q "capacity-report-app"; then
            if docker inspect capacity-report-app --format='{{.State.Health.Status}}' 2>/dev/null | grep -q "healthy"; then
                echo "  App: Ready"
                break
            elif [ $i -gt 10 ]; then
                echo "  App: Running"
                break
            fi
        fi
        if [ $i -eq 30 ]; then
            echo "  App: Timeout"
            echo "  Check logs: $DOCKER_COMPOSE_CMD logs capacity-app"
            exit 1
        fi
        sleep 2
    done
fi

echo ""
echo "=========================================="
echo "Update completed!"
echo "=========================================="
echo ""
echo "Application: http://localhost:{APP_PORT_HOST}"
echo ""
echo "Database status:"
if docker ps --format "{{.Names}}" | grep -q "capacity-mysql"; then
    echo "  MySQL: Running (unchanged)"
else
    echo "  MySQL: Not running"
fi
echo ""
echo "Useful commands:"
echo "  View logs:    $DOCKER_COMPOSE_CMD logs -f capacity-app"
echo "  Restart app:  $DOCKER_COMPOSE_CMD restart capacity-app"
echo "  Status:       $DOCKER_COMPOSE_CMD ps"
echo ""
'''

def build_full_package():
    """构建完整部署包"""
    print_step("构建完整部署包...")
    
    # 清理临时目录
    if TEMP_BUILD_DIR.exists():
        shutil.rmtree(TEMP_BUILD_DIR)
    TEMP_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    
    # 检查 Docker
    if not check_command("docker"):
        print_error("未检测到 Docker，请先安装 Docker Desktop")
        sys.exit(1)
    
    # 检查 Docker Compose
    docker_compose_cmd = None
    try:
        subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
        docker_compose_cmd = "docker compose"
    except:
        if check_command("docker-compose"):
            docker_compose_cmd = "docker-compose"
        else:
            print_error("未检测到 Docker Compose")
            sys.exit(1)
    
    # 检查并获取符合要求的镜像
    print_step("检查镜像版本...")
    python_image = check_and_get_python_image()
    mysql_image = check_and_get_mysql_image()
    
    # 拉取基础镜像（如果不存在则自动拉取）
    print_step("拉取基础镜像...")
    if not image_exists(python_image):
        print_info(f"Python 镜像不存在，正在拉取: {python_image}")
        run_cmd(["docker", "pull", python_image])
        print_info(f"Python 镜像拉取完成")
    else:
        print_info(f"Python 镜像已存在: {python_image}")
    
    if not image_exists(mysql_image):
        print_info(f"MySQL 镜像不存在，正在拉取: {mysql_image}")
        run_cmd(["docker", "pull", mysql_image])
        print_info(f"MySQL 镜像拉取完成")
    else:
        print_info(f"MySQL 镜像已存在: {mysql_image}")
    
    # 构建应用镜像
    print_step("构建应用镜像...")
    # 使用 build 目录的 Dockerfile
    dockerfile_path = BUILD_DIR / "Dockerfile"
    if not dockerfile_path.exists():
        print_error(f"Dockerfile 不存在: {dockerfile_path}")
        sys.exit(1)
    print_info(f"使用 build 目录的 Dockerfile: {dockerfile_path}")
    
    # 构建时使用项目根目录作为上下文（因为需要复制应用代码）
    os.chdir(PROJECT_ROOT)
    # 但使用 build 目录的 Dockerfile
    dockerfile_arg = str(dockerfile_path)
    # .dockerignore 会自动使用构建上下文根目录的（即 PROJECT_ROOT/.dockerignore）
    # 从 build 目录复制 .dockerignore 到根目录（临时，构建时使用）
    dockerignore_build = BUILD_DIR / ".dockerignore"
    dockerignore_root = PROJECT_ROOT / ".dockerignore"
    if dockerignore_build.exists():
        shutil.copy2(dockerignore_build, dockerignore_root)
        print_info("已使用 build 目录的 .dockerignore")
    run_cmd(["docker", "build", "-t", "capacity-report-app:latest", "-f", dockerfile_arg, "."])
    # 清理临时复制的 .dockerignore（如果根目录原本没有）
    if dockerignore_build.exists() and dockerignore_root.exists():
        try:
            # 如果内容相同，说明是从 build 目录复制的，可以删除
            if dockerignore_build.read_text() == dockerignore_root.read_text():
                dockerignore_root.unlink()
                print_info("已清理临时 .dockerignore")
        except:
            pass
    
    # 标记 MySQL 镜像（提取版本号）
    mysql_tag = mysql_image.split(':')[1]
    mysql_tagged = f"capacity-mysql:{mysql_tag}"
    run_cmd(["docker", "tag", mysql_image, mysql_tagged])
    
    # 导出镜像
    print_step("导出镜像...")
    images_dir = TEMP_BUILD_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    tar_file = images_dir / "capacity-images.tar"
    # 提取 MySQL 标签
    mysql_tag = mysql_image.split(':')[1]
    mysql_tagged = f"capacity-mysql:{mysql_tag}"
    
    run_cmd([
        "docker", "save",
        "capacity-report-app:latest",
        mysql_tagged,
        "-o", str(tar_file)
    ])
    print_info(f"镜像导出完成: {format_size(tar_file.stat().st_size)}")
    
    # 复制配置文件
    print_step("复制配置文件...")
    # 优先从 build 目录读取，如果不存在则从根目录读取
    def get_source_path(filename, subdir=None):
        """获取源文件路径，优先 build 目录，其次根目录"""
        if subdir:
            build_path = BUILD_DIR / subdir / filename
            root_path = PROJECT_ROOT / subdir / filename
        else:
            build_path = BUILD_DIR / filename
            root_path = PROJECT_ROOT / filename
        return build_path if build_path.exists() else root_path
    
    # Configure.json 和 ReportScript.sql 从项目根目录读取（应用配置文件）
    files_to_copy = [
        (PROJECT_ROOT / "Configure.json", TEMP_BUILD_DIR / "Configure.json"),
        (PROJECT_ROOT / "ReportScript.sql", TEMP_BUILD_DIR / "ReportScript.sql"),
        (get_source_path("docker-compose.yml"), TEMP_BUILD_DIR / "docker-compose.yml"),
        (get_source_path("custom.cnf", "mysql/conf.d"), TEMP_BUILD_DIR / "mysql" / "conf.d" / "custom.cnf"),
        (get_source_path("01-init-db.sql", "mysql/init"), TEMP_BUILD_DIR / "mysql" / "init" / "01-init-db.sql"),
    ]
    
    for src, dst in files_to_copy:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
        else:
            print_warning(f"{src.name} 不存在: {src}")
    
    # 更新 Configure.json
    config_file = TEMP_BUILD_DIR / "Configure.json"
    if config_file.exists():
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        config['MySQL_DBInfo'] = {
            'host': MYSQL_HOST,
            'port': MYSQL_PORT,
            'user': MYSQL_ROOT_USER,
            'passwd': MYSQL_ROOT_PASSWORD,
            'dbname': MYSQL_DATABASE
        }
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    # 生成 deploy.sh
    print_step("生成部署脚本...")
    write_sh_script(TEMP_BUILD_DIR / "deploy.sh", get_deploy_sh())
    
    # 打包
    print_step("打包部署包...")
    tar_output = DIST_DIR / "capacity-report-full.tar.gz"
    DIST_DIR.mkdir(exist_ok=True)
    
    with tarfile.open(tar_output, 'w:gz') as tar:
        tar.add(TEMP_BUILD_DIR, arcname='.')
    
    print_info(f"部署包已生成: {tar_output}")
    print_info(f"文件大小: {format_size(tar_output.stat().st_size)}")
    
    # 清理临时文件和缓存
    print_step("清理临时文件...")
    if TEMP_BUILD_DIR.exists():
        shutil.rmtree(TEMP_BUILD_DIR, ignore_errors=True)
        print_info("已清理临时构建目录")
    
    return tar_output

def build_update_package():
    """构建更新包"""
    print_step("构建更新包...")
    
    # 清理临时目录
    if TEMP_BUILD_DIR.exists():
        shutil.rmtree(TEMP_BUILD_DIR)
    TEMP_BUILD_DIR.mkdir(parents=True, exist_ok=True)
    
    # 检查 Docker
    if not check_command("docker"):
        print_error("未检测到 Docker")
        sys.exit(1)
    
    # 检查并获取符合要求的镜像
    print_step("检查镜像版本...")
    python_image = check_and_get_python_image()
    
    # 拉取基础镜像（如果不存在则自动拉取）
    print_step("拉取基础镜像...")
    if not image_exists(python_image):
        print_info(f"Python 镜像不存在，正在拉取: {python_image}")
        run_cmd(["docker", "pull", python_image])
        print_info(f"Python 镜像拉取完成")
    else:
        print_info(f"Python 镜像已存在: {python_image}")
    
    # 构建应用镜像
    print_step("构建应用镜像...")
    # 使用 build 目录的 Dockerfile
    dockerfile_path = BUILD_DIR / "Dockerfile"
    if not dockerfile_path.exists():
        print_error(f"Dockerfile 不存在: {dockerfile_path}")
        sys.exit(1)
    print_info(f"使用 build 目录的 Dockerfile: {dockerfile_path}")
    
    # 构建时使用项目根目录作为上下文（因为需要复制应用代码）
    os.chdir(PROJECT_ROOT)
    # 但使用 build 目录的 Dockerfile
    dockerfile_arg = str(dockerfile_path)
    # .dockerignore 会自动使用构建上下文根目录的（即 PROJECT_ROOT/.dockerignore）
    # 从 build 目录复制 .dockerignore 到根目录（临时，构建时使用）
    dockerignore_build = BUILD_DIR / ".dockerignore"
    dockerignore_root = PROJECT_ROOT / ".dockerignore"
    if dockerignore_build.exists():
        shutil.copy2(dockerignore_build, dockerignore_root)
        print_info("已使用 build 目录的 .dockerignore")
    run_cmd(["docker", "build", "-t", "capacity-report-app:latest", "-f", dockerfile_arg, "."])
    # 清理临时复制的 .dockerignore（如果根目录原本没有）
    if dockerignore_build.exists() and dockerignore_root.exists():
        try:
            # 如果内容相同，说明是从 build 目录复制的，可以删除
            if dockerignore_build.read_text() == dockerignore_root.read_text():
                dockerignore_root.unlink()
                print_info("已清理临时 .dockerignore")
        except:
            pass
    
    # 导出镜像
    print_step("导出镜像...")
    images_dir = TEMP_BUILD_DIR / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    
    tar_file = images_dir / "capacity-app-update.tar"
    run_cmd([
        "docker", "save",
        "capacity-report-app:latest",
        "-o", str(tar_file)
    ])
    print_info(f"镜像导出完成: {format_size(tar_file.stat().st_size)}")
    
    # 复制配置文件
    print_step("复制配置文件...")
    # 从 build 目录读取配置文件
    def get_source_path(filename, subdir=None):
        """获取源文件路径，从 build 目录读取"""
        if subdir:
            return BUILD_DIR / subdir / filename
        else:
            return BUILD_DIR / filename
    
    files_to_copy = [
        (get_source_path("docker-compose.yml"), TEMP_BUILD_DIR / "docker-compose.yml"),
    ]
    
    for src, dst in files_to_copy:
        if src.exists():
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src, dst)
    
    # 生成 update.sh
    print_step("生成更新脚本...")
    write_sh_script(TEMP_BUILD_DIR / "update.sh", get_update_sh())
    
    # 打包
    print_step("打包更新包...")
    tar_output = DIST_DIR / "capacity-report-update.tar.gz"
    DIST_DIR.mkdir(exist_ok=True)
    
    with tarfile.open(tar_output, 'w:gz') as tar:
        tar.add(TEMP_BUILD_DIR, arcname='.')
    
    print_info(f"更新包已生成: {tar_output}")
    print_info(f"文件大小: {format_size(tar_output.stat().st_size)}")
    
    # 清理临时文件和缓存
    print_step("清理临时文件...")
    if TEMP_BUILD_DIR.exists():
        shutil.rmtree(TEMP_BUILD_DIR, ignore_errors=True)
        print_info("已清理临时构建目录")
    
    return tar_output

def main():
    print("=" * 60)
    print("CapacityReport 统一构建脚本")
    print("=" * 60)
    print()
    
    print_choice("请选择构建类型:")
    print("  1. 完整部署包 (包含 MySQL + 应用)")
    print("  2. 更新包 (仅应用)")
    print()
    
    while True:
        choice = input("请输入选项 (1/2): ").strip()
        if choice in ['1', '2']:
            break
        print_error("无效选项，请输入 1 或 2")
    
    print()
    
    if choice == '1':
        tar_file = build_full_package()
        print()
        print("=" * 60)
        print("构建完成！")
        print("=" * 60)
        print()
        print(f"部署包位置: {tar_file}")
        print()
        print("使用方法:")
        print("1. 将 tar.gz 文件传输到目标 Linux 机器")
        print("2. 解压: tar -xzf capacity-report-full.tar.gz")
        print("3. 进入解压目录，执行: sh deploy.sh")
        print()
    else:
        tar_file = build_update_package()
        print()
        print("=" * 60)
        print("构建完成！")
        print("=" * 60)
        print()
        print(f"更新包位置: {tar_file}")
        print()
        print("使用方法:")
        print("1. 将 tar.gz 文件传输到目标 Linux 机器")
        print("2. 解压: tar -xzf capacity-report-update.tar.gz")
        print("3. 进入解压目录，执行: sh update.sh")
        print()
        print("注意: 更新包仅用于更新已部署的应用，不包含 MySQL")
        print()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n构建已取消")
        sys.exit(1)
    except Exception as e:
        print_error(f"构建失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
