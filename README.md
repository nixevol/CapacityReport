# CapacityReport - 容量报表处理系统

CapacityReport 用于导入每周容量报表数据，按 `Configure.json` 的字段映射和 `ReportScript.sql` 的业务脚本完成数据清洗、入库、计算和结果表生成。系统支持本地上传处理，也支持从 FTP/SFTP 远程目录递归下载数据后自动处理。

## 双模式后端（自带 FTP/MySQL，或接入 Metrix 平台）

CapacityReport 是自包含应用，源与仓库各自可在「直连」与「Metrix 平台」之间独立选择，二者可任意组合，互不依赖——Metrix 在不在、CapacityReport 怎么跑都不影响：

- **数据源**（系统设置 → 数据源/仓库）：`SFTP` / `FTP`（直连，填服务器与账号密码）或 `Metrix 存储平台`（填平台地址 + Token + storage_id）。
- **数据仓库**：`MySQL`（直连，填主机/账号密码）或 `Metrix 数据库平台`（填平台地址 + Token + database_conn_id + 目标库）。
- **Metrix 连接**作为一种连接类型在「数据源/仓库」标签页配置：`base_url` + `API Token`（存配置，非环境变量）+ `storage_id`（存储平台）+ `database_conn_id`/`target_database`（数据库平台），存储/数据库平台共用同一地址与 Token。
- 直连模式走原生路径（自带 LOAD DATA 入库、单会话跑报表 SQL、本地查看/导出）；Metrix 模式下源走平台储存 API、仓库走平台导入 + `run-script(single_session)`，「数据管理」查看/导出自动**代理到 Metrix** 的 table-data/导出接口。
- 切换后端不改业务：字段映射、报表 SQL、自动调度、处理历史在两种模式下一致。

## 功能概览

- Excel/CSV/ZIP 数据导入与自动解压、转换、入库。
- FTP/SFTP 远程数据源配置、连接测试、远程下载并处理。
- 远程自动调度：按远程 ZIP 文件名日期检查目标自然周 7 天数据，就绪后自动下载并处理。
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
│  ├─ services/                 # 授权、远程下载等业务服务
│  ├─ utils/                    # 通用工具
│  ├─ main.py                   # 后端入口和前端托管
│  ├─ processor.py              # 数据处理主流程
│  ├─ database.py               # MySQL 访问
│  ├─ history.py                # 处理历史
│  └─ config.py                 # 配置读写
├─ frontend/                    # Vue 前端
├─ src-tauri/                   # Tauri 桌面壳
├─ scripts/                     # 运行 / 编译 Python 脚本（dev、run、tauri、docker、clean...）
├─ packaging/                   # Dockerfile、Compose、PyInstaller 配置
├─ dist/                        # 编译后的最终产物
├─ docs/project_context.md      # 项目维护记录
├─ Configure.json               # 应用配置
├─ ReportScript.sql             # SQL 处理脚本
├─ requirements.txt             # Python 依赖
└─ Dockerfile                   # 服务端容器镜像
```

## 运行与编译脚本

所有运行 / 编译都统一为 `scripts/` 下的 Python 脚本，直接用系统 Python 运行即可（`python scripts/xxx.py`）。脚本会**自动创建 `.venv` 并安装依赖**（使用标准库 `venv`，不依赖 uv），自动安装前端依赖；缺少 Node.js / Rust / Docker 时会给出安装引导。

前置要求：

- Python 3.10+（加入 PATH，作为创建 `.venv` 的基础解释器）
- Node.js 18+（前端构建）
- MySQL 8.0+（直连仓库模式）
- Rust 工具链（仅编译 Tauri 桌面版需要）
- Docker（仅编译 Docker 镜像需要）

| 脚本 | 用途 |
| --- | --- |
| `python scripts/dev.py` | 开发测试：后端自动重载 + 前端 Vite 热更新 |
| `python scripts/run.py` | 本地运行：构建前端（如缺失）并启动服务 |
| `python scripts/tauri_dev.py` | Tauri 桌面端测试运行 |
| `python scripts/build_server.py` | 编译 Server 便携版 |
| `python scripts/build_tauri.py` | 编译 Tauri 桌面版 |
| `python scripts/build_docker.py` | 编译 / 更新 Docker 镜像 |
| `python scripts/clean.py` | 清理缓存、`__pycache__`、编译产物、运行时临时数据 |
| `python scripts/gen_license_code.py` | 根据授权 key 生成激活码 |

### 开发测试

```powershell
python scripts/dev.py
```

启动后端（`http://127.0.0.1:9081`，自动重载）和前端（`http://127.0.0.1:5174`，Vite 热更新，`/api` 与 `/health` 代理到后端）。按 `Ctrl+C` 停止。

