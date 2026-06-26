# Docker 编排：一键构建并运行整套系统（应用 + MySQL + sftpgo）

`docker-compose.yml` 把整套系统编排为三个互相连通的服务，开箱即用。

| 服务 | 容器名 | 端口（宿主:容器） | 说明 |
| --- | --- | --- | --- |
| capacity-app | capacity-report-app | 9081:9081 | 应用（前端 + 后端），数据落在 `/data` 卷 |
| capacity-mysql | capacity-mysql | 13306:3306 | MySQL 8，自动建 `CapacityReport` 与 `celldata` 两库 |
| sftpgo | capacity-sftpgo | 2022:2022（SFTP）、18080:8080（Web） | 文件服务，供应用拉取数据 |

> 应用镜像 `capacity-report-app:latest` 由本仓库根的 `Dockerfile` 构建；MySQL、sftpgo 为公共镜像。

---

## 前置要求

- 已安装 Docker（含 Docker Compose v2，命令为 `docker compose`）。
- 构建应用镜像需要先产出前端 `frontend/dist`（下方步骤会做）。
- 联网构建需要能拉取 `python:3.13.11-slim`、`mysql:8.0.44`、`drakkan/sftpgo:v2.7.1`；
  内网离线见「方式 B」。

---

## 方式 A：联网机器，一键构建并启动

```bash
# 1) 构建前端（产出 frontend/dist，镜像会拷贝它）
cd ../frontend
npm ci && npm run build
cd ../packaging

# 2) 构建应用镜像并启动整套系统
docker compose build
docker compose up -d

# 3) 查看状态 / 日志
docker compose ps
docker compose logs -f capacity-app
```

启动后访问 `http://localhost:9081`（默认登录 `root` / `Capacity`）。

> 也可以用脚本一步构建并导出离线包：在仓库根执行 `python scripts/build_docker.py`，
> 产物在 `dist/docker/`（含 `capacity-report-app-latest.tar` + `docker-compose.yml` + `mysql/` + `sftpgo/` + 默认脚本）。

---

## 方式 B：内网离线部署（无外网）

在有网机器准备好以下文件，拷贝到内网机器：

1. **基础/公共镜像**（python、mysql、sftpgo）——可用离线镜像目录方案：
   - 有网机器：`docker pull` 三个镜像后 `docker save -o xxx.tar`，连同导入脚本放一个目录。
   - 内网机器：在该目录执行 `python load_images.py` 逐个 `docker load -i ./xxx.tar`。
   - （示例：本项目已在 `F:\CR\env\images` 准备了 `mysql_8.0.44.tar`、`sftpgo_v2.7.1.tar`、`python_3.13.11-slim.tar` 与 `load_images.py`。）
2. **应用镜像**：在有网机器 `docker compose build` 后
   `docker save capacity-report-app:latest -o capacity-report-app.tar`，拷到内网 `docker load -i ./capacity-report-app.tar`。
   - 或直接用 `python scripts/build_docker.py` 生成 `dist/docker/` 整包带走。
3. **编排文件**：本目录的 `docker-compose.yml` + `mysql/` + `sftpgo/`。

内网机器导入镜像后，在编排文件目录执行：

```bash
docker compose up -d        # 镜像已在本地，不会联网拉取
```

> 若内网机器**不便构建**应用镜像，务必走「先在有网机器 build 出 `capacity-report-app:latest` 再 save」，
> 这样内网仅需 `docker load` + `docker compose up -d`，无需 python 基础镜像与构建。

---

## 默认账号 / 连接

| 项 | 值 |
| --- | --- |
| 应用登录 | `root` / `Capacity` |
| MySQL | `root` / `gmcc123`，库 `CapacityReport`、`celldata`（容器内主机名 `capacity-mysql`） |
| SFTP 用户 | `capacity` / `capacity123`（home `/srv/sftpgo/data/capacity`） |
| sftpgo Web | `admin` / `gmcc123`（http://localhost:18080） |

应用**首次启动**时，`entrypoint` 会按 `docker-compose.yml` 里的环境变量把 `Configure.json` 的
「数据库 / SFTP 连接」自动改写为容器服务（主机名用 `capacity-mysql` / `sftpgo`）；
之后你在界面里的修改不会被覆盖。要改默认密码等，编辑 compose 的环境变量与 `sftpgo/sftpgo-init.json`。

---

## 上传数据

通过 SFTP（`localhost:2022`，`capacity`/`capacity123`）或 sftpgo Web（`:18080`）上传到 `capacity` 用户目录：

- 容量数据 → `/CapacityReportData`（对应 `RemoteData.remote_dir`，结构 `4G/ 5G/ RJ/`）。
- CellData → `/网优日常优化数据文档/...`（对应 `CellData.scan_paths`）。

> 用仓库 `test/make_test_data.py` 生成的小样本可直接传上来做快速测试。
> 上传后在「数据处理」页执行处理；首次会自动建表（`db_init/` 前置检查）。

---

## 数据卷（持久化）

| 卷 | 内容 |
| --- | --- |
| `capacity-data` | 应用 `/data`：Configure.json、ReportScript.sql、CellData.sql、db_init、历史、缓存 |
| `capacity-mysql-data` | MySQL 数据 |
| `sftpgo-config` / `sftpgo-data` | sftpgo 状态与上传的文件 |

---

## 常用运维

```bash
docker compose ps                       # 状态
docker compose logs -f capacity-app     # 应用日志
docker compose restart capacity-app     # 重启应用
docker compose down                     # 停止（保留数据卷）
docker compose down -v                  # 停止并删除数据卷（彻底重置，慎用）

# 改了代码 / 前端后更新应用：
cd ../frontend && npm run build && cd ../packaging
docker compose build capacity-app && docker compose up -d capacity-app
```

> 重置应用侧连接：`Configure.json` 仅在首次播种时按环境变量初始化；如需重新按 env 生成，
> 删除 `capacity-data` 卷（`docker volume rm packaging_capacity-data`）后重新 `up -d`。
