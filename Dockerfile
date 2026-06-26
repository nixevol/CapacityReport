# CapacityReport 平台容器版（单阶段）。
# 前端先在构建机用 node 构建：cd frontend && npm ci && npm run build（产出 frontend/dist）。
# 然后构建镜像：docker build -t capacity-report-app:latest .
# 基础镜像用 python:3.13.11-slim（内网无 dockerhub 时需本地已有该镜像），依赖从 PyPI 安装。
FROM python:3.13.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    CAPAREPORT_BASE_DIR=/data \
    CAPAREPORT_FRONTEND_DIR=/app/frontend/dist

COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY app/ ./app/
COPY frontend/dist ./frontend/dist
# 默认配置/脚本/特征库：首次启动由 entrypoint 播种到数据卷 /data（已存在则保留用户修改）。
COPY Configure.json ReportScript.sql CellData.sql ./defaults/
COPY db_init/ ./defaults/db_init/
COPY docker/ ./docker/
RUN sed -i 's/\r$//' /app/docker/entrypoint.sh \
    && cp /app/docker/entrypoint.sh /usr/local/bin/entrypoint.sh \
    && chmod +x /usr/local/bin/entrypoint.sh

VOLUME ["/data"]
EXPOSE 9081
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