### 本地运行

```powershell
python scripts/run.py            # 默认 0.0.0.0:9081
python scripts/run.py --port 8080
python scripts/run.py --rebuild  # 强制重新构建前端
```

访问 `http://localhost:9081`。

### Server 便携版

```powershell
python scripts/build_server.py
python scripts/build_server.py --no-archive
```

输出：

```text
dist\server\CapacityReport-Server-windows-x64\
dist\server\CapacityReport-Server-windows-x64.zip
```

便携版内包含后端可执行文件、前端构建产物、`Configure.json`、`ReportScript.sql`、`CellData.sql`、`cache/`、`logs/` 和启动脚本（Windows 为 `run.bat`，Linux/macOS 为 `start.sh`）。默认监听端口 `9081`。便携版需在目标系统原生构建。

### Tauri 桌面版

```powershell
python scripts/build_tauri.py                   # 编译当前系统的桌面版
python scripts/build_tauri.py --platform windows
```

输出：`dist\desktop\` 下的安装包（Windows: `.msi` / `.exe`；Linux: `.deb` / `.AppImage`；macOS: `.dmg`）。

- 桌面版使用 Tauri 启动 Python sidecar，sidecar 监听 `127.0.0.1:9081`，运行数据写入系统 app data 目录。
- Windows 安装包内置 WebView2 离线安装器，适合无外网、未预装 WebView2 Runtime 的机器。
- Windows 默认安装到 `D:\Program Files\CapacityReport`，无 D 盘时回落系统盘。
- 首次安装运行 Rust/Tauri 时，脚本会在缺少 Tauri CLI 时自动 `cargo install tauri-cli --locked`。
- Tauri 无法可靠跨系统交叉编译：`--platform` 必须与当前系统一致，否则脚本会提示需在目标系统本机构建。

### Docker 镜像

```powershell
python scripts/build_docker.py            # 编译镜像并生成 dist/docker/ 离线部署包
python scripts/build_docker.py update     # 重新编译镜像并就地更新本机容器
python scripts/build_docker.py --no-save  # 编译但不导出 tar
```

离线部署包输出到 `dist\docker\`（`capacity-report-app-latest.tar`、`docker-compose.yml`、`Configure.json`、`ReportScript.sql`、`CellData.sql`、`mysql/`）。运行态数据落在 `/data` 数据卷，首次启动由 `docker/entrypoint.sh` 播种默认配置。

部署：

```bash
docker load -i dist/docker/capacity-report-app-latest.tar
docker compose -f dist/docker/docker-compose.yml up -d
```

访问 `http://localhost:9081`；停止：`docker compose -f dist/docker/docker-compose.yml down`。

### 清理

```powershell
python scripts/clean.py          # 清理缓存 / 编译产物 / 运行时临时数据
python scripts/clean.py --deep   # 额外清理 .venv 与 frontend/node_modules
```

## Linux / macOS

脚本跨平台通用，在对应系统原生环境执行相同命令即可：

```bash
python3 scripts/build_server.py
python3 scripts/build_tauri.py
python3 scripts/build_docker.py
```

