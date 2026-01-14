#!/bin/bash
# CapacityReport 启动脚本

echo "Starting CapacityReport..."

# 创建必要的目录
mkdir -p /var/log/supervisor /var/run /app/cache

# 启动 supervisor
exec supervisord -c /app/supervisord.conf
