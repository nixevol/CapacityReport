FROM python:3.11

WORKDIR /app

# 复制依赖文件
COPY requirements.txt ./

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 创建日志目录
RUN mkdir -p /var/log/supervisor /var/run

# 复制应用代码
COPY . .

# 设置启动脚本权限
RUN chmod +x /app/start.sh

# 暴露端口
EXPOSE 9081

# 使用启动脚本
CMD ["/app/start.sh"]
