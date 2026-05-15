import os
import platform
import signal
import subprocess
from pathlib import Path


def is_supervisor_running() -> bool:
    if os.environ.get("SUPERVISOR_ENABLED") == "1":
        return True

    supervisor_sock = Path("/var/run/supervisor.sock")
    if supervisor_sock.exists() and _command_succeeds(["supervisorctl", "status"], timeout=5):
        return True

    try:
        import psutil  # pyright: ignore[reportMissingModuleSource]

        parent = psutil.Process().parent()
        if parent and "supervisor" in parent.name().lower():
            return True
    except Exception:
        pass

    return _command_succeeds(["pgrep", "-f", "supervisord"], timeout=2)


def restart_via_supervisor() -> tuple[bool, str]:
    try:
        result = subprocess.run(
            ["supervisorctl", "restart", "fastapi"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        if result.returncode == 0:
            return True, "服务正在通过 supervisor 重启..."

        error_msg = result.stderr or result.stdout or "未知错误"
        return False, f"重启失败: {error_msg}"
    except subprocess.TimeoutExpired:
        return False, "重启操作超时"
    except FileNotFoundError:
        return False, "找不到 supervisorctl 命令"
    except Exception as exc:
        return False, f"重启异常: {exc}"


def terminate_current_process() -> None:
    if platform.system() == "Windows":
        os._exit(0)
    os.kill(os.getpid(), signal.SIGTERM)


def _command_succeeds(command: list[str], timeout: int) -> bool:
    try:
        result = subprocess.run(command, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0 and bool(result.stdout.strip() or command[0] == "supervisorctl")
    except Exception:
        return False

