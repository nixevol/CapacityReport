from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app import state
from app.processor import DataProcessor, ProcessLogger


router = APIRouter(tags=["tasks"])


@router.get("/api/task/status")
async def get_global_task_status():
    if state.global_task_lock["locked"]:
        task_id = state.global_task_lock["task_id"]
        if task_id and _task_finished(task_id):
            state.reset_task_lock()
            return {"has_active": False}

        return {
            "has_active": True,
            "task_id": task_id,
            "stage": state.global_task_lock["stage"],
            "started_at": state.global_task_lock["started_at"],
            "logs": [],
        }

    active_tasks = {
        task_id: task
        for task_id, task in state.processing_tasks.items()
        if task.get("status") == "processing"
    }
    if active_tasks:
        task_id = next(iter(active_tasks))
        return {
            "has_active": True,
            "task_id": task_id,
            "stage": "processing",
            "logs": active_tasks[task_id].get("logs", []),
        }

    return {"has_active": False}


@router.post("/api/task/lock")
async def lock_task(task_id: str = Body(..., embed=True)):
    if state.global_task_lock["locked"]:
        raise HTTPException(status_code=409, detail="已有任务在运行")

    state.global_task_lock.update(
        {
            "locked": True,
            "task_id": task_id,
            "stage": "uploading",
            "started_at": datetime.now().isoformat(),
        }
    )
    return {"success": True, "message": "任务已锁定"}


@router.post("/api/task/unlock")
async def unlock_task(task_id: str | None = Body(None, embed=True)):
    if task_id and state.global_task_lock["task_id"] != task_id:
        raise HTTPException(status_code=403, detail="无权解锁此任务")

    state.reset_task_lock()
    return {"success": True, "message": "任务已解锁"}


@router.get("/api/process/active")
async def get_active_task():
    return await get_global_task_status()


@router.post("/api/process/start")
async def start_processing(task_id: str = Body(..., embed=True)):
    record = state.history_manager.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")
    if record.status == "processing":
        raise HTTPException(status_code=400, detail="任务正在处理中")

    work_dir = Path(record.work_dir)
    if not work_dir.exists():
        raise HTTPException(status_code=400, detail="工作目录不存在")

    logs: list[str] = []

    def log_callback(message: str) -> None:
        logs.append(message)
        state.processing_tasks[task_id] = {"logs": logs.copy(), "status": "processing"}

    logger = ProcessLogger(log_file=work_dir / "log.txt", callback=log_callback)
    state.history_manager.update(task_id, status="processing")
    state.processing_tasks[task_id] = {"logs": [], "status": "processing"}
    state.global_task_lock.update(
        {
            "locked": True,
            "task_id": task_id,
            "stage": "processing",
            "started_at": datetime.now().isoformat(),
        }
    )

    thread = Thread(target=_run_processing, args=(task_id, work_dir, logger), daemon=True)
    thread.start()

    return {"success": True, "message": "处理任务已启动", "task_id": task_id}


@router.post("/api/process/status")
async def get_processing_status(task_id: str = Body(..., embed=True)):
    if task_id in state.processing_tasks:
        task_info = state.processing_tasks[task_id]
        logs = task_info.get("logs") or state.history_manager.get_logs(task_id)
        return {"task_id": task_id, "status": task_info["status"], "logs": logs}

    record = state.history_manager.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")

    return {
        "task_id": task_id,
        "status": record.status,
        "logs": state.history_manager.get_logs(task_id),
        "elapsed_time": record.elapsed_time,
        "error": record.error,
    }


def _task_finished(task_id: str) -> bool:
    record = state.history_manager.get(task_id)
    if record and record.status in {"completed", "failed"}:
        return True

    task_info: dict[str, Any] | None = state.processing_tasks.get(task_id)
    return bool(task_info and task_info.get("status") in {"completed", "failed"})


def _run_processing(task_id: str, work_dir: Path, logger: ProcessLogger) -> None:
    try:
        processor = DataProcessor(state.config, work_dir, logger)
        result = processor.process()
        status = "completed" if result.get("success") else "failed"
        state.history_manager.update(
            task_id,
            status=status,
            elapsed_time=result.get("elapsed_time", 0),
            error=result.get("error"),
            result_tables=["4G_结果表", "5G_结果表"],
        )
        state.processing_tasks[task_id] = {
            "logs": state.history_manager.get_logs(task_id),
            "status": status,
        }
    except Exception as exc:
        state.history_manager.update(task_id, status="failed", error=str(exc))
        state.processing_tasks[task_id] = {
            "logs": state.history_manager.get_logs(task_id),
            "status": "failed",
        }
    finally:
        try:
            state.apply_history_retention()
        except Exception as exc:
            print(f"自动清理处理历史失败: {exc}")
        state.reset_task_lock()
