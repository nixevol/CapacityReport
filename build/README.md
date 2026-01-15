# 构建脚本

## 使用方法

在项目根目录运行：

```bash
python build/build.py
```

选择构建类型：
- `1` - 完整部署包（MySQL + 应用）
- `2` - 更新包（仅应用）

## 输出

构建完成后在 `dist/` 目录生成：
- `capacity-report-full.tar.gz` - 完整部署包
- `capacity-report-update.tar.gz` - 更新包

## 部署包内容

**完整部署包**：
- `images/capacity-images.tar` - Docker 镜像
- `docker-compose.yml` - 编排文件
- `deploy.sh` - 部署脚本
- `Configure.json` - 配置文件（已更新为 Docker 环境）
- `ReportScript.sql` - SQL 脚本
- `mysql/` - MySQL 配置

**更新包**：
- `images/capacity-app-update.tar` - 应用镜像
- `docker-compose.yml` - 编排文件
- `update.sh` - 更新脚本

## 部署

**完整部署**：
```bash
tar -xzf capacity-report-full.tar.gz
cd capacity-report-full
sh deploy.sh
```

**更新应用**：
```bash
tar -xzf capacity-report-update.tar.gz
cd capacity-report-update
sh update.sh
```

## 配置

所有配置在 `build/build.py` 文件头部：
- 默认镜像版本
- 版本要求范围
- 数据库账号密码
- 端口映射
