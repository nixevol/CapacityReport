from pathlib import Path

from fastapi import APIRouter, Body, HTTPException

from app import state
from app.utils.files import format_size, get_dir_size


router = APIRouter(tags=["history"])


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