Server 便携版与桌面版需在目标系统原生构建（Windows 包在 Windows、Linux 包在 Linux、macOS 包在 macOS）；Docker 镜像可在任意装有 Docker 的开发机构建。

## 配置说明

`Configure.json` 主要包含：

- `MySQL_DBInfo`：MySQL 连接配置。
- `RemoteData`：FTP/SFTP 远程数据源配置。
- `HistoryRetention`：处理历史保留配置。
- `SheetFilter`：Excel Sheet 过滤规则。
- `ExtractField`：字段映射配置。

`RemoteData.auto_scheduler` 用于远程自动调度：

```json
{
  "enabled": false,
  "check_interval_hours": 1,
  "expected_directories": ["4G/FDD", "4G/900", "5G/2.6", "5G/700"],
  "week_offset": 0
}
```

- `enabled`：是否启用自动调度。
- `check_interval_hours`：检查间隔，最小 1 小时。
- `expected_directories`：相对 `remote_dir` 的预期数据目录；为空时按远程 ZIP 实际所在目录检测。
- `week_offset`：`0` 表示上周自然周，`-1` 表示上上周。

自动调度开启后，系统会强制开启 `RemoteData.enabled` 和 `auto_delete_source`。调度器每轮先检查 `cache/auto_scheduler/ready.flag`；如果标识存在则直接触发远程下载并处理。没有标识时，会按 ZIP 文件名中的第一个时间戳判断每个目录是否覆盖目标自然周 7 天；全部就绪后写入标识，下一个检查周期再启动处理。处理成功并完成远程源文件清理后会删除标识；处理失败或源文件清理失败会保留标识，后续自动重试。

如果配置了 `expected_directories`，其中某个目录可访问但完全没有 ZIP 文件，会视为该目录已停推并跳过，不再阻塞其他目录；但所有目录都为空时不会触发自动处理。

无论手动上传还是远程下载，处理流程都会按文件名日期对每个目录只保留最近 7 天文件。文件名支持 `XXX_YYYYMMDDHHMM_YYYYMMDDHHMM` 和 `XXX_YYYYMMDDHHMM` 两类格式，数据日期始终取第一个时间戳。

登录密码保存在本地 `auth.ini`，该文件不应提交到版本库。

## 授权

授权到期日期保存在本地加密文件 `license.dat`，默认到期日由 `app/services/license.py` 中的 `DEFAULT_EXPIRES_ON` 控制，当前为 `2026-12-30`。处理任务不会读取系统日期，而是从任务目录 ZIP 文件名中的 `YYYYMMDDHHMM` 或 `YYYYMMDDHHMMSS` 时间戳取最大日期进行比对。登录后连续点击左上角品牌图标 8 次，可主动打开授权延期窗口。

## 常用接口

- `POST /api/login`：登录
- `POST /api/change-password`：修改密码
- `POST /api/upload`：上传文件
- `POST /api/remote/test`：测试 FTP/SFTP 连接
- `POST /api/remote/start`：远程下载并处理
- `GET /api/remote/scheduler/status`：查询远程自动调度状态
- `POST /api/remote/scheduler/trigger`：手动触发一次自动调度检查
- `POST /api/process/start`：启动本地处理
- `POST /api/process/status`：查询处理状态
- `GET /api/license/status`：查询授权状态
- `POST /api/license/activate`：提交激活码并顺延授权期限
- `GET /api/history`：处理历史
- `POST /api/history/download`：下载历史原始数据
- `GET /health`：健康检查

## 维护注意事项

- 不要提交 `auth.ini`、`license.dat`、`cache/`、`logs/`、`dist/`、`frontend/dist/`、`src-tauri/target/`、`src-tauri/binaries/`。
- `src-tauri/gen/schemas/` 需要保留并提交，`src-tauri/capabilities/default.json` 的 JSON schema 会引用它。
- `ReportScript.sql` 是业务处理链路的一部分，修改前需要确认 SQL 语义和字段映射兼容。
