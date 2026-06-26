# CapacityReport 开发文档

面向二次开发者，介绍项目实际用到的技术栈、目录结构，以及导航栏每个功能对应的代码文件，方便快速定位要修改的位置。

## 技术栈与主要库

### 后端（Python）

| 库 | 用途 |
| --- | --- |
| fastapi / uvicorn | Web 框架与 ASGI 服务器 |
| python-multipart | 文件上传表单解析 |
| pandas / openpyxl | Excel/CSV 数据读取与处理 |
| chardet | CSV 编码探测 |
| pymysql | 直连 MySQL 读写 |
| cryptography | 本地授权文件加密 |
| paramiko | SFTP 远程下载 |
| requests | Metrix 平台 API 客户端（可选模式） |

### 前端（Vue 3）

| 库 | 用途 |
| --- | --- |
| vue / vue-router | 框架与路由 |
| naive-ui | UI 组件库 |
| @vicons/ionicons5 | 图标 |
| echarts | 容量看板图表 |
| monaco-editor | 脚本编辑页的 SQL 编辑器 |
| @tauri-apps/api | 桌面端与原生能力交互 |
| vite / vue-tsc / typescript | 构建与类型检查 |
| unplugin-auto-import / unplugin-vue-components | Naive UI 组件按需自动导入 |

### 桌面端（Tauri 2 / Rust）

| 库 | 用途 |
| --- | --- |
| tauri | 桌面应用框架 |
| tauri-plugin-shell | 启动并管理后端 sidecar 进程 |
| tauri-plugin-dialog | 文件保存对话框 |
| reqwest | 下载文件到本地 |
| sysinfo | 跨平台进程检测与清理 |
| open | 调用系统文件管理器打开目录 |
| serde | 序列化 |

## 目录结构

```text
CapacityReport/
├─ app/                     # 后端（FastAPI）
│  ├─ main.py               # 入口：创建应用、鉴权中间件、注册路由、托管前端
│  ├─ state.py              # 运行时共享状态（配置、历史、任务锁、上传会话）
│  ├─ config.py             # 配置读写（AppConfig 与各配置块）
│  ├─ auth.py               # 登录账号（auth.ini）、JWT、密码修改
│  ├─ db_init.py            # 启动时确保必要数据表存在
│  ├─ database.py           # DatabaseManager：直连 MySQL 表操作
│  ├─ warehouse.py          # make_warehouse：按仓库类型返回直连或 Metrix 仓库
│  ├─ processor.py          # DataProcessor：解压/转换/入库/执行报表 SQL；ProcessLogger
│  ├─ history.py            # HistoryManager：处理历史记录与日志
│  ├─ api/routers/          # 各业务接口（按模块拆分，见下表）
│  ├─ services/             # 业务服务（远程下载、调度、CellData、授权、Metrix 等）
│  └─ utils/                # 通用工具（文件、文件名日期解析）
├─ frontend/                # 前端（Vue 3 + Vite）
│  └─ src/
│     ├─ AppShell.vue       # 整体框架：登录、侧边导航、顶栏、主题切换
│     ├─ App.vue / main.ts  # 应用根与入口
│     ├─ router.ts          # 路由表（6 个功能页）
│     ├─ types.ts           # 前端类型定义
│     ├─ api/client.ts      # 请求封装（token、错误处理、下载）
│     ├─ components/        # 各功能页面与公共组件
│     └─ composables/       # 可复用逻辑（页头、主题、剪贴板、日志等）
├─ src-tauri/               # Tauri 桌面壳（Rust）
│  ├─ src/main.rs           # 启动/停止 Python sidecar、下载、打开目录
│  └─ tauri.conf.json       # 桌面打包配置（WebView2、NSIS 等）
├─ scripts/                 # 运行/编译 Python 脚本
├─ packaging/               # docker-compose、PyInstaller 配置、MySQL 初始化
├─ docker/entrypoint.sh     # 容器启动脚本
├─ docs/                    # 文档（本文件、项目维护记录）
├─ Configure.json           # 应用配置
├─ ReportScript.sql         # 容量报表处理 SQL
├─ CellData.sql             # CellData 处理 SQL
├─ Dockerfile               # 服务端镜像
└─ requirements.txt         # Python 依赖
```

运行时数据（不进版本库）：`cache/`（任务工作目录、历史记录 `history.json`）、`logs/`、`auth.ini`（账号）、`license.dat`（授权）。

## 功能与代码对照

后端接口按模块拆分在 `app/api/routers/`，前端页面在 `frontend/src/components/`。下面按导航栏 6 个功能逐一说明涉及的代码文件。

公共代码（多数功能都会用到）：

- 前端框架与导航：`frontend/src/AppShell.vue`、`router.ts`、`api/client.ts`、`composables/`
- 后端入口与共享：`app/main.py`、`app/state.py`、`app/config.py`、`app/api/routers/task_runtime.py`（任务阶段、授权日志、历史保留清理）

### 数据处理

页面路由 `/upload`。负责本地上传或远程下载数据，清洗入库并执行报表 SQL；若启用 CellData 数据源，会在容量处理前先更新 CellData。

