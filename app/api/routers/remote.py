from datetime import datetime
from pathlib import Path
from threading import Thread
from typing import Any

from fastapi import APIRouter, Body, HTTPException

from app import state
from app.config import CACHE_DIR, RemoteDataConfig
from app.processor import DataProcessor, ProcessLogger
from app.services.remote_download import RemoteDataDownloader


router = APIRouter(tags=["remote"])


@router.post("/api/remote/test")
async def test_remote_connection(config: dict[str, Any] | None = Body(None)):
    remote_config = RemoteDataConfig.from_dict(config) if config else state.config.remote_data
    try:
        RemoteDataDownloader(remote_config).test_connection()
        return {"success": True, "message": "远程服务器连接成功"}
    except Exception as exc:
        return {"success": False, "message": f"远程服务器连接失败: {exc}"}


@router.post("/api/remote/start")
async def start_remote_processing():
    if state.global_task_lock["locked"]:
        raise HTTPException(status_code=409, detail="已有任务在运行，请等待当前任务完成")

    remote_config = state.config.remote_data.normalized()
    if not remote_config.enabled:
        raise HTTPException(status_code=400, detail="请先启用远程数据配置")

    task_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = CACHE_DIR / task_id
    work_dir.mkdir(parents=True, exist_ok=True)

    logs: list[str] = []

    def log_callback(message: str) -> None:
        logs.append(message)
        state.processing_tasks[task_id] = {"logs": logs.copy(), "status": "processing"}

    logger = ProcessLogger(log_file=work_dir / "log.txt", callback=log_callback)
    state.history_manager.create(work_dir, 0, record_id=task_id)
    state.history_manager.update(task_id, status="processing")
    state.processing_tasks[task_id] = {"logs": [], "status": "processing"}
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
        args=(task_id, work_dir, remote_config, logger),
        daemon=True,
    )
    thread.start()

    return {
        "success": True,
        "message": "远程下载处理任务已启动",
        "task_id": task_id,
        "stage": "downloading",
    }


def _run_remote_processing(
    task_id: str,
    work_dir: Path,
    remote_config: RemoteDataConfig,
    logger: ProcessLogger,
) -> None:
    try:
        logger.info(
            f"开始远程下载，协议: {remote_config.protocol.upper()}，"
            f"服务器: {remote_config.host}:{remote_config.port}，目录: {remote_config.remote_dir}"
        )
        downloader = RemoteDataDownloader(remote_config, logger.info)
        download_result = downloader.download_to(work_dir)
        logger.success(
            f"远程下载完成，共 {download_result.file_count} 个文件，"
            f"{_format_bytes(download_result.total_bytes)}"
        )

        if download_result.file_count == 0:
            raise RuntimeError("远程目录中未下载到任何文件")

        state.history_manager.update(task_id, file_count=download_result.file_count)
        state.global_task_lock["stage"] = "processing"

        processor = DataProcessor(state.config, work_dir, logger)
        result = processor.process()
        status = "completed" if result.get("success") else "failed"
        if status == "completed" and remote_config.auto_delete_source:
            try:
                deleted_count = downloader.delete_source_files(download_result.remote_files)
                logger.success(f"远程源文件清理完成，共删除 {deleted_count} 个文件，目录已保留")
            except Exception as exc:
                logger.warning(f"远程源文件清理失败，数据处理结果已保留: {exc}")

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
        logger.error(f"远程自动化任务失败: {exc}")
        state.history_manager.update(task_id, status="failed", error=str(exc))
        state.processing_tasks[task_id] = {
            "logs": state.history_manager.get_logs(task_id),
            "status": "failed",
        }
    finally:
        state.reset_task_lock()


def _format_bytes(size: int) -> str:
    value = float(size)
    for unit in ("B", "KB", "MB", "GB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TB"
