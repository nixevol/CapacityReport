# CapacityReport Dockerfile
# 容量报表处理系统 - 用于内网离线部署

FROM python:3.13-slim

LABEL maintainer="CapacityReport"
LABEL description="容量报表处理系统"

WORKDIR /app

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 先复制依赖文件（利用缓存）
COPY requirements.txt ./

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建目录
RUN mkdir -p /var/log/supervisor /var/run /app/cache /app/static/lib

# 复制应用代码
COPY . .

# 设置启动脚本权限
RUN chmod +x /app/start.sh 2>/dev/null || true

# 暴露端口
EXPOSE 9081

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9081/health || exit 1

# 启动命令
CMD ["supervisord", "-c", "/app/supervisord.conf"]
