from typing import Any

from app import state


def set_task_stage(task_id: str, stage: str, logs: list[str], status: str = "processing") -> None:
    state.processing_tasks[task_id] = {
        "logs": logs.copy(),
        "status": status,
        "stage": stage,
    }
    if state.global_task_lock["task_id"] == task_id:
        state.global_task_lock["stage"] = stage


def log_license_check(logger: Any, info: Any) -> None:
    if info.current_date:
        logger.info(
            f"授权校验通过，数据日期: {info.current_date.isoformat()}，"
            f"到期日期: {info.expires_on.isoformat()}"
        )
    elif info.zip_count:
        logger.warning("未从 ZIP 文件名识别到日期，已跳过授权日期比对")
    else:
        logger.warning("未找到 ZIP 文件，已跳过授权日期比对")


def apply_history_retention_safely() -> None:
    try:
        state.apply_history_retention()
    except Exception as exc:
        print(f"自动清理处理历史失败: {exc}")
