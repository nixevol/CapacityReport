"""CapacityReport 脚本共享工具。

所有 scripts/ 下的运行/编译脚本都只依赖 Python 标准库，可直接用任意系统 Python 运行
（python scripts/xxx.py）。本模块负责：

- 自动创建并维护项目 .venv（使用标准库 venv，不使用 uv），按 requirements.txt 变化自动重装依赖。
- 检测 Node.js / Rust(Cargo) / Docker 环境，缺失时给出安装引导。
- 统一的日志、命令执行、平台判断等助手。
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IS_WINDOWS = os.name == "nt"

VENV_DIR = ROOT / ".venv"
VENV_BIN = VENV_DIR / ("Scripts" if IS_WINDOWS else "bin")
VENV_PYTHON = VENV_BIN / ("python.exe" if IS_WINDOWS else "python")
REQUIREMENTS = ROOT / "requirements.txt"
REQ_HASH_FILE = VENV_DIR / ".requirements.hash"

FRONTEND_DIR = ROOT / "frontend"
SRC_TAURI_DIR = ROOT / "src-tauri"
PACKAGING_DIR = ROOT / "packaging"
DIST_DIR = ROOT / "dist"

DESKTOP_API_BASE = "http://127.0.0.1:9081"
SERVER_NAME = "capareport-server"


# --------------------------------------------------------------------------- 日志


def _supports_color() -> bool:
    return sys.stdout.isatty() and not IS_WINDOWS


_C = {
    "reset": "\033[0m",
    "green": "\033[32m",
    "cyan": "\033[36m",
    "yellow": "\033[33m",
    "red": "\033[31m",
}


def setup_console() -> None:
    """让 Windows 控制台也能正常输出 UTF-8，避免中文乱码报错。"""
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


def step(message: str) -> None:
    color = _C["green"] if _supports_color() else ""
    reset = _C["reset"] if _supports_color() else ""
    print(f"\n{color}==> {message}{reset}", flush=True)


def info(message: str) -> None:
    print(f"    {message}", flush=True)


def warn(message: str) -> None:
    color = _C["yellow"] if _supports_color() else ""
    reset = _C["reset"] if _supports_color() else ""
    print(f"{color}[warn] {message}{reset}", flush=True)


def die(message: str, hint: str | None = None) -> "NoReturn":  # type: ignore[name-defined]
    color = _C["red"] if _supports_color() else ""
    reset = _C["reset"] if _supports_color() else ""
    print(f"{color}[error] {message}{reset}", file=sys.stderr, flush=True)
    if hint:
        print(f"        {hint}", file=sys.stderr, flush=True)
    raise SystemExit(1)


# --------------------------------------------------------------------------- 命令执行


def run(args: list[str], cwd: Path | None = None, env: dict[str, str] | None = None) -> None:
    """执行命令并实时输出；失败抛 SystemExit。"""
    printable = " ".join(str(a) for a in args)
    info(printable)
    completed = subprocess.run(
        [str(a) for a in args],
        cwd=str(cwd) if cwd else None,
        env=env,
        shell=False,
    )
    if completed.returncode != 0:
        die(f"命令执行失败（退出码 {completed.returncode}）：{printable}")


def which(name: str) -> str | None:
    return shutil.which(name)


def host_platform() -> str:
    if IS_WINDOWS:
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def server_exe_name(platform: str | None = None) -> str:
    platform = platform or host_platform()
    return f"{SERVER_NAME}.exe" if platform == "windows" else SERVER_NAME


# --------------------------------------------------------------------------- Python venv


def _base_python() -> str:
    """返回用于创建 venv 的基础解释器，优先当前运行脚本的解释器。"""
    if sys.executable:
        return sys.executable
    for name in ("python3", "python"):
        found = shutil.which(name)
        if found:
            return found
    die(
        "未找到可用的 Python 解释器。",
        "请安装 Python 3.10+ 并加入 PATH：https://www.python.org/downloads/",
    )


def _requirements_hash() -> str:
    try:
        return hashlib.sha256(REQUIREMENTS.read_bytes()).hexdigest()
    except OSError:
        return ""


def ensure_venv(extra_packages: list[str] | None = None) -> Path:
    """确保 .venv 存在且依赖最新，返回 venv 内的 python 路径。"""
    extra_packages = extra_packages or []
    created = False

    if not VENV_PYTHON.exists():
        base = _base_python()
        step(f"创建虚拟环境 .venv（{base}）")
        run([base, "-m", "venv", str(VENV_DIR)])
        created = True

    current_hash = _requirements_hash()
    stored_hash = REQ_HASH_FILE.read_text(encoding="utf-8").strip() if REQ_HASH_FILE.exists() else ""

    if created or current_hash != stored_hash:
        step("安装/更新 Python 依赖（requirements.txt）")
        run([str(VENV_PYTHON), "-m", "pip", "install", "--upgrade", "pip"])
        run([str(VENV_PYTHON), "-m", "pip", "install", "-r", str(REQUIREMENTS)], cwd=ROOT)
        try:
            REQ_HASH_FILE.write_text(current_hash, encoding="utf-8")
        except OSError:
            pass

    for package in extra_packages:
        _ensure_python_package(package)

    return VENV_PYTHON


def _ensure_python_package(package: str) -> None:
    """确保某个额外包（如 pyinstaller）已安装在 venv 中。"""
    name = package.split("==")[0].split(">=")[0].strip()
    probe = subprocess.run(
        [str(VENV_PYTHON), "-m", "pip", "show", name],
        capture_output=True,
    )
    if probe.returncode == 0:
        return
    step(f"安装构建依赖 {package}")
    run([str(VENV_PYTHON), "-m", "pip", "install", package], cwd=ROOT)


# --------------------------------------------------------------------------- Node.js


def ensure_node() -> str:
    """确保 Node.js / npm 可用，返回 npm 可执行路径。"""
    npm = shutil.which("npm")
    node = shutil.which("node")
    if not npm or not node:
        die(
            "未检测到 Node.js / npm（构建前端需要）。",
            "请安装 Node.js 18+：https://nodejs.org/ ，安装后重新打开终端再运行。",
        )
    return npm


def ensure_frontend_deps() -> None:
    npm = ensure_node()
    if (FRONTEND_DIR / "node_modules").exists():
        return
    step("安装前端依赖（npm install）")
    run([npm, "install"], cwd=FRONTEND_DIR)


def build_frontend(api_base: str | None = None) -> None:
    npm = ensure_node()
    ensure_frontend_deps()
    step("构建前端（npm run build）")
    env = os.environ.copy()
    if api_base:
        env["VITE_API_BASE"] = api_base
    else:
        env.pop("VITE_API_BASE", None)
    completed = subprocess.run([npm, "run", "build"], cwd=str(FRONTEND_DIR), env=env)
    if completed.returncode != 0:
        die("前端构建失败（npm run build）")


# --------------------------------------------------------------------------- Rust / Tauri


def ensure_rust() -> None:
    """确保 Rust 工具链（cargo + rustc）可用（编译 Tauri 桌面端需要）。"""
    if shutil.which("cargo") and shutil.which("rustc"):
        return
    die(
        "未检测到 Rust 工具链（cargo / rustc），编译 Tauri 桌面端需要。",
        "请安装 Rust：https://www.rust-lang.org/tools/install ，安装后重新打开终端再运行。",
    )


def rust_host_triple() -> str:
    output = subprocess.run(["rustc", "-vV"], capture_output=True, text=True)
    for line in output.stdout.splitlines():
        if line.startswith("host:"):
            return line.split(":", 1)[1].strip()
    die("无法识别 Rust host triple（rustc -vV）")


def ensure_tauri_cli() -> None:
    probe = subprocess.run(["cargo", "tauri", "--version"], capture_output=True)
    if probe.returncode == 0:
        return
    step("安装 Tauri CLI（cargo install tauri-cli）")
    run(["cargo", "install", "tauri-cli", "--locked"])


# --------------------------------------------------------------------------- PyInstaller

PYINSTALLER_SPEC = PACKAGING_DIR / "capareport-server.spec"


def build_server_binary(python: Path, onefile: bool, work_dir: Path, dist_dir: Path) -> Path:
    """用 PyInstaller 打包后端为可执行文件。

    onefile=True 返回单文件可执行文件路径；onefile=False 返回 onedir 目录路径。
    """
    remove_path(work_dir)
    remove_path(dist_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    dist_dir.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    if onefile:
        env["CAPAREPORT_ONEFILE"] = "1"
    else:
        env.pop("CAPAREPORT_ONEFILE", None)

    step(f"PyInstaller 打包后端（{'onefile' if onefile else 'onedir'}）")
    run(
        [
            str(python), "-m", "PyInstaller", "--clean", "--noconfirm",
            "--workpath", str(work_dir), "--distpath", str(dist_dir), str(PYINSTALLER_SPEC),
        ],
        cwd=ROOT,
        env=env,
    )

    if onefile:
        binary = dist_dir / server_exe_name()
        if not binary.exists():
            die(f"未找到 PyInstaller 单文件产物：{binary}")
        return binary

    out_dir = dist_dir / SERVER_NAME
    if not out_dir.exists():
        die(f"未找到 PyInstaller onedir 产物：{out_dir}")
    return out_dir


def build_tauri_sidecar(python: Path, work_dir: Path, dist_dir: Path) -> Path:
    """构建桌面端 sidecar（onefile）并按 Rust host triple 命名复制到 src-tauri/binaries。"""
    binary = build_server_binary(python, onefile=True, work_dir=work_dir, dist_dir=dist_dir)
    triple = rust_host_triple()
    sidecar_dir = SRC_TAURI_DIR / "binaries"
    sidecar_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".exe" if host_platform() == "windows" else ""
    target = sidecar_dir / f"{SERVER_NAME}-{triple}{suffix}"
    shutil.copy2(binary, target)
    info(f"sidecar -> {target}")
    return target


# --------------------------------------------------------------------------- Docker


def ensure_docker() -> None:
    if not shutil.which("docker"):
        die(
            "未检测到 Docker，构建镜像需要。",
            "请安装 Docker Desktop / Docker Engine：https://docs.docker.com/get-docker/",
        )


# --------------------------------------------------------------------------- 清理助手


def remove_path(path: Path) -> bool:
    """安全删除文件或目录，仅允许删除工作区内路径。"""
    try:
        resolved = path.resolve()
    except OSError:
        return False
    if ROOT not in resolved.parents and resolved != ROOT:
        warn(f"跳过工作区外路径：{resolved}")
        return False
    if not resolved.exists():
        return False
    if resolved.is_dir():
        shutil.rmtree(resolved, ignore_errors=True)
    else:
        try:
            resolved.unlink()
        except OSError:
            return False
    return True
