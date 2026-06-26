"""Docker 镜像编译 / 更新脚本（基于根目录 Dockerfile + docker/entrypoint.sh）。

用法：
    python scripts/build_docker.py            # 编译镜像并生成可部署离线包（dist/docker/）
    python scripts/build_docker.py update      # 重新编译镜像并就地更新本机运行的容器
    python scripts/build_docker.py --no-save   # 编译但不导出 tar（本机调试更快）

镜像 tag：capacity-report-app:latest。镜像内运行态数据落在 /data 数据卷，
首次启动由 docker/entrypoint.sh 播种默认 Configure.json / ReportScript.sql。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

IMAGE_TAG = "capacity-report-app:latest"
DOCKERFILE = _env.ROOT / "Dockerfile"
COMPOSE_FILE = _env.PACKAGING_DIR / "docker-compose.yml"
BUNDLE_FILES = ["Configure.json", "ReportScript.sql", "CellData.sql"]


def build_image() -> None:
    _env.ensure_docker()
    _env.build_frontend()
    _env.step("构建 Docker 镜像")
    _env.run(
        ["docker", "build", "--progress=plain", "-f", str(DOCKERFILE), "-t", IMAGE_TAG, "."],
        cwd=_env.ROOT,
    )


def make_bundle(save_tar: bool) -> Path:
    out_dir = _env.DIST_DIR / "docker"
    _env.remove_path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "cache").mkdir(exist_ok=True)
    (out_dir / "logs").mkdir(exist_ok=True)

    shutil.copy2(COMPOSE_FILE, out_dir / "docker-compose.yml")
    shutil.copytree(_env.PACKAGING_DIR / "mysql", out_dir / "mysql", dirs_exist_ok=True)
    for name in BUNDLE_FILES:
        src = _env.ROOT / name
        if src.exists():
            shutil.copy2(src, out_dir / name)

    if save_tar:
        _env.step("导出镜像 tar")
        _env.run(["docker", "save", "-o", str(out_dir / "capacity-report-app-latest.tar"), IMAGE_TAG])

    _env.step(f"Docker 离线包：{out_dir}")
    return out_dir


def update_running() -> None:
    _env.step("更新本机运行的容器（docker compose up -d）")
    _env.run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "up", "-d", "--force-recreate", "capacity-app"],
        cwd=_env.PACKAGING_DIR,
    )


def main() -> int:
    _env.setup_console()
    parser = argparse.ArgumentParser(description="编译 / 更新 Docker 镜像")
    parser.add_argument("action", nargs="?", choices=["build", "update"], default="build", help="build=编译并打包；update=编译并就地更新容器")
    parser.add_argument("--no-save", action="store_true", help="编译镜像但不导出 tar")
    args = parser.parse_args()

    build_image()

    if args.action == "update":
        update_running()
    else:
        make_bundle(save_tar=not args.no_save)

    _env.step("清理前端中间产物")
    _env.remove_path(_env.FRONTEND_DIR / "dist")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
