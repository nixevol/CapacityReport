from __future__ import annotations

import time
from datetime import datetime
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, Body, HTTPException

from app import state
from app.api.routers.task_runtime import set_task_stage
from app.config import AppConfig, CACHE_DIR
from app.processor import ProcessLogger
from app.services.cell_data import refresh_cell_data

router = APIRouter(tags=["cell-data"])


@router.post("/api/cell-data/process/start")
async def start_cell_data_processing():
    if state.global_task_lock["locked"]:
        raise HTTPException(status_code=409, detail="已有任务在运行，请等待当前任务完成")

    task_id = "cell_data_" + datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = CACHE_DIR / task_id
    work_dir.mkdir(parents=True, exist_ok=True)
    logs: list[str] = []
    current_stage = "locating"

    def log_callback(message: str) -> None:
        logs.append(message)
        set_task_stage(task_id, current_stage, logs)

    def stage_callback(stage: str) -> None:
        nonlocal current_stage
        current_stage = stage
        set_task_stage(task_id, current_stage, logs)

    logger = ProcessLogger(
        log_file=work_dir / "log.txt",
        callback=log_callback,
        stage_callback=stage_callback,
    )
    app_config = state.current_config()
    state.processing_tasks[task_id] = {"logs": [], "status": "processing", "stage": current_stage}
    state.global_task_lock.update(
        {
            "locked": True,
            "task_id": task_id,
            "stage": current_stage,
            "started_at": datetime.now().isoformat(),
        }
    )

    thread = Thread(target=_run_cell_data_processing, args=(task_id, work_dir, logger, app_config), daemon=True)
    thread.start()
    return {"success": True, "message": "CellData 处理已启动", "task_id": task_id, "stage": current_stage}


@router.post("/api/cell-data/process/status")
async def get_cell_data_processing_status(task_id: str = Body(..., embed=True)):
    if task_id in state.processing_tasks:
        task = state.processing_tasks[task_id]
        return {
            "task_id": task_id,
            "status": task.get("status", "processing"),
            "stage": task.get("stage", "processing"),
            "logs": task.get("logs", []),
            "error": task.get("error"),
            "result": task.get("result"),
            "elapsed_time": task.get("elapsed_time"),
        }
    raise HTTPException(status_code=404, detail="任务不存在")


def _run_cell_data_processing(task_id: str, work_dir: Path, logger: ProcessLogger, app_config: AppConfig) -> None:
    started = time.time()
    try:
        result = refresh_cell_data(app_config, work_dir, logger)
        elapsed = round(time.time() - started, 2)
        state.processing_tasks[task_id] = {
            "logs": logger.get_logs(),
            "status": "completed",
            "stage": "completed",
            "elapsed_time": elapsed,
            "result": {
                "selected_files": result.selected_files,
                "parsed_rows": result.parsed_rows,
                "imported_rows": result.imported_rows,
                "skipped_rows": result.skipped_rows,
            },
        }
    except Exception as exc:
        logger.error(str(exc))
        state.processing_tasks[task_id] = {
            "logs": logger.get_logs(),
            "status": "failed",
            "stage": "failed",
            "error": str(exc),
            "elapsed_time": round(time.time() - started, 2),
        }
    finally:
        state.reset_task_lock()
