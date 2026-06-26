"""开发测试脚本：同时启动后端（自动重载）和前端（Vite 热更新）。

用法：
    python scripts/dev.py

启动两个进程：
  [api] CapacityReport API  http://127.0.0.1:9081  （自动重载）
  [web] CapacityReport web  http://127.0.0.1:5174  （Vite 热更新，/api 代理到 9081）

按 Ctrl+C 停止全部。首次运行会自动创建 .venv 并安装依赖、自动安装前端依赖。
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _env  # noqa: E402

API_PORT = 9081
WEB_PORT = 5174

_processes: list[tuple[str, subprocess.Popen]] = []
_stopping = threading.Event()


def log(name: str, message: str) -> None:
    print(f"[{name}] {message}".rstrip(), flush=True)


def _stream(name: str, process: subprocess.Popen) -> None:
    assert process.stdout is not None
    for raw in iter(process.stdout.readline, b""):
        log(name, raw.decode("utf-8", "replace").rstrip("\r\n"))


def _spawn(name: str, args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen:
    kwargs: dict[str, object] = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "env": env,
    }
    if _env.IS_WINDOWS:
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP | getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True
    process = subprocess.Popen(args, **kwargs)  # type: ignore[arg-type]
    _processes.append((name, process))
    threading.Thread(target=_stream, args=(name, process), daemon=True).start()
    return process


def _stop_all() -> None:
    if _stopping.is_set():
        return
    _stopping.set()
    for name, process in _processes:
        if process.poll() is not None:
            continue
        log(name, "stopping...")
        try:
            if _env.IS_WINDOWS:
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(process.pid)], capture_output=True, check=False)
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        except Exception:
            pass


def _wait_for_http(proc_name: str, url: str, timeout: float = 90.0) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if _stopping.is_set():
            return False
        if any(name == proc_name and proc.poll() is not None for name, proc in _processes):
            return False
        try:
            with urllib.request.urlopen(url, timeout=2):
                return True
        except urllib.error.HTTPError:
            return True
        except (urllib.error.URLError, OSError):
            time.sleep(0.4)
    return False


def main() -> int:
    _env.setup_console()

    python = _env.ensure_venv()
    _env.ensure_frontend_deps()

    node = _env.which("node")
    vite_bin = _env.FRONTEND_DIR / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite_bin.exists():
        _env.die("未找到 node 或 vite（请确认前端依赖已安装）")

    _env.step("启动开发服务")
    _spawn(
        "api",
        [str(python), "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", str(API_PORT)],
        _env.ROOT,
    )
    log("api", f"starting -> http://127.0.0.1:{API_PORT} (auto-reload)")

    log("web", "waiting for backend ...")
    if _wait_for_http("api", f"http://127.0.0.1:{API_PORT}/health"):
        log("web", "backend ready")
    elif not _stopping.is_set():
        log("web", "backend not ready in time; starting frontend anyway")

    api_proc = _processes[0][1]
    if _stopping.is_set() or api_proc.poll() is not None:
        return api_proc.poll() or 1

    _spawn("web", [node, str(vite_bin), "--host", "127.0.0.1", "--port", str(WEB_PORT)], _env.FRONTEND_DIR)
    log("web", f"starting -> http://127.0.0.1:{WEB_PORT} (hot reload)")
    log("dev", "press Ctrl+C to stop")

    reported: set[str] = set()
    try:
        while not _stopping.is_set():
            for name, process in _processes:
                code = process.poll()
                if code is None or name in reported:
                    continue
                reported.add(name)
                if name == "api":
                    log(name, f"exited with code {code}; shutting down")
                    return code or 0
                log(name, f"exited with code {code}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        log("dev", "received Ctrl+C")
    finally:
        _stop_all()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
