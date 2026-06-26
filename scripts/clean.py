"""清理脚本：清除缓存、__pycache__、编译产物和运行时临时数据，保持项目整洁。

用法：
    python scripts/clean.py            # 清理缓存 / 编译产物 / 运行时临时数据（保留 .venv 与前端依赖）
    python scripts/clean.py --deep      # 额外清理 .venv 与 frontend/node_modules（下次运行会重装）

默认不会删除源码、配置（Configure.json/*.sql）、授权文件或 .git。
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

# 遍历时跳过这些目录（既慢又无意义）
PRUNE_DIRS = {".git", ".venv", "node_modules"}

# 编译产物 / 缓存目录（相对项目根）
ARTIFACT_DIRS = [
    "dist",
    "frontend/dist",
    "frontend/.vite",
    "src-tauri/target",
    "src-tauri/binaries",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
]

# 运行时临时数据目录
RUNTIME_DIRS = ["cache", "logs", "uploads"]

DEEP_DIRS = [".venv", "frontend/node_modules"]


def clean_pycache() -> int:
    removed = 0
    for current, dirs, files in os.walk(_env.ROOT):
        dirs[:] = [d for d in dirs if d not in PRUNE_DIRS]
        for d in list(dirs):
            if d == "__pycache__":
                if _env.remove_path(Path(current) / d):
                    removed += 1
                dirs.remove(d)
        for f in files:
            if f.endswith((".pyc", ".pyo")):
                if _env.remove_path(Path(current) / f):
                    removed += 1
    return removed


def clean_dirs(rel_dirs: list[str]) -> int:
    removed = 0
    for rel in rel_dirs:
        if _env.remove_path(_env.ROOT / rel):
            _env.info(f"已删除 {rel}")
            removed += 1
    return removed


def main() -> int:
    _env.setup_console()
    parser = argparse.ArgumentParser(description="清理缓存与编译产物")
    parser.add_argument("--deep", action="store_true", help="额外清理 .venv 与 frontend/node_modules")
    args = parser.parse_args()

    _env.step("清理 __pycache__ / *.pyc")
    n = clean_pycache()
    _env.info(f"清理 {n} 项")

    _env.step("清理编译产物")
    clean_dirs(ARTIFACT_DIRS)

    _env.step("清理运行时临时数据（cache / logs / uploads）")
    clean_dirs(RUNTIME_DIRS)

    if args.deep:
        _env.step("深度清理依赖（.venv / node_modules）")
        clean_dirs(DEEP_DIRS)

    _env.step("清理完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
