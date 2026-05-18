import os
import platform
import time
from threading import Thread

from fastapi import APIRouter

from app.services.runtime import (
    is_container_runtime,
    is_supervisor_running,
    restart_method_name,
    restart_via_supervisor,
    terminate_current_process,
)


router = APIRouter(tags=["service"])


@router.post("/api/service/restart")
async def restart_service():
    supervisor_running = is_supervisor_running()
    container_runtime = is_container_runtime()

    if supervisor_running:
        success, message = restart_via_supervisor()
        if success:
            return {
                "success": True,
                "message": message,
                "method": "supervisor",
                "container": container_runtime,
            }

    method = restart_method_name(supervisor_running)
    thread = Thread(target=_delayed_exit, daemon=True)
    thread.start()

    message = "服务正在重启，请稍后刷新页面..."
    if supervisor_running:
        message = "supervisor 命令不可用，已切换为进程重启..."
    elif container_runtime:
        message = "服务进程正在退出，容器或进程管理器将拉起服务..."

    return {
        "success": True,
        "message": message,
        "method": method,
        "container": container_runtime,
    }


@router.get("/api/service/status")
async def get_service_status():
    return {
        "status": "running",
        "version": "2.0.2",
        "platform": platform.system(),
        "supervisor": is_supervisor_running(),
        "container": is_container_runtime(),
        "pid": os.getpid(),
        "python_version": platform.python_version(),
    }


def _delayed_exit() -> None:
    time.sleep(1)
    terminate_current_process()
