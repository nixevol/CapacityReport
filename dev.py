"""CapacityReport standalone dev launcher.

Usage:
    python dev.py

Starts two processes:
  [api] CapacityReport API  http://127.0.0.1:9081  (auto-reload)
  [web] CapacityReport web  http://127.0.0.1:5174  (vite HMR, proxy /api -> 9081)
Press Ctrl+C to stop.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IS_WINDOWS = os.name == "nt"
VENV_DIR = ROOT / ".venv"
VENV_PYTHON = VENV_DIR / ("Scripts" if IS_WINDOWS else "bin") / ("python.exe" if IS_WINDOWS else "python")
REQUIREMENTS = ROOT / "requirements.txt"
API_PORT = 9081
WEB_PORT = 5174

SYSTEM_PYTHON_CANDIDATES = [
    Path(r"D:\Program Files\uv\python\cpython-3.14.3-windows-x86_64-none\python.exe"),
    Path(shutil.which("python3") or ""),
    Path(shutil.which("python") or ""),
]

_processes: list[tuple[str, subprocess.Popen]] = []
_stopping = threading.Event()


def log(name: str, message: str) -> None:
    line = f"[{name}] {message}".rstrip("\r\n") + "\n"
    try:
        sys.stdout.write(line)
    except UnicodeEncodeError:
        encoding = sys.stdout.encoding or "utf-8"
        sys.stdout.write(line.encode(encoding, "replace").decode(encoding, "replace"))
    sys.stdout.flush()


def _stream(name: str, process: subprocess.Popen) -> None:
    assert process.stdout is not None
    for raw in iter(process.stdout.readline, b""):
        line = raw.decode("utf-8", "replace").rstrip("\r\n")
        log(name, line)


def _spawn(name: str, args: list[str], cwd: Path, env: dict[str, str] | None = None) -> subprocess.Popen:
    kwargs: dict[str, object] = {
        "cwd": str(cwd),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "env": env,
    }
    if IS_WINDOWS:
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
            if IS_WINDOWS:
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


def _find_system_python() -> Path | None:
    for candidate in SYSTEM_PYTHON_CANDIDATES:
        if candidate and candidate.exists():
            return candidate
    return None


def _ensure_venv() -> Path:
    if VENV_PYTHON.exists():
        return VENV_PYTHON

    base_python = _find_system_python()
    if base_python is None:
        log("dev", "no Python found; install Python or uv first")
        raise SystemExit(1)

    log("dev", f"creating venv with {base_python} ...")
    subprocess.run([str(base_python), "-m", "venv", str(VENV_DIR)], check=True)

    log("dev", "installing dependencies ...")
    subprocess.run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)], cwd=str(ROOT), check=True)

    return VENV_PYTHON


def _ensure_node_modules() -> None:
    web_dir = ROOT / "frontend"
    if (web_dir / "node_modules").exists():
        return
    npm = shutil.which("npm")
    if not npm:
        log("dev", "npm not found; install Node.js first")
        raise SystemExit(1)
    log("web", "installing frontend dependencies ...")
    subprocess.run([npm, "install"], cwd=str(web_dir), shell=IS_WINDOWS, check=True)


def main() -> int:
    try:
        sys.stdout.reconfigure(errors="replace")
    except Exception:
        pass

    python = _ensure_venv()
    _ensure_node_modules()

    node = shutil.which("node")
    vite_bin = ROOT / "frontend" / "node_modules" / "vite" / "bin" / "vite.js"
    if not node or not vite_bin.exists():
        log("dev", "node or vite not found after npm install")
        return 1

    api_proc = _spawn(
        "api",
        [str(python), "-m", "uvicorn", "app.main:app", "--reload", "--host", "127.0.0.1", "--port", str(API_PORT)],
        ROOT,
    )
    log("api", f"starting -> http://127.0.0.1:{API_PORT} (auto-reload)")

    log("web", "waiting for backend ...")
    if _wait_for_http("api", f"http://127.0.0.1:{API_PORT}/health"):
        log("web", "backend ready")
    elif not _stopping.is_set():
        log("web", "backend not ready in time; starting frontend anyway")

    if _stopping.is_set() or api_proc.poll() is not None:
        return api_proc.poll() or 1

    _spawn("web", [node, str(vite_bin), "--host", "127.0.0.1", "--port", str(WEB_PORT)], ROOT / "frontend")
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
