import zipfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app import state
from app.config import CACHE_DIR
from app.utils.files import format_size, get_dir_size


router = APIRouter(tags=["history"])


def _remove_file(path: Path) -> None:
    with suppress(OSError):
        path.unlink()


def _safe_filename_part(value: str) -> str:
    safe = "".join(char if char.isalnum() or char in {"-", "_"} else "_" for char in value)
    return safe.strip("_") or "history"


def _get_safe_work_dir(record_id: str) -> tuple[Path, str]:
    record = state.history_manager.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if record.status in {"pending", "processing"}:
        raise HTTPException(status_code=409, detail="任务尚未完成，暂不能下载历史数据")

    work_dir = Path(record.work_dir).resolve()
    cache_dir = CACHE_DIR.resolve()
    try:
        work_dir.relative_to(cache_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="历史目录不合法") from exc

    if not work_dir.exists() or not work_dir.is_dir():
        raise HTTPException(status_code=404, detail="历史数据目录不存在")

    return work_dir, record.id


def _zip_directory(source_dir: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for item in source_dir.rglob("*"):
            arcname = item.relative_to(source_dir).as_posix()
            if item.is_dir():
                archive.writestr(f"{arcname}/", "")
            elif item.is_file():
                archive.write(item, arcname)


@router.post("/api/history")
async def get_history(limit: int = Body(50, embed=True)):
    return {"records": state.history_manager.list(limit)}


@router.post("/api/history/delete")
async def delete_history(record_id: str = Body(..., embed=True)):
    if state.history_manager.delete(record_id):
        return {"success": True, "message": "删除成功"}
    raise HTTPException(status_code=404, detail="记录不存在")


@router.post("/api/history/clear")
async def clear_history():
    count = state.history_manager.clear()
    return {"success": True, "deleted": count}


@router.post("/api/history/detail")
async def get_history_detail(record_id: str = Body(..., embed=True)):
    record = state.history_manager.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    result = record.to_dict()
    result["logs"] = state.history_manager.get_logs(record_id)
    return result


@router.post("/api/history/size")
async def get_history_size(record_id: str = Body(..., embed=True)):
    record = state.history_manager.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    work_dir = Path(record.work_dir)
    if not work_dir.exists():
        return {"success": True, "size": 0, "size_formatted": "0 B"}

    size = get_dir_size(work_dir)
    return {"success": True, "size": size, "size_formatted": format_size(size)}


@router.post("/api/history/download")
async def download_history(record_id: str = Body(..., embed=True)):
    work_dir, safe_record_id = _get_safe_work_dir(record_id)
    export_dir = CACHE_DIR / ".downloads"
    export_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_safe_filename_part(safe_record_id)}_{timestamp}.zip"
    archive_path = export_dir / filename

    try:
        _zip_directory(work_dir, archive_path)
    except Exception:
        _remove_file(archive_path)
        raise

    return FileResponse(
        path=str(archive_path),
        filename=filename,
        media_type="application/zip",
        background=BackgroundTask(_remove_file, archive_path),
    )
