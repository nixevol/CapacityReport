"""Tauri 桌面端测试运行脚本：构建前端 + 后端 sidecar，然后 cargo tauri dev。

用法：
    python scripts/dev_tauri.py                 # 复用已有 sidecar/前端产物（缺失才构建）
    python scripts/dev_tauri.py --rebuild        # 强制重建前端和 sidecar

桌面端会启动本机 sidecar（http://127.0.0.1:9081）。首次运行会自动准备 .venv、
前端依赖、PyInstaller，并在缺少 Rust / Tauri CLI 时给出安装引导。
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402


def main() -> int:
    _env.setup_console()
    parser = argparse.ArgumentParser(description="Tauri 桌面端测试运行")
    parser.add_argument("--rebuild", action="store_true", help="强制重建前端与 sidecar")
    args = parser.parse_args()

    _env.ensure_rust()
    python = _env.ensure_venv(extra_packages=["pyinstaller"])

    dist_index = _env.FRONTEND_DIR / "dist" / "index.html"
    if args.rebuild or not dist_index.exists():
        _env.build_frontend(api_base=_env.DESKTOP_API_BASE)

    triple = _env.rust_host_triple()
    suffix = ".exe" if _env.host_platform() == "windows" else ""
    sidecar = _env.SRC_TAURI_DIR / "binaries" / f"{_env.SERVER_NAME}-{triple}{suffix}"
    if args.rebuild or not sidecar.exists():
        tmp = _env.DIST_DIR / ".tmp" / "pyinstaller"
        _env.build_tauri_sidecar(python, tmp / "work", tmp / "dist")

    _env.ensure_tauri_cli()

    _env.step("启动 Tauri 开发模式（cargo tauri dev）")
    _env.info("按 Ctrl+C 停止")
    try:
        completed = subprocess.run(["cargo", "tauri", "dev"], cwd=str(_env.SRC_TAURI_DIR))
    except KeyboardInterrupt:
        return 0
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
