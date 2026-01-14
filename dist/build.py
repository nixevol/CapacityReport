#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CapacityReport 镜像构建和导出脚本 (Windows)
在有外网的 Windows 机器上运行此脚本，生成离线部署包
"""

import os
import sys
import json
import shutil
import subprocess
import re
from pathlib import Path

# 脚本所在目录
SCRIPT_DIR = Path(__file__).parent.absolute()
PROJECT_ROOT = SCRIPT_DIR.parent
DIST_DIR = SCRIPT_DIR

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
    RESET = '\033[0m'

def print_step(msg):
    print(f"\n{Colors.GREEN}{msg}{Colors.RESET}")

def print_info(msg):
    print(f"  {msg}")

def print_warning(msg):
    print(f"{Colors.YELLOW}警告: {msg}{Colors.RESET}")

def print_error(msg):
    print(f"{Colors.RED}错误: {msg}{Colors.RESET}")

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

def get_python_tag_from_dockerfile():
    """从 Dockerfile 中提取 Python 镜像标签"""
    dockerfile_path = PROJECT_ROOT / "Dockerfile"
    if not dockerfile_path.exists():
        print_error(f"Dockerfile 不存在: {dockerfile_path}")
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

def main():
    print("=" * 50)
    print("CapacityReport 离线部署包构建脚本")
    print("=" * 50)
    print()
    
    # 清理旧的构建文件
    print_step("清理旧的构建文件...")
    files_to_clean = [
        DIST_DIR / "images" / "capacity-images.tar",
        DIST_DIR / "Configure.json",
        DIST_DIR / "ReportScript.sql",
        DIST_DIR / "mysql" / "conf.d" / "custom.cnf",
        DIST_DIR / "mysql" / "init" / "01-init-db.sql",
    ]
    
    for file_path in files_to_clean:
        if file_path.exists():
            if file_path.is_file():
                file_path.unlink()
                print_info(f"已删除旧 {file_path.name}")
            elif file_path.is_dir():
                shutil.rmtree(file_path)
                print_info(f"已删除旧 {file_path.name}")
    
    print_info("清理完成")
    
    # 检查 Docker
    print_step("检查 Docker 环境...")
    if not check_command("docker"):
        print_error("未检测到 Docker，请先安装 Docker Desktop")
        sys.exit(1)
    print_info("Docker: OK")
    
    # 检查 Docker Compose
    docker_compose_cmd = None
    try:
        subprocess.run(["docker", "compose", "version"], capture_output=True, check=True)
        docker_compose_cmd = "docker compose"
        print_info("Docker Compose: OK (docker compose)")
    except:
        if check_command("docker-compose"):
            docker_compose_cmd = "docker-compose"
            print_info("Docker Compose: OK (docker-compose)")
        else:
            print_error("未检测到 Docker Compose，请先安装 Docker Compose")
            sys.exit(1)
    
    # 步骤 1: 拉取基础镜像
    print_step("步骤 1: 拉取基础镜像...")
    
    # 获取 Python 版本
    python_tag = get_python_tag_from_dockerfile()
    python_image = f"python:{python_tag}"
    print_info(f"从 Dockerfile 检测到 Python 镜像标签: {python_tag}")
    
    # 检查并拉取 Python 镜像
    if image_exists(python_image):
        print_info(f"Python 镜像 {python_image} 已存在，跳过拉取")
    else:
        print_info(f"正在拉取 {python_image}...")
        run_cmd(["docker", "pull", python_image])
        print_info(f"Python 镜像拉取完成")
    
    # 检查并拉取 MySQL 镜像
    mysql_image = "mysql:8.0.44"
    if image_exists(mysql_image):
        print_info(f"MySQL 镜像 {mysql_image} 已存在，跳过拉取")
    else:
        print_info(f"正在拉取 {mysql_image}...")
        run_cmd(["docker", "pull", mysql_image])
        print_info(f"MySQL 镜像拉取完成")
    
    # 步骤 2: 构建应用镜像
    print_step("步骤 2: 构建应用镜像...")
    os.chdir(PROJECT_ROOT)
    run_cmd(["docker", "build", "-t", "capacity-report-app:latest", "-f", "Dockerfile", "."])
    print_info("应用镜像构建完成")
    
    # 步骤 3: 标记 MySQL 镜像
    print_step("步骤 3: 标记 MySQL 镜像...")
    run_cmd(["docker", "tag", mysql_image, "capacity-mysql:8.0.44"])
    print_info("MySQL 镜像标记完成")
    
    # 步骤 4: 导出镜像
    print_step("步骤 4: 导出镜像到 dist 目录...")
    images_dir = DIST_DIR / "images"
    images_dir.mkdir(exist_ok=True)
    
    tar_file = images_dir / "capacity-images.tar"
    print_info("正在导出镜像到单个 tar 文件:")
    print_info("  - capacity-report-app:latest (应用镜像)")
    print_info("  - capacity-mysql:8.0.44 (MySQL 镜像)")
    
    run_cmd([
        "docker", "save",
        "capacity-report-app:latest",
        "capacity-mysql:8.0.44",
        "-o", str(tar_file)
    ])
    
    print_info(f"镜像导出完成: {tar_file}")
    print_info("注意: 此文件包含应用镜像和 MySQL 镜像，部署时会自动加载所有镜像")
    
    # 步骤 5: 复制必要文件
    print_step("步骤 5: 复制必要文件到 dist 目录...")
    
    # 创建必要的目录结构
    (DIST_DIR / "mysql" / "conf.d").mkdir(parents=True, exist_ok=True)
    (DIST_DIR / "mysql" / "init").mkdir(parents=True, exist_ok=True)
    
    # 复制配置文件
    print_info("正在复制配置文件...")
    
    files_to_copy = [
        (PROJECT_ROOT / "Configure.json", DIST_DIR / "Configure.json"),
        (PROJECT_ROOT / "ReportScript.sql", DIST_DIR / "ReportScript.sql"),
        (PROJECT_ROOT / "mysql" / "conf.d" / "custom.cnf", DIST_DIR / "mysql" / "conf.d" / "custom.cnf"),
        (PROJECT_ROOT / "mysql" / "init" / "01-init-db.sql", DIST_DIR / "mysql" / "init" / "01-init-db.sql"),
    ]
    
    for src, dst in files_to_copy:
        if src.exists():
            shutil.copy2(src, dst)
            print_info(f"{src.name} 已复制")
        else:
            print_warning(f"{src.name} 不存在: {src}")
    
    # 更新 Configure.json 为 Docker 环境配置
    config_file = DIST_DIR / "Configure.json"
    if config_file.exists():
        print_info("正在更新 Configure.json 为 Docker 环境配置...")
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            config['MySQL_DBInfo'] = {
                'host': 'capacity-mysql',
                'port': 3306,
                'user': 'root',
                'passwd': 'gmcc123',
                'dbname': 'CapacityReport'
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            print_info("已更新数据库配置: host=capacity-mysql, port=3306, user=root, passwd=gmcc123")
        except Exception as e:
            print_warning(f"无法自动更新 Configure.json: {e}")
            print_warning("请手动修改数据库配置")
    
    # 步骤 6: 计算文件大小
    print_step("步骤 6: 计算文件大小...")
    if tar_file.exists():
        size = tar_file.stat().st_size
        print_info(f"镜像文件大小: {format_size(size)}")
    
    # 步骤 7: 清理临时目录
    print_step("步骤 7: 清理临时目录...")
    temp_dirs = [DIST_DIR / "cache", DIST_DIR / "logs"]
    for temp_dir in temp_dirs:
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
            print_info(f"已删除 {temp_dir.name} 目录")
    
    # 完成
    print()
    print("=" * 50)
    print("构建完成！")
    print("=" * 50)
    print()
    print(f"离线部署包位置: {DIST_DIR}")
    print()
    print("部署步骤:")
    print("1. 将整个 dist 目录传输到目标 Linux 机器")
    print("2. 在目标机器上执行: sh dist/deploy.sh")
    print()
    print("端口映射:")
    print("  - 应用端口: 19081 (原 9081)")
    print("  - MySQL 端口: 13306 (原 3306)")
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
