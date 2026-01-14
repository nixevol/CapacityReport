# CapacityReport Docker 部署指南

## 环境要求

- Docker Engine 20.10+
- Docker Compose 2.0+

## 快速启动

```bash
# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

## 内网离线部署

### 步骤1：准备镜像（在有外网的机器上）

```bash
# 拉取所需镜像
docker pull python:3.11-slim
docker pull mysql:8.0

# 导出为文件
docker save -o capacity-images.tar python:3.11-slim mysql:8.0

# 将 capacity-images.tar 传输到目标机器
```

### 步骤2：加载镜像（在目标机器上）

```bash
# 加载镜像
docker load -i capacity-images.tar
```

### 步骤3：构建并启动

```bash
# 构建应用镜像
docker-compose build

# 启动服务
docker-compose up -d
```

## 配置说明

### 数据库连接

Docker 环境下，需要修改 `Configure.json` 中的数据库地址：

```json
{
  "MySQL_DBInfo": {
    "host": "mysql",
    "port": 3306,
    "user": "root",
    "passwd": "gmcc123",
    "dbname": "CapacityReport"
  }
}
```

**注意**：
- Docker Compose 中 host 应设置为 `mysql`（服务名），而不是 `localhost` 或 `127.0.0.1`
- 数据库 `CapacityReport` 会在容器首次启动时自动创建（使用 utf8mb4 字符集）
- 如果数据目录已存在（从持久化卷恢复），数据库不会被重复创建，这是安全的

### 端口映射

| 服务 | 端口 | 说明 |
|-----|------|-----|
| app | 9081 | Web 应用 |
| mysql | 3306 | MySQL 数据库 |

## LOAD DATA INFILE 支持

MySQL 容器已配置支持 `LOAD DATA LOCAL INFILE`：

1. 服务端配置：`mysql/conf.d/custom.cnf` 中 `local_infile = ON`
2. 启动参数：`--local-infile=ON`
3. Python 客户端：PyMySQL 连接时 `local_infile=True`

验证是否启用：

```bash
docker exec -it capacity-mysql mysql -uroot -pgmcc123 -e "SHOW VARIABLES LIKE 'local_infile';"
```

预期输出：
```
+---------------+-------+
| Variable_name | Value |
+---------------+-------+
| local_infile  | ON    |
+---------------+-------+
```

## 数据持久化

| 路径 | 说明 |
|-----|-----|
| ./cache | 处理缓存和历史记录 |
| ./logs | 应用日志 |
| mysql-data | MySQL 数据（Docker 卷） |

## 常用命令

```bash
# 查看运行状态
docker-compose ps

# 查看应用日志
docker-compose logs -f app

# 查看 MySQL 日志
docker-compose logs -f mysql

# 重启应用
docker-compose restart app

# 进入应用容器
docker exec -it capacity-report bash

# 进入 MySQL
docker exec -it capacity-mysql mysql -uroot -pgmcc123

# 备份数据库
docker exec capacity-mysql mysqldump -uroot -pgmcc123 CapacityReport > backup.sql

# 恢复数据库
docker exec -i capacity-mysql mysql -uroot -pgmcc123 CapacityReport < backup.sql

# 清空数据重新开始
docker-compose down -v
docker-compose up -d
```

## 故障排查

### 应用无法连接 MySQL

1. 检查 MySQL 是否就绪：
   ```bash
   docker-compose logs mysql
   ```

2. 验证 MySQL 健康状态：
   ```bash
   docker exec capacity-mysql mysqladmin ping -uroot -pgmcc123
   ```

3. 检查 Configure.json 中 host 设置是否为 `mysql`

### LOAD DATA INFILE 不工作

1. 检查 MySQL 变量：
   ```bash
   docker exec -it capacity-mysql mysql -uroot -pgmcc123 -e "SHOW VARIABLES LIKE 'local_infile';"
   ```

2. 检查配置文件：
   ```bash
   docker exec -it capacity-mysql cat /etc/mysql/conf.d/custom.cnf
   ```

### cache 目录权限问题

```bash
chmod -R 777 cache/
```
