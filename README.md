# CapacityReport - 容量报表处理系统

CapacityReport 用于每周导入 Excel/CSV 数据，按 `Configure.json` 与 `ReportScript.sql` 完成清洗、入库和报表处理。系统面向内网运行，后端由 FastAPI 提供接口，前端由 Vue 3 构建后交给 FastAPI 托管。

## 技术栈

- 后端：FastAPI + Uvicorn + Supervisor
- 前端：Vue 3 + TypeScript + Vite + Naive UI
- 数据库：MySQL 8.0+，通过 PyMySQL + SQLAlchemy 访问
- 数据处理：Pandas + OpenPyXL
- 部署：Docker + Docker Compose

## 目录结构

```text
CapaReport/
├── app/
│   ├── api/routers/        # FastAPI 路由模块
│   ├── services/           # 运行时服务能力
│   ├── utils/              # 文件和通用工具
│   ├── main.py             # FastAPI 入口和前端托管
│   ├── auth.py             # 登录、密码和 Token
│   ├── state.py            # 运行期共享状态
│   ├── processor.py        # 数据处理主流程
│   ├── database.py         # 数据库访问
│   ├── history.py          # 历史记录
│   └── config.py           # 配置读写
├── frontend/
│   ├── src/                # Vue 3 + TypeScript 源码
│   ├── package.json
│   └── vite.config.ts
├── build/                  # Docker 与离线部署构建脚本
├── docs/project_context.md # 项目上下文记录
├── Configure.json          # 应用配置
├── ReportScript.sql        # SQL 处理脚本
├── requirements.txt        # Python 依赖
├── run.bat                 # Windows 本地启动脚本
└── supervisord.conf        # 容器内进程管理配置
```

## 本地运行

前置要求：

- Windows 10
- Python >= 3.10，项目虚拟环境由 `uv` 创建
- Node.js，建议使用当前 LTS 或更新版本
- MySQL >= 8.0

安装后端依赖：

```powershell
uv pip install -r requirements.txt
```

安装并构建前端：

```powershell
cd frontend
npm install
npm run build
cd ..
```

启动服务：

```powershell
.\run.bat
```

访问地址：

```text
新版前端：http://localhost:9081
旧版前端：http://localhost:9082
```

开发前端时可运行：

```powershell
cd frontend
npm run dev
```

Vite 会把 `/api` 和 `/health` 代理到 `http://localhost:9081`。

## 配置

`Configure.json` 主要包含：

- `MySQL_DBInfo`：MySQL 连接信息
- `RemoteData`：FTP/SFTP 远程数据源配置，用于递归下载目录后自动处理，可选择处理成功后删除远程源文件
- `SheetFilter`：Excel Sheet 过滤规则
- `ExtractField`：字段抽取映射配置

登录账号密码保存在本地 `auth.ini`，首次运行会自动创建默认配置。`auth.ini` 已被 `.gitignore` 忽略。

## Docker 构建与部署

离线部署包由 `build/build.py` 生成：

```powershell
python build/build.py
```

脚本提供两种构建：

- `1`：完整部署包，包含 MySQL 镜像和应用镜像
- `2`：更新包，只包含应用镜像

Docker 镜像构建采用多阶段流程：先在 Node 阶段执行前端构建，再把 `frontend/dist` 复制到 Python 运行镜像内。

## 主要接口

- `POST /api/login`：登录
- `POST /api/change-password`：修改密码
- `POST /api/upload`：上传文件
- `POST /api/remote/test`：测试 FTP/SFTP 远程数据源
- `POST /api/remote/start`：从远程目录下载数据并自动启动处理
- `POST /api/process/start`：启动处理
- `POST /api/process/status`：查询处理状态
- `GET /api/history`：历史记录
- `POST /api/service/restart`：重启服务
- `GET /health`：健康检查
