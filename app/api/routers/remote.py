import time
from datetime import date, datetime
from pathlib import Path
from threading import Thread
from typing import Any, Callable, Iterable

from fastapi import APIRouter, Body, HTTPException

from app import state
from app.api.routers.task_runtime import (
    apply_history_retention_safely,
    log_license_check,
    set_task_stage,
)
from app.config import AppConfig, CACHE_DIR, RemoteDataConfig
from app.processor import DataProcessor, ProcessLogger
from app.config import CELLDATA_SCRIPT
from app.services.cell_data import copy_celldata_tables_to_capacity, execute_celldata_script, refresh_cell_data
from app.services.license import LicenseError, check_processing_allowed
from app.services.platform import PlatformStorageDownloader, make_source_downloader
from app.services.pipeline import RESULT_TABLES, run_import_and_report
from app.services.remote_download import RemoteDataDownloader


router = APIRouter(tags=["remote"])


@router.post("/api/remote/test")
def test_remote_connection(config: dict[str, Any] | None = Body(None)):
    app_config = state.current_config()
    try:
        if app_config.source_type == "metrix":
            PlatformStorageDownloader(app_config).test_connection()
            return {"success": True, "message": "平台储存连接成功"}
        # FTP/SFTP: test the posted form config if provided, else the saved one.
        remote_config = RemoteDataConfig.from_dict(config) if config else app_config.remote_data
        RemoteDataDownloader(remote_config).test_connection()
        return {"success": True, "message": "远程服务器连接成功"}
    except Exception as exc:
        return {"success": False, "message": f"连接失败: {exc}"}


@router.post("/api/remote/start")
async def start_remote_processing():
    return start_remote_processing_job(source="manual")


@router.get("/api/remote/scheduler/status")
def get_scheduler_status():
    if state.auto_scheduler is None:
        return {"enabled": False, "running": False, "message": "自动调度器未启动"}
    return state.auto_scheduler.get_status()


@router.post("/api/remote/scheduler/trigger")
def trigger_scheduler_check():
    if state.auto_scheduler is None:
        raise HTTPException(status_code=503, detail="自动调度器未启动")
    return state.auto_scheduler.check_and_run(manual=True)


def start_remote_processing_job(
    *,
    source: str = "manual",
    on_finish: Callable[[str, str], None] | None = None,
    target_dates: Iterable[date] | None = None,
) -> dict[str, Any]:
    if state.global_task_lock["locked"]:
        raise HTTPException(status_code=409, detail="已有任务在运行，请等待当前任务完成")

    app_config = state.current_config()
    remote_config = app_config.remote_data.normalized()
    if not remote_config.enabled:
        raise HTTPException(status_code=400, detail="请先启用远程数据配置")

    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = CACHE_DIR / task_id
    work_dir.mkdir(parents=True, exist_ok=True)

    logs: list[str] = []
    current_stage = "downloading"

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
    state.history_manager.create(work_dir, 0, record_id=task_id)
    state.history_manager.update(task_id, status="processing")
    state.processing_tasks[task_id] = {"logs": [], "status": "processing", "stage": current_stage}
    state.global_task_lock.update(
        {
            "locked": True,
            "task_id": task_id,
            "stage": "downloading",
            "started_at": datetime.now().isoformat(),
        }
    )

    thread = Thread(
        target=_run_remote_processing,
        args=(task_id, work_dir, app_config, remote_config, logger, source, on_finish, target_dates),
        daemon=True,
    )
    thread.start()

    return {
        "success": True,
        "message": "自动调度远程下载处理任务已启动" if source == "scheduler" else "远程下载处理任务已启动",
        "task_id": task_id,
        "stage": "downloading",
    }


def _run_remote_processing(
    task_id: str,
    work_dir: Path,
    app_config: AppConfig,
    remote_config: RemoteDataConfig,
    logger: ProcessLogger,
    source: str = "manual",
    on_finish: Callable[[str, str], None] | None = None,
    target_dates: Iterable[date] | None = None,
) -> None:
    final_status = "failed"
    try:
        if app_config.source_type == "metrix":
            logger.info(f"开始从平台储存下载，目录: {remote_config.remote_dir}")
        else:
            logger.info(
                f"开始远程下载，协议: {remote_config.protocol.upper()}，"
                f"服务器: {remote_config.host}:{remote_config.port}，目录: {remote_config.remote_dir}"
            )
        downloader = make_source_downloader(app_config, logger.info)
        download_result = downloader.download_to(work_dir, target_dates=target_dates)
        logger.success(
            f"下载完成，共 {download_result.file_count} 个文件，"
            f"{_format_bytes(download_result.total_bytes)}"
        )

        if download_result.file_count == 0:
            raise RuntimeError("源目录中未下载到任何文件")

        state.history_manager.update(task_id, file_count=download_result.file_count)

        _try_refresh_cell_data(app_config, work_dir, logger)

        if app_config.warehouse_type == "metrix":
            started = time.time()
            run_import_and_report(work_dir, app_config, logger)
            status, error, elapsed = "completed", None, round(time.time() - started, 2)
        else:
            logger.set_stage("license")
            log_license_check(logger, check_processing_allowed(work_dir))
            processor = DataProcessor(app_config, work_dir, logger)
            result = processor.process()
            status = "completed" if result.get("success") else "failed"
            error = result.get("error")
            elapsed = result.get("elapsed_time", 0)
        if status == "completed" and remote_config.auto_delete_source:
            try:
                deleted_count = downloader.delete_source_files(download_result.remote_files)
                logger.success(f"远程源文件清理完成，共删除 {deleted_count} 个文件，目录已保留")
                final_status = status
            except Exception as exc:
                logger.warning(f"远程源文件清理失败，数据处理结果已保留: {exc}")
                final_status = "source_cleanup_failed"
        else:
            final_status = status

        state.history_manager.update(
            task_id,
            status=status,
            elapsed_time=elapsed,
            error=error,
            result_tables=RESULT_TABLES,
        )
        state.processing_tasks[task_id] = {
            "logs": state.history_manager.get_logs(task_id),
            "status": status,
            "stage": status,
            "error": error,
        }
    except Exception as exc:
        error_detail = exc.to_detail() if isinstance(exc, LicenseError) else None
        if source == "scheduler":
            logger.error(f"自动调度任务失败: {exc}")
        else:
            logger.error(f"远程自动化任务失败: {exc}")
        state.history_manager.update(task_id, status="failed", error=str(exc))
        state.processing_tasks[task_id] = {
            "logs": state.history_manager.get_logs(task_id),
            "status": "failed",
            "stage": "failed",
            "error": str(exc),
            "error_detail": error_detail,
        }
    finally:
        apply_history_retention_safely()
        state.reset_task_lock()
        if on_finish:
            on_finish(task_id, final_status)


def _try_refresh_cell_data(app_config: AppConfig, work_dir: Path, logger: ProcessLogger) -> None:
    if not app_config.cell_data.remote_data.enabled:
        return
    logger.set_stage("cell_data")
    logger.info("── CellData 更新 ──")
    try:
        result = refresh_cell_data(app_config, work_dir, logger)
        logger.success(
            f"CellData 更新完成：{result.imported_rows} 行"
            f"（解析 {result.parsed_rows}，跳过 {result.skipped_rows}）"
        )
        execute_celldata_script(CELLDATA_SCRIPT, app_config, logger)
        copy_celldata_tables_to_capacity(app_config, logger)
    except Exception as exc:
        logger.warning(f"CellData 更新失败，继续容量处理: {exc}")


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
