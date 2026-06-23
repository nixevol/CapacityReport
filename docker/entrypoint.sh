#!/bin/sh
set -e

# 运行态都落在数据卷 /data：配置、脚本、历史、缓存、登录态、Token。
mkdir -p /data/cache
[ -f /data/Configure.json ] || cp /app/defaults/Configure.json /data/Configure.json
[ -f /data/ReportScript.sql ] || cp /app/defaults/ReportScript.sql /data/ReportScript.sql

exec python -m uvicorn app.main:app --host 0.0.0.0 --port 9081
