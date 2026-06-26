"""本地运行脚本：构建前端（如缺失）并启动后端服务。

用法：
    python scripts/run.py                 # 默认 0.0.0.0:9081
    python scripts/run.py --port 8080     # 指定端口
    python scripts/run.py --rebuild       # 强制重新构建前端

首次运行会自动创建 .venv、安装依赖；前端构建产物缺失时自动构建。按 Ctrl+C 停止。
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
    parser = argparse.ArgumentParser(description="本地运行 CapacityReport 服务")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址（默认 0.0.0.0）")
    parser.add_argument("--port", default="9081", help="监听端口（默认 9081）")
    parser.add_argument("--rebuild", action="store_true", help="强制重新构建前端")
    args = parser.parse_args()

    python = _env.ensure_venv()

    dist_index = _env.FRONTEND_DIR / "dist" / "index.html"
    if args.rebuild or not dist_index.exists():
        _env.build_frontend()

    _env.step(f"启动服务 -> http://localhost:{args.port}")
    _env.info("按 Ctrl+C 停止")
    try:
        completed = subprocess.run(
            [str(python), "-m", "app.main", "--host", args.host, "--port", str(args.port)],
            cwd=str(_env.ROOT),
        )
    except KeyboardInterrupt:
        return 0
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
