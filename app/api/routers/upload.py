from datetime import datetime
from typing import Any, Optional

from fastapi import APIRouter, File, HTTPException, UploadFile

from app import state
from app.config import CACHE_DIR
from app.utils.files import safe_relative_path


router = APIRouter(tags=["upload"])


@router.post("/api/upload/create")
async def create_upload_session():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    work_dir = CACHE_DIR / session_id
    work_dir.mkdir(parents=True, exist_ok=True)

    state.upload_sessions[session_id] = {
        "work_dir": work_dir,
        "files": [],
        "created_at": datetime.now().isoformat(),
    }

    return {"success": True, "session_id": session_id, "work_dir": str(work_dir)}


@router.post("/api/upload")
async def upload_files(
    files: list[UploadFile] = File(...),
    session_id: Optional[str] = None,
):
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")

    is_new_session = False
    if not session_id or session_id not in state.upload_sessions:
        if state.global_task_lock["locked"]:
            raise HTTPException(status_code=409, detail="已有任务在运行，请等待当前任务完成")

        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        work_dir = CACHE_DIR / session_id
        work_dir.mkdir(parents=True, exist_ok=True)

        state.global_task_lock.update(
            {
                "locked": True,
                "task_id": session_id,
                "stage": "uploading",
                "started_at": datetime.now().isoformat(),
            }
        )
        is_new_session = True

        state.upload_sessions[session_id] = {
            "work_dir": work_dir,
            "files": [],
            "created_at": datetime.now().isoformat(),
        }
    else:
        if state.global_task_lock["locked"] and state.global_task_lock["task_id"] != session_id:
            raise HTTPException(status_code=409, detail="已有其他任务在运行")

    session: dict[str, Any] = state.upload_sessions[session_id]
    work_dir = session["work_dir"]

    try:
        saved_files: list[str] = []
        for file in files:
            if not file.filename:
                continue

            relative_path = safe_relative_path(file.filename)
            file_path = work_dir / relative_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_bytes(await file.read())

            saved_name = str(relative_path).replace("\\", "/")
            saved_files.append(saved_name)
            session["files"].append(saved_name)

        record = state.history_manager.get(session_id)
        if record:
            state.history_manager.update(session_id, file_count=len(session["files"]))
        else:
            state.history_manager.create(work_dir, len(session["files"]), record_id=session_id)

        return {
            "success": True,
            "task_id": session_id,
            "session_id": session_id,
            "work_dir": str(work_dir),
            "file_count": len(saved_files),
            "total_files": len(session["files"]),
            "files": saved_files,
        }
    except Exception as exc:
        if is_new_session:
            state.reset_task_lock()
        raise HTTPException(status_code=500, detail=f"上传失败: {exc}") from exc


@router.post("/api/upload/complete/{session_id}")
async def complete_upload_session(session_id: str):
    if session_id not in state.upload_sessions:
        raise HTTPException(status_code=404, detail="上传会话不存在")

    session = state.upload_sessions[session_id]
    state.history_manager.update(session_id, file_count=len(session["files"]))

    return {"success": True, "session_id": session_id, "total_files": len(session["files"])}
