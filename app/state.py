from typing import Any

from app.config import AppConfig
from app.history import HistoryManager


config = AppConfig.load()
history_manager = HistoryManager()
processing_tasks: dict[str, dict[str, Any]] = {}
upload_sessions: dict[str, dict[str, Any]] = {}

global_task_lock: dict[str, Any] = {
    "locked": False,
    "task_id": None,
    "stage": None,
    "started_at": None,
}


def reset_task_lock() -> None:
    global_task_lock["locked"] = False
    global_task_lock["task_id"] = None
    global_task_lock["stage"] = None
    global_task_lock["started_at"] = None


def apply_history_retention() -> int:
    retention = config.history_retention.normalized()
    if not retention.enabled:
        return 0
    return history_manager.prune_finished(retention.keep_count)
