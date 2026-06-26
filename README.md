# CapacityReport · 容量报表处理系统

CapacityReport 用于处理每周的网络容量报表数据：从本地上传或 FTP/SFTP 远程目录获取 Excel/CSV/ZIP 数据，按字段映射清洗、入库到 MySQL，再执行业务 SQL 生成 4G/5G 容量结果表，并通过容量看板做高负荷小区分析。

## 技术栈

- 后端：Python + FastAPI + Uvicorn
- 前端：Vue 3 + TypeScript + Vite + Naive UI
- 桌面端：Tauri 2（Rust）+ Python sidecar
- 数据库：MySQL 8.0+
- 数据处理：Pandas + OpenPyXL；图表：ECharts；SQL 编辑器：Monaco Editor

## 功能模块

系统左侧导航分为 6 个模块：

| 模块 | 作用 |
| --- | --- |
| 数据处理 | 本地上传或远程下载数据，清洗后入库并执行报表 SQL |
| 容量看板 | 4G/5G 高负荷小区分析大屏（汇总、图表、问题清单、单小区详情） |
| 处理历史 | 查看历史任务、处理日志，浏览/下载历史原始数据 |
| 数据管理 | 浏览、编辑、导入导出数据库表，在线执行 SQL |
| 脚本编辑 | 在线编辑并执行容量报表 SQL / CellData SQL |
| 系统设置 | 数据库、远程数据源、字段映射、自动调度等配置 |

## 初次运行

- 默认登录账号：用户名 `root`，密码 `Capacity`（登录后可在「系统设置 → 修改密码」中修改）。
- 系统需要配套使用：
  - **一个 FTP/SFTP 数据源**：存放每周容量报表数据，在「系统设置 → 远程数据源」中配置，可手动下载或开启自动调度。
  - **一个 MySQL 8.0+ 数据库**：作为数据仓库，在「系统设置 → 数据库」中配置连接信息。
- 启动后访问 `http://localhost:9081`。
- 也可以直接在「数据处理」页拖拽上传数据文件，无需远程数据源。

详细的 Web 端操作方法与注意事项见 [使用说明 USAGE.md](USAGE.md)。

## 运行与编译

所有运行 / 编译都统一为 `scripts/` 下的 Python 脚本，直接用系统 Python 运行即可。脚本会自动创建 `.venv` 并安装依赖、自动安装前端依赖；缺少 Node.js / Rust / Docker 时会给出安装引导。

环境要求：

- Python 3.10+（加入 PATH）
- Node.js 18+
- MySQL 8.0+
- Rust 工具链（仅编译 Tauri 桌面版时需要）
- Docker（仅编译镜像时需要）

| 命令 | 用途 |
| --- | --- |
| `python scripts/dev.py` | 开发模式：后端自动重载 + 前端热更新 |
| `python scripts/run.py` | 本地运行：构建前端（如缺失）并启动服务 |
| `python scripts/dev_tauri.py` | Tauri 桌面端测试运行 |
| `python scripts/build_server.py` | 编译 Server 便携版 |
| `python scripts/build_tauri.py` | 编译 Tauri 桌面版 |
| `python scripts/build_docker.py` | 编译 / 更新 Docker 镜像 |
| `python scripts/clean.py` | 清理缓存与编译产物 |

### 本地运行

```bash
python scripts/run.py            # 默认 0.0.0.0:9081
python scripts/run.py --port 8080
```

### 开发模式

```bash
python scripts/dev.py
```

后端 `http://127.0.0.1:9081`（自动重载），前端 `http://127.0.0.1:5174`（Vite 热更新）。

### 编译发布版

```bash
python scripts/build_server.py            # Server 便携版（dist/server/）
python scripts/build_tauri.py             # Tauri 桌面版（dist/desktop/）
python scripts/build_docker.py            # Docker 镜像 + 离线包（dist/docker/）
```

桌面版需在目标系统本机构建（Windows 包在 Windows、Linux 包在 Linux、macOS 包在 macOS）；Windows 安装包内置 WebView2 离线安装器。Docker 离线包部署：

```bash
docker load -i dist/docker/capacity-report-app-latest.tar
docker compose -f dist/docker/docker-compose.yml up -d
```

## 文档

- [使用说明 USAGE.md](USAGE.md)：Web 端各功能的操作方法与注意事项。
- [开发文档 DEVELOPMENT.md](DEVELOPMENT.md)：技术栈、目录结构与「功能 ↔ 代码」对照。

开发文档锚点：

- [技术栈与主要库](DEVELOPMENT.md#技术栈与主要库)
- [目录结构](DEVELOPMENT.md#目录结构)
- [功能与代码对照](DEVELOPMENT.md#功能与代码对照)
  - [数据处理](DEVELOPMENT.md#数据处理)
  - [容量看板](DEVELOPMENT.md#容量看板)
  - [处理历史](DEVELOPMENT.md#处理历史)
  - [数据管理](DEVELOPMENT.md#数据管理)
  - [脚本编辑](DEVELOPMENT.md#脚本编辑)
  - [系统设置](DEVELOPMENT.md#系统设置)
