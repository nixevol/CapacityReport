import os
from datetime import datetime

from fastapi import APIRouter

from app import state
from app.database import DatabaseManager


router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    checks = {
        "app": {"status": "ok"},
        "database": {"status": "unknown"},
    }

    try:
        db_manager = DatabaseManager(state.current_config())
        server_info = db_manager.get_server_info()
        checks["database"] = {
            "status": "ok",
            "version": server_info.get("version", "unknown"),
            "load_data_infile": server_info.get("load_data_infile", False),
        }
    except Exception as exc:
        checks["database"] = {"status": "error", "message": str(exc)}

    is_healthy = all(check.get("status") == "ok" for check in checks.values())
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.2",
        "uptime_pid": os.getpid(),
        "checks": checks,
    }
