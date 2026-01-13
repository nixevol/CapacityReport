# CapacityReport - 容量报表处理程序

容量报表数据处理系统，支持 Excel/CSV 文件上传、数据提取、清洗和导入 MySQL 数据库。

## 技术栈

- **后端**: FastAPI + Uvicorn + Supervisor
- **前端**: 原生 JavaScript + HTML/CSS
- **数据库**: MySQL (PyMySQL + SQLAlchemy)
- **数据处理**: Pandas + OpenPyXL
- **部署**: Docker + Supervisor

## 系统架构

```mermaid
graph TB
    A[浏览器] -->|HTTP| B[FastAPI]
    B -->|静态文件| C[Static Files]
    B -->|API请求| D[业务逻辑层]
    D -->|数据处理| E[DataProcessor]
    D -->|数据管理| F[DatabaseManager]
    D -->|历史记录| G[HistoryManager]
    E -->|批量插入| H[MySQL]
    F -->|连接池| H
    I[Supervisor] -->|管理进程| J[Uvicorn]
    J -->|运行| B
```

## 核心模块

- `app/main.py` - FastAPI 应用入口，API 路由
- `app/processor.py` - 数据处理核心（ZIP解压、Excel转CSV、CSV导入）
- `app/database.py` - 数据库连接与批量插入
- `app/history.py` - 处理历史记录管理
- `app/config.py` - 配置管理

## 数据流程

```mermaid
flowchart TD
    A[上传文件] --> B{文件类型}
    B -->|ZIP| C[解压ZIP]
    B -->|Excel| D[Excel转CSV]
    B -->|CSV| E[直接处理]
    C --> D
    D --> F[字段映射]
    E --> F
    F --> G[数据清洗]
    G --> H[批量插入MySQL]
    H --> I[执行SQL脚本]
    I --> J[生成结果表]
```

## 上传处理时序

```mermaid
sequenceDiagram
    participant U as 用户
    participant F as 前端
    participant A as FastAPI
    participant P as DataProcessor
    participant D as MySQL

    U->>F: 选择文件上传
    F->>A: POST /api/upload
    A->>A: 保存文件到 cache/
    A->>F: 返回 task_id
    F->>A: POST /api/process/start
    A->>P: 启动处理任务
    P->>P: 解压ZIP/处理Excel
    P->>P: 读取CSV并清洗
    P->>D: 批量插入数据
    P->>D: 执行SQL脚本
    P->>A: 返回处理结果
    A->>F: 推送日志更新
    F->>U: 显示处理进度
```



## 部署

### Docker 部署

```bash
docker build -t capareport .
docker run -d --restart=always -p 9081:9081 capareport
```

### Windows 部署

```bash
# 安装依赖
pip install -r requirements.txt

# 启动服务（自动重启模式）
run.bat
```

### Linux 部署

```bash
# 使用 Supervisor
supervisord -c supervisord.conf
```

## 配置

配置文件: `Configure.json`

- `MySQL_DBInfo` - 数据库连接信息
- `SheetFilter` - Excel Sheet 过滤规则
- `ExtractField` - 字段映射配置

## API 端点

- `POST /api/upload` - 上传文件
- `POST /api/process/start` - 启动处理
- `POST /api/process/status` - 查询处理状态
- `POST /api/history` - 获取历史记录
- `POST /api/service/restart` - 重启服务
- `GET /api/service/status` - 服务状态

## 目录结构

```
CapaReport/
├── app/              # 应用代码
│   ├── main.py       # FastAPI 入口
│   ├── processor.py  # 数据处理
│   ├── database.py   # 数据库管理
│   ├── history.py    # 历史记录
│   └── config.py     # 配置管理
├── static/           # 前端静态文件
├── cache/            # 临时文件目录
├── Configure.json    # 配置文件
├── Dockerfile        # Docker 配置
└── supervisord.conf  # Supervisor 配置
```
