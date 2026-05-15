from fastapi import APIRouter

from app.config import CACHE_DIR
from app.utils.files import format_size, get_dir_size


router = APIRouter(tags=["cache"])


@router.get("/api/cache/size")
async def get_cache_size():
    if not CACHE_DIR.exists():
        return {
            "success": True,
            "size_bytes": 0,
            "size_formatted": "0 B",
            "file_count": 0,
            "dir_count": 0,
        }

    total_size = 0
    file_count = 0
    dir_count = 0

    try:
        for item in CACHE_DIR.iterdir():
            if item.name == "history.json":
                continue
            if item.is_dir():
                dir_count += 1
            elif item.is_file():
                file_count += 1
            total_size += get_dir_size(item)
    except (PermissionError, OSError) as exc:
        return {"success": False, "error": str(exc), "size_formatted": "计算失败"}

    return {
        "success": True,
        "size_bytes": total_size,
        "size_formatted": format_size(total_size),
        "file_count": file_count,
        "dir_count": dir_count,
    }

