import zipfile
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Any

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


def _get_safe_work_dir(record_id: str, *, require_finished: bool = True) -> tuple[Path, str]:
    record = state.history_manager.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if require_finished and record.status in {"pending", "processing"}:
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


def _get_safe_history_path(record_id: str, relative_path: str | None, *, require_finished: bool = False) -> tuple[Path, Path, str]:
    work_dir, safe_record_id = _get_safe_work_dir(record_id, require_finished=require_finished)
    clean_path = _normalize_relative_path(relative_path)
    target = work_dir.joinpath(*clean_path.split("/")).resolve() if clean_path else work_dir

    try:
        target.relative_to(work_dir)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="历史文件路径不合法") from exc

    if not target.exists():
        raise HTTPException(status_code=404, detail="历史文件不存在")

    return work_dir, target, safe_record_id


def _normalize_relative_path(value: str | None) -> str:
    normalized = (value or "").replace("\\", "/").strip("/")
    if not normalized:
        return ""

    parts = [part for part in normalized.split("/") if part and part != "."]
    if any(part == ".." for part in parts):
        raise HTTPException(status_code=400, detail="历史文件路径不合法")
    return "/".join(parts)


def _zip_directory(source_dir: Path, archive_path: Path) -> None:
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        for item in source_dir.rglob("*"):
            arcname = item.relative_to(source_dir).as_posix()
            if item.is_dir():
                archive.writestr(f"{arcname}/", "")
            elif item.is_file():
                archive.write(item, arcname)


def _zip_history_item(source_path: Path, archive_path: Path) -> None:
    root_name = source_path.name or "history"
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED, allowZip64=True) as archive:
        if source_path.is_file():
            archive.write(source_path, root_name)
            return

        has_content = False
        for item in source_path.rglob("*"):
            has_content = True
            arcname = Path(root_name, item.relative_to(source_path)).as_posix()
            if item.is_dir():
                archive.writestr(f"{arcname}/", "")
            elif item.is_file():
                archive.write(item, arcname)

        if not has_content:
            archive.writestr(f"{root_name}/", "")


def _history_entry(item: Path, work_dir: Path) -> dict[str, Any]:
    stat = item.stat()
    is_dir = item.is_dir()
    size = get_dir_size(item) if is_dir else stat.st_size
    modified = datetime.fromtimestamp(stat.st_mtime)
    return {
        "name": item.name,
        "path": item.relative_to(work_dir).as_posix(),
        "type": "dir" if is_dir else "file",
        "size": size,
        "size_formatted": format_size(size),
        "modified": modified.isoformat(),
        "modified_formatted": modified.strftime("%Y-%m-%d %H:%M:%S"),
    }


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


@router.post("/api/history/files")
async def list_history_files(
    record_id: str = Body(..., embed=True),
    path: str | None = Body("", embed=True),
):
    work_dir, current_path, _safe_record_id = _get_safe_history_path(record_id, path)
    if not current_path.is_dir():
        raise HTTPException(status_code=400, detail="请选择目录")

    current_relative = current_path.relative_to(work_dir).as_posix()
    current_relative = "" if current_relative == "." else current_relative
    parent_relative = None
    if current_path != work_dir:
        parent_relative = current_path.parent.relative_to(work_dir).as_posix()
        parent_relative = "" if parent_relative == "." else parent_relative

    entries = [_history_entry(item, work_dir) for item in current_path.iterdir()]
    entries.sort(key=lambda item: (item["type"] != "dir", item["name"].lower()))
    return {
        "success": True,
        "record_id": record_id,
        "path": current_relative,
        "parent_path": parent_relative,
        "entries": entries,
    }


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


@router.post("/api/history/file/download")
async def download_history_file(
    record_id: str = Body(..., embed=True),
    path: str = Body(..., embed=True),
):
    _work_dir, target_path, safe_record_id = _get_safe_history_path(record_id, path, require_finished=True)
    if target_path.is_file():
        return FileResponse(
            path=str(target_path),
            filename=target_path.name,
            media_type="application/octet-stream",
        )

    if not target_path.is_dir():
        raise HTTPException(status_code=400, detail="历史文件类型不支持下载")

    export_dir = CACHE_DIR / ".downloads"
    export_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{_safe_filename_part(safe_record_id)}_{_safe_filename_part(target_path.name)}_{timestamp}.zip"
    archive_path = export_dir / filename

    try:
        _zip_history_item(target_path, archive_path)
    except Exception:
        _remove_file(archive_path)
        raise

    return FileResponse(
        path=str(archive_path),
        filename=filename,
        media_type="application/zip",
        background=BackgroundTask(_remove_file, archive_path),
    )
