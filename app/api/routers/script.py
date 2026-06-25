import shutil
import uuid
from datetime import datetime
from pathlib import Path
from threading import Thread

from fastapi import APIRouter, Body, HTTPException, Query

from app import state
from app.api.routers.task_runtime import set_task_stage
from app.config import AppConfig, CACHE_DIR, CELLDATA_SCRIPT, SQL_SCRIPT
from app.processor import DataProcessor, ProcessLogger


router = APIRouter(tags=["script"])

SCRIPT_PATHS = {
    "report": SQL_SCRIPT,
    "celldata": CELLDATA_SCRIPT,
}
SCRIPT_LABELS = {
    "report": "容量报表脚本",
    "celldata": "CellData 脚本",
}


def _resolve_script_path(script_type: str) -> Path:
    path = SCRIPT_PATHS.get(script_type)
    if path is None:
        raise HTTPException(status_code=400, detail=f"不支持的脚本类型: {script_type}")
    return path


@router.get("/api/script/content")
async def get_script_content(script_type: str = Query("report")):
    script_path = _resolve_script_path(script_type)
    label = SCRIPT_LABELS.get(script_type, script_type)
    try:
        if not script_path.exists():
            return {
                "success": True,
                "content": f"# {label}文件不存在，请在此编写脚本\n",
                "modified": None,
                "path": str(script_path),
                "script_type": script_type,
            }

        modified = datetime.fromtimestamp(script_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {
            "success": True,
            "content": script_path.read_text(encoding="utf-8"),
            "modified": modified,
            "path": str(script_path),
            "script_type": script_type,
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.post("/api/script/execute")
async def execute_script(script_type: str = Body("report", embed=True)):
    script_path = _resolve_script_path(script_type)
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
        set_task_stage(task_id, "processing", logs)

    logger = ProcessLogger(log_file=None, callback=log_callback)
    set_task_stage(task_id, "processing", logs)
    app_config = state.current_config()

    thread = Thread(
        target=_run_script,
        args=(task_id, logger, logs, app_config, script_path, script_type),
        daemon=True,
    )
    thread.start()
    label = SCRIPT_LABELS.get(script_type, script_type)
    return {"success": True, "message": f"{label}执行任务已启动", "task_id": task_id}


@router.post("/api/script/save")
async def save_script_content(
    content: str = Body(...),
    script_type: str = Body("report"),
):
    script_path = _resolve_script_path(script_type)
    try:
        if script_path.exists():
            shutil.copy(script_path, script_path.with_suffix(".sql.bak"))

        script_path.write_text(content, encoding="utf-8")
        modified = datetime.fromtimestamp(script_path.stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
        return {"success": True, "message": "脚本保存成功", "modified": modified}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def _run_script(
    task_id: str,
    logger: ProcessLogger,
    logs: list[str],
    app_config: AppConfig,
    script_path: Path,
    script_type: str,
) -> None:
    temp_work_dir: Path | None = None
    label = SCRIPT_LABELS.get(script_type, script_type)
    try:
        logger.info(f"开始执行{label}...")
        if script_type == "celldata":
            _run_celldata_script(script_path, app_config, logger)
        elif app_config.warehouse_type == "metrix":
            from app.services.pipeline import run_report_sql

            run_report_sql(app_config, logger)
        else:
            temp_work_dir = CACHE_DIR / task_id
            temp_work_dir.mkdir(parents=True, exist_ok=True)
            processor = DataProcessor(app_config, temp_work_dir, logger)
            processor._execute_sql_script()
        logger.success(f"{label}执行完成")
        set_task_stage(task_id, "completed", logs, status="completed")
    except Exception as exc:
        logger.error(f"{label}执行失败: {exc}")
        set_task_stage(task_id, "failed", logs, status="failed")
    finally:
        if temp_work_dir and temp_work_dir.exists():
            shutil.rmtree(temp_work_dir, ignore_errors=True)
        state.reset_task_lock()


def _run_celldata_script(script_path: Path, app_config: AppConfig, logger: ProcessLogger) -> None:
    from app.services.cell_data import execute_celldata_script

    execute_celldata_script(script_path, app_config, logger)
