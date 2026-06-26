"""Server 便携版编译脚本：打包后端可执行文件 + 前端产物 + 配置 + 启动脚本。

用法：
    python scripts/build_server.py                 # 编译当前系统的便携版
    python scripts/build_server.py --no-archive     # 不生成 zip 压缩包

产物：dist/server/CapacityReport-Server-<平台>-x64/ 及其 .zip。
注意：便携版需在目标系统原生构建（Windows 包在 Windows、Linux 包在 Linux、macOS 包在 macOS）。
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

RUNTIME_FILES = ["Configure.json", "ReportScript.sql", "CellData.sql"]

RUN_BAT = """@echo off
setlocal
cd /d "%~dp0"
if not exist cache mkdir cache
if not exist logs mkdir logs
echo Starting CapacityReport server...
echo URL: http://localhost:9081
"%~dp0{exe}" --host 0.0.0.0 --port 9081
pause
"""

START_SH = """#!/usr/bin/env sh
set -eu
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"
cd "$SCRIPT_DIR"
mkdir -p cache logs
chmod +x "./{exe}" 2>/dev/null || true
echo "Starting CapacityReport server..."
echo "URL: http://localhost:9081"
exec "./{exe}" --host 0.0.0.0 --port 9081
"""


def write_launchers(out_dir: Path, platform: str) -> None:
    exe = _env.server_exe_name(platform)
    if platform == "windows":
        (out_dir / "run.bat").write_text(RUN_BAT.format(exe=exe), encoding="utf-8")
    else:
        start = out_dir / "start.sh"
        start.write_text(START_SH.format(exe=exe).replace("\r\n", "\n"), encoding="utf-8", newline="\n")
        start.chmod(0o755)


def main() -> int:
    _env.setup_console()
    parser = argparse.ArgumentParser(description="编译 Server 便携版")
    parser.add_argument("--no-archive", action="store_true", help="不生成 zip 压缩包")
    args = parser.parse_args()

    platform = _env.host_platform()
    python = _env.ensure_venv(extra_packages=["pyinstaller"])
    _env.build_frontend()

    tmp = _env.DIST_DIR / ".tmp" / "pyinstaller"
    binary_dir = _env.build_server_binary(python, onefile=False, work_dir=tmp / "work", dist_dir=tmp / "dist")

    out_name = f"CapacityReport-Server-{platform}-x64"
    out_dir = _env.DIST_DIR / "server" / out_name
    _env.remove_path(out_dir)
    _env.remove_path(_env.DIST_DIR / "server" / f"{out_name}.zip")
    out_dir.mkdir(parents=True, exist_ok=True)

    _env.step("组装便携版目录")
    shutil.copytree(binary_dir, out_dir, dirs_exist_ok=True)
    for name in RUNTIME_FILES:
        src = _env.ROOT / name
        if src.exists():
            shutil.copy2(src, out_dir / name)
    (out_dir / "cache").mkdir(exist_ok=True)
    (out_dir / "logs").mkdir(exist_ok=True)

    frontend_dist = _env.FRONTEND_DIR / "dist"
    if not frontend_dist.exists():
        _env.die(f"前端产物不存在：{frontend_dist}")
    shutil.copytree(frontend_dist, out_dir / "frontend" / "dist", dirs_exist_ok=True)

    write_launchers(out_dir, platform)

    if not args.no_archive:
        _env.step("生成压缩包")
        archive = shutil.make_archive(str(out_dir), "zip", root_dir=out_dir)
        _env.info(f"压缩包：{archive}")

    _env.step("清理中间产物")
    _env.remove_path(_env.DIST_DIR / ".tmp")
    _env.remove_path(frontend_dist)

    _env.step(f"便携版完成：{out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
