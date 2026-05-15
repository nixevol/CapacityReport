import os
import platform
import subprocess
import time
from threading import Thread

from fastapi import APIRouter

from app.services.runtime import (
    is_supervisor_running,
    restart_via_supervisor,
    terminate_current_process,
)


router = APIRouter(tags=["service"])


@router.post("/api/service/restart")
async def restart_service():
    if is_supervisor_running():
        success, message = restart_via_supervisor()
        return {"success": success, "message": message, "method": "supervisor"}

    if platform.system() != "Windows":
        try:
            result = subprocess.run(
                ["supervisorctl", "restart", "fastapi"],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0:
                return {
                    "success": True,
                    "message": "服务正在通过 supervisor 重启...",
                    "method": "supervisor",
                }
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "message": "重启操作超时，请检查 supervisor 状态",
                "method": "supervisor",
            }
        except Exception:
            pass

    thread = Thread(target=_delayed_exit, daemon=True)
    thread.start()
    return {"success": True, "message": "服务正在重启，请稍后刷新页面...", "method": "signal"}


@router.get("/api/service/status")
async def get_service_status():
    return {
        "status": "running",
        "version": "2.0.2",
        "platform": platform.system(),
        "supervisor": is_supervisor_running(),
        "pid": os.getpid(),
        "python_version": platform.python_version(),
    }


def _delayed_exit() -> None:
    time.sleep(1)
    terminate_current_process()

