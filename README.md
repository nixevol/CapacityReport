# CapacityReport - 容量报表处理系统

支持 Excel/CSV 文件上传、数据提取、清洗和导入 MySQL 数据库。

## 技术栈

- **后端**: FastAPI + Uvicorn + Supervisor
- **前端**: 原生 JavaScript + HTML/CSS
- **数据库**: MySQL 8.0+ (PyMySQL + SQLAlchemy)
- **数据处理**: Pandas + OpenPyXL
- **部署**: Docker + Docker Compose

## 数据库要求

- **MySQL**: >= 8.0, < 9.0
- **字符集**: utf8mb4
- **必需功能**: LOAD DATA LOCAL INFILE

## 目录结构

```
CapaReport/
├── app/                    # 应用代码
│   ├── main.py            # FastAPI 入口
│   ├── processor.py      # 数据处理
│   ├── database.py        # 数据库管理
│   ├── history.py         # 历史记录
│   └── config.py          # 配置管理
├── build/                  # 构建脚本和配置
│   ├── build.py           # 统一构建脚本
│   ├── Dockerfile         # Docker 镜像定义
│   ├── docker-compose.yml # Docker Compose 编排
│   └── mysql/             # MySQL 配置
├── static/                 # 前端静态文件
│   ├── index.html
│   ├── css/
│   └── js/
├── Configure.json          # 应用配置
├── ReportScript.sql        # SQL 处理脚本
├── requirements.txt       # Python 依赖
└── supervisord.conf       # Supervisor 配置
```

## 本地运行

### 前置要求

- Python >= 3.10, < 3.14
- MySQL >= 8.0, < 9.0

### 安装依赖

```bash
pip install -r requirements.txt
```

### 配置数据库

编辑 `Configure.json`，设置 MySQL 连接信息：

```json
{
  "MySQL_DBInfo": {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "passwd": "your_password",
    "dbname": "CapacityReport"
  }
}
```

### 启动服务

**Windows**:
```bash
run.bat
```

**Linux**:
```bash
supervisord -c supervisord.conf
```

访问: http://localhost:9081

## Docker 编译与部署

### 构建部署包

```bash
python build/build.py
```

选择构建类型：
- `1` - 完整部署包（MySQL + 应用）
- `2` - 更新包（仅应用）

输出文件在 `dist/` 目录：
- `capacity-report-full.tar.gz` - 完整部署包
- `capacity-report-update.tar.gz` - 更新包

### 部署

**完整部署**:
```bash
tar -xzf capacity-report-full.tar.gz
cd capacity-report-full
sh deploy.sh
```

**更新应用**:
```bash
tar -xzf capacity-report-update.tar.gz
cd capacity-report-update
sh update.sh
```

### 配置说明

Docker 环境配置在 `build/build.py` 文件头部：
- 默认镜像版本
- 数据库账号密码
- 端口映射

部署包中的 `Configure.json` 会自动更新为 Docker 环境配置。

## 配置

`Configure.json` 主要配置项：

- `MySQL_DBInfo` - 数据库连接信息
- `SheetFilter` - Excel Sheet 过滤规则
- `ExtractField` - 字段映射配置

## API 端点

- `POST /api/upload` - 上传文件
- `POST /api/process/start` - 启动处理
- `GET /api/process/status` - 查询状态
- `GET /api/history` - 获取历史记录
- `POST /api/service/restart` - 重启服务
- `GET /api/health` - 健康检查
