# CapacityReport - 容量报表处理系统

CapacityReport 用于导入每周容量报表数据，按 `Configure.json` 的字段映射和 `ReportScript.sql` 的业务脚本完成数据清洗、入库、计算和结果表生成。系统支持本地上传处理，也支持从 FTP/SFTP 远程目录递归下载数据后自动处理。

## 功能概览

- Excel/CSV/ZIP 数据导入与自动解压、转换、入库。
- FTP/SFTP 远程数据源配置、连接测试、远程下载并处理。
- MySQL 数据表查看、清空、删除、CSV/XLSX 导出。
- SQL 脚本在线查看、保存和执行。
- 处理历史、日志查看、历史原始数据打包下载。
- 按 ZIP 文件名数据日期校验本地授权期限，过期后可输入激活码顺延。
- 系统设置：数据库、远程数据源、Sheet 过滤、字段映射、历史保留、密码修改。
- 发行形态：Server Portable、Tauri 桌面版、Docker 服务端版。

## 技术栈

- 后端：FastAPI + Uvicorn
- 前端：Vue 3 + TypeScript + Vite + Naive UI
- 桌面端：Tauri 2 + Python sidecar
- 数据库：MySQL 8.0+
- 数据处理：Pandas + OpenPyXL
- 打包：PyInstaller、Docker、Docker Compose

## 目录结构

```text
CapaReport/
├─ app/                         # FastAPI 后端源码
│  ├─ api/routers/              # API 路由
│  ├─ services/                 # 运行时和远程下载服务
│  ├─ utils/                    # 通用工具
│  ├─ main.py                   # 后端入口和前端托管
│  ├─ processor.py              # 数据处理主流程
│  ├─ database.py               # MySQL 访问
│  ├─ history.py                # 处理历史
│  └─ config.py                 # 配置读写
├─ frontend/                    # Vue 前端
├─ src-tauri/                   # Tauri 桌面壳
├─ scripts/                     # 一键构建脚本
├─ packaging/                   # Docker、Compose、PyInstaller 配置
├─ dist/                        # 一键构建后的最终产物
├─ docs/project_context.md      # 项目维护记录
├─ Configure.json               # 应用配置
├─ ReportScript.sql             # SQL 处理脚本
├─ requirements.txt             # Python 依赖
└─ run.bat                      # Windows 本地启动脚本
```

## 本地运行

前置要求：

- Windows 10/11
- Python 与 `uv`
- Node.js
- MySQL 8.0+

安装后端依赖：

```powershell
uv venv
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
http://localhost:9081
```

前端开发模式：

```powershell
cd frontend
npm run dev
```

Vite 会把 `/api` 和 `/health` 代理到 `http://localhost:9081`。

## 一键构建

Windows 在项目根目录执行：

```bat
scripts\build.bat -?
```

可用目标：

```bat
scripts\build.bat server
scripts\build.bat desktop
scripts\build.bat docker
scripts\build.bat all
```

常用参数：

```bat
scripts\build.bat server -NoArchive
scripts\build.bat all -Clean
scripts\build.bat docker -SkipDockerBuild
scripts\build.bat all -SkipDesktopBuild
```

构建完成后只保留 `dist/` 下的最终产物；`dist/.tmp`、`frontend/dist`、`src-tauri/target`、`src-tauri/binaries` 等中间产物会自动清理。

### Server Portable

```bat
scripts\build.bat server
```

输出：

```text
dist\server\CapacityReport-Server-windows-x64\
dist\server\CapacityReport-Server-windows-x64.zip
```

便携版内包含后端可执行文件、前端构建产物、`Configure.json`、`ReportScript.sql`、`cache/`、`logs/` 和启动脚本。默认监听端口为 `9081`。

### 桌面版

```bat
scripts\build.bat desktop
```

输出：

```text
dist\desktop\*.msi
dist\desktop\*-setup.exe
```

桌面版使用 Tauri 启动 Python sidecar。sidecar 默认监听 `127.0.0.1:19082`，运行数据写入系统 app data 目录，不写入安装目录。
首次启动会把安装包内置的 `Configure.json` 和 `ReportScript.sql` 复制到运行数据目录；Windows 下通常是 `%APPDATA%\com.nixevol.capacityreport\`。安装目录中的 `_up_` 只是 Tauri 打包资源目录，程序运行时不会直接编辑它。

构建桌面版需要 Rust 和 Tauri CLI。脚本会在缺少 Tauri CLI 时自动执行：

```bat
cargo install tauri-cli --locked
```

### Docker 版

```bat
scripts\build.bat docker
```

输出：

```text
capacity-report-app:latest
dist\docker\capacity-report-app-latest.tar
dist\docker\docker-compose.yml
dist\docker\Configure.json
dist\docker\ReportScript.sql
```

启动：

```bat
docker load -i dist\docker\capacity-report-app-latest.tar
docker compose -f dist\docker\docker-compose.yml up -d
```

访问：

```text
http://localhost:19081
```

停止：

```bat
docker compose -f dist\docker\docker-compose.yml down
```

## Linux / macOS 构建

在对应系统原生环境执行：

```bash
sh scripts/build.sh server
sh scripts/build.sh desktop
sh scripts/build.sh docker
sh scripts/build.sh all
```

Server Portable 和桌面版需要在目标系统原生构建：Windows 包在 Windows 构建，Linux 包在 Linux 构建，macOS 包在 macOS 构建。Docker 镜像可以在 Windows 开发机上构建。

## 配置说明

`Configure.json` 主要包含：

- `MySQL_DBInfo`：MySQL 连接配置。
- `RemoteData`：FTP/SFTP 远程数据源配置。
- `HistoryRetention`：处理历史保留配置。
- `SheetFilter`：Excel Sheet 过滤规则。
- `ExtractField`：字段映射配置。

登录密码保存在本地 `auth.ini`，该文件不应提交到版本库。

授权到期日期保存在本地加密文件 `license.dat`，默认到期日为 `2026-06-20`。处理任务不会读取系统日期，而是从任务目录 ZIP 文件名中的 `YYYYMMDDHHMM` 或 `YYYYMMDDHHMMSS` 时间戳取最大日期进行比对。

## 常用接口

- `POST /api/login`：登录
- `POST /api/change-password`：修改密码
- `POST /api/upload`：上传文件
- `POST /api/remote/test`：测试 FTP/SFTP 连接
- `POST /api/remote/start`：远程下载并处理
- `POST /api/process/start`：启动本地处理
- `POST /api/process/status`：查询处理状态
- `GET /api/license/status`：查询授权状态
- `POST /api/license/activate`：提交激活码并顺延授权期限
- `GET /api/history`：处理历史
- `POST /api/history/download`：下载历史原始数据
- `POST /api/service/restart`：重启服务
- `GET /health`：健康检查

## 维护注意事项

- 不要提交 `auth.ini`、`license.dat`、`cache/`、`logs/`、`dist/`、`frontend/dist/`、`src-tauri/target/`、`src-tauri/binaries/`。
- `src-tauri/gen/schemas/` 需要保留并提交，`src-tauri/capabilities/default.json` 的 JSON schema 会引用它。
- `ReportScript.sql` 是业务处理链路的一部分，修改前需要确认 SQL 语义和字段映射兼容。