| 类型 | 文件 | 职责 |
| --- | --- | --- |
| 前端 | `frontend/src/components/FileWorkflow.vue` | 上传/远程下载入口、处理进度与日志、CellData 卡片 |
| 接口 | `app/api/routers/upload.py` | 创建上传会话、接收文件 |
| 接口 | `app/api/routers/tasks.py` | 任务锁、启动容量处理、查询状态 |
| 接口 | `app/api/routers/remote.py` | 远程下载并处理、连接测试、自动调度状态/触发 |
| 接口 | `app/api/routers/cell_data.py` | CellData 单独处理（远程刷新 / 本地上传） |
| 服务 | `app/processor.py` | 直连 MySQL：解压、Excel/CSV 转换、入库、执行 `ReportScript.sql` |
| 服务 | `app/services/remote_download.py` | FTP/SFTP 远程下载 |
| 服务 | `app/services/auto_scheduler.py` | 后台自动调度（按目标周检查远程数据就绪） |
| 服务 | `app/services/cell_data.py` | CellData 解析入库、执行 `CellData.sql`、跨库复制 |
| 服务 | `app/services/license.py` | 按数据日期校验授权期限 |
| 服务 | `app/services/csv_processor.py`、`pipeline.py`、`platform.py` | Metrix 平台模式下的预处理与平台导入（可选） |
| 工具 | `app/utils/file_dates.py` | 文件名日期解析、按目录筛选最近 7 天文件 |

### 容量看板

页面路由 `/dashboard`。基于主仓库的 4G/5G 结果表做高负荷分析。

| 类型 | 文件 | 职责 |
| --- | --- | --- |
| 前端 | `frontend/src/components/CapacityDashboard.vue` | 看板大屏：汇总卡片、图表、问题小区清单、详情抽屉 |
| 前端 | `frontend/src/components/EChart.vue` | ECharts 封装组件 |
| 接口 | `app/api/routers/dashboard.py` | 状态、汇总概览、问题小区清单、单小区详情、清单导出 |
| 依赖 | `app/warehouse.py` | 读取主仓库结果表 |

### 处理历史

页面路由 `/history`。查看历史任务、日志，浏览/下载历史原始数据。

| 类型 | 文件 | 职责 |
| --- | --- | --- |
| 前端 | `frontend/src/components/HistoryPanel.vue` | 历史列表、详情、日志、文件浏览与下载 |
| 接口 | `app/api/routers/history.py` | 历史记录、日志、占用计算、文件浏览/下载、删除 |
| 服务 | `app/history.py` | HistoryManager：记录存于 `cache/history.json` 与 `cache/<task_id>` |

### 数据管理

页面路由 `/database`。浏览、编辑、导入导出数据库表，可切换主数据库与 CellData 数据库。

| 类型 | 文件 | 职责 |
| --- | --- | --- |
| 前端 | `frontend/src/components/DatabasePanel.vue` | 表列表、表数据分页、行编辑/删除、导入导出、执行 SQL |
| 接口 | `app/api/routers/database.py` | 表列表/结构/分页、清空/删除、行增改删、CSV/XLSX 导出、模板/导入、执行 SQL（`database_source` 选主库或 CellData 库） |
| 服务 | `app/database.py` | DatabaseManager：直连 MySQL 表操作 |
| 服务 | `app/warehouse.py` | 直连或 Metrix 仓库的统一访问 |

### 脚本编辑

页面路由 `/script`。在线编辑并执行报表 SQL 与 CellData SQL。

| 类型 | 文件 | 职责 |
| --- | --- | --- |
| 前端 | `frontend/src/components/ScriptPanel.vue` | Monaco SQL 编辑器、保存、运行、切换脚本类型 |
| 接口 | `app/api/routers/script.py` | 读取/保存/执行（`report` → `ReportScript.sql`，`celldata` → `CellData.sql`） |
| 服务 | `app/processor.py`、`app/services/cell_data.py`、`app/services/pipeline.py` | 在对应数据库上下文执行脚本 |

### 系统设置

页面路由 `/settings`。配置数据库、远程数据源、字段映射、自动调度等，并提供修改密码。

| 类型 | 文件 | 职责 |
| --- | --- | --- |
| 前端 | `frontend/src/components/SettingsPanel.vue` | 各类配置表单、连接测试、配置导入导出 |
| 前端 | `frontend/src/components/LicenseActivationModal.vue` | 授权延期窗口、Metrix 平台开关（连点品牌图标 8 次打开） |
| 接口 | `app/api/routers/config.py` | 各配置块读写、配置上传/下载、MySQL/远程/CellData 连接测试、CellData 规则校验 |
| 接口 | `app/api/routers/auth.py` | 登录、修改密码 |
| 接口 | `app/api/routers/license.py` | 授权状态查询与激活 |
| 服务 | `app/config.py` | AppConfig 及各配置块的解析与保存 |
| 服务 | `app/auth.py` | 账号（`auth.ini`）、JWT |
| 服务 | `app/services/license.py` | 授权加密文件读写、激活码校验 |
