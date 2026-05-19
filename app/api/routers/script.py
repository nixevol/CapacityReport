import shutil
import uuid
from datetime import datetime
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, Body, HTTPException

from app import state
from app.config import AppConfig, CACHE_DIR, SQL_SCRIPT
from app.processor import DataProcessor, ProcessLogger


router = APIRouter(tags=["script"])


@router.get("/api/script/content")
async def get_script_content():
    try:
        if not SQL_SCRIPT.exists():
            return {
                "success": True,
                "content": "# SQL 脚本文件不存在，请在此编写脚本\n",
                "modified": None,
                "path": str(SQL_SCRIPT),
            }

        modified = datetime.fromtimestamp(SQL_SCRIPT.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "success": True,
            "content": SQL_SCRIPT.read_text(encoding="utf-8"),
            "modified": modified,
            "path": str(SQL_SCRIPT),
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/api/script/execute")
async def execute_script():
    if state.global_task_lock["locked"]:
        raise HTTPException(status_code=409, detail="已有任务在运行，请等待完成")

    task_id = f"script_{uuid.uuid4().hex[:8]}"
    state.global_task_lock.update(
        {
            "locked": True,
            "task_id": task_id,
            "stage": "processing",
            "started_at": datetime.now().isoformat(),
        }
    )

    logs: list[str] = []

    def log_callback(message: str) -> None:
        logs.append(message)
        state.processing_tasks[task_id] = {"logs": logs.copy(), "status": "processing"}

    logger = ProcessLogger(log_file=None, callback=log_callback)
    state.processing_tasks[task_id] = {"logs": [], "status": "processing"}
    app_config = state.current_config()

    thread = Thread(target=_run_script, args=(task_id, logger, logs, app_config), daemon=True)
    thread.start()
    return {"success": True, "message": "脚本执行任务已启动", "task_id": task_id}


@router.post("/api/script/save")
async def save_script_content(content: str = Body(..., embed=True)):
    try:
        if SQL_SCRIPT.exists():
            shutil.copy(SQL_SCRIPT, SQL_SCRIPT.with_suffix(".sql.bak"))

        SQL_SCRIPT.write_text(content, encoding="utf-8")
        modified = datetime.fromtimestamp(SQL_SCRIPT.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {"success": True, "message": "脚本保存成功", "modified": modified}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _run_script(task_id: str, logger: ProcessLogger, logs: list[str], app_config: AppConfig) -> None:
    temp_work_dir: Path | None = None
    try:
        logger.info("开始执行 SQL 脚本...")
        temp_work_dir = CACHE_DIR / task_id
        temp_work_dir.mkdir(parents=True, exist_ok=True)

        processor = DataProcessor(app_config, temp_work_dir, logger)
        processor._execute_sql_script()
        logger.success("SQL 脚本执行完成")
        state.processing_tasks[task_id] = {"logs": logs.copy(), "status": "completed"}
    except Exception as exc:
        logger.error(f"SQL 脚本执行失败: {exc}")
        state.processing_tasks[task_id] = {"logs": logs.copy(), "status": "failed"}
    finally:
        if temp_work_dir and temp_work_dir.exists():
            shutil.rmtree(temp_work_dir, ignore_errors=True)
        state.reset_task_lock()
