# CapacityReport Dockerfile
# 内网离线部署镜像，前端在镜像构建阶段编译后交给 FastAPI 托管。

FROM node:22-slim AS frontend-build

WORKDIR /frontend

COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ ./
RUN npm run build


FROM python:3.13.11-slim

LABEL maintainer="CapacityReport"
LABEL description="容量报表处理系统"

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libmariadb-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

RUN mkdir -p /var/log/supervisor /var/run /app/cache

COPY . .
COPY --from=frontend-build /frontend/dist /app/frontend/dist

RUN chmod +x /app/start.sh 2>/dev/null || true

EXPOSE 9081

HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:9081/health || exit 1

CMD ["supervisord", "-c", "/app/supervisord.conf"]
