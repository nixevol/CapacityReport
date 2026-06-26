#!/bin/sh
set -e

# 运行态都落在数据卷 /data：配置、脚本、特征库、历史、缓存、登录态。
mkdir -p /data/cache

seeded=0
if [ ! -f /data/Configure.json ]; then
  cp /app/defaults/Configure.json /data/Configure.json
  seeded=1
fi
[ -f /data/ReportScript.sql ] || cp /app/defaults/ReportScript.sql /data/ReportScript.sql
[ -f /data/CellData.sql ] || cp /app/defaults/CellData.sql /data/CellData.sql
[ -d /data/db_init ] || cp -r /app/defaults/db_init /data/db_init

# 首次播种时按容器环境变量改写 数据库/SFTP 连接（用户后续在界面的修改不会被覆盖）
if [ "$seeded" = "1" ] && [ -f /app/docker/apply_env_config.py ]; then
  python /app/docker/apply_env_config.py || true
fi

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 9081
