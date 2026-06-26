# Docker 一键编排（应用 + MySQL + sftpgo）

`docker-compose.yml` 编排三个服务，开箱即用、互相连通：

| 服务 | 容器 | 端口（宿主:容器） | 说明 |
|---|---|---|---|
| capacity-app | capacity-report-app | 9081:9081 | 应用（前端+后端） |
| capacity-mysql | capacity-mysql | 13306:3306 | MySQL 8（建 `CapacityReport` 与 `celldata` 两库） |
| sftpgo | capacity-sftpgo | 2022:2022（SFTP）、18080:8080（Web） | 文件服务，供应用拉取数据 |

## 构建并启动
```bash
# 1) 先构建前端（产出 frontend/dist，镜像会拷贝它）
cd ../frontend && npm ci && npm run build && cd ../packaging

# 2) 构建并启动
docker compose build
docker compose up -d
```

## 默认账号 / 连接（首次启动自动写入应用配置）
- MySQL：`root / gmcc123`，库 `CapacityReport`、`celldata`（应用内主机用服务名 `capacity-mysql`）。
- sftpgo：SFTP 用户 `capacity / capacity123`（home `/srv/sftpgo/data/capacity`）；Web 管理员 `admin / gmcc123`（http://localhost:18080）。
- 应用首次启动时，`entrypoint` 会按 compose 里的环境变量把 `Configure.json` 的「数据库/SFTP 连接」改写为容器服务（主机用服务名 `capacity-mysql` / `sftpgo`）。之后你在界面里的修改不会被覆盖。

## 放数据
通过 SFTP（localhost:2022，capacity/capacity123）或 Web（18080）把数据上传到 `capacity` 用户目录：
- 容量数据：上传到 `/CapacityReportData`（对应 `RemoteData.remote_dir`，结构 `4G/ 5G/ RJ/`）。
- CellData：上传到 `/网优日常优化数据文档/...`（对应 `CellData.scan_paths`）。
> 用 `test/make_test_data.py` 生成的小样本可直接传上来做测试。

## 数据卷（持久化）
- `capacity-data`：应用 `/data`（配置、脚本、特征库、历史、缓存）。
- `capacity-mysql-data`：MySQL 数据。
- `sftpgo-config` / `sftpgo-data`：sftpgo 状态与文件。

## 修改密码等
改 `docker-compose.yml` 里的环境变量与 `sftpgo/sftpgo-init.json`，重新 `up -d` 即可（首次播种后应用侧连接不再自动改写，需要的话删除 `capacity-data` 卷重置）。
