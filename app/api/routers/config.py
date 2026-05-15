import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Body, HTTPException, UploadFile, File
from fastapi.responses import FileResponse

from app import state
from app.config import CONFIG_FILE


router = APIRouter(tags=["config"])


@router.get("/api/config")
async def get_config():
    return state.config.to_dict()


@router.get("/api/config/full")
async def get_config_full():
    return state.config.to_dict_full()


@router.post("/api/config/mysql")
async def update_mysql_config(
    host: str = Body(...),
    port: int = Body(...),
    user: str = Body(...),
    passwd: str = Body(...),
    dbname: str = Body(...),
):
    state.config.mysql.host = host
    state.config.mysql.port = port
    state.config.mysql.user = user
    state.config.mysql.passwd = passwd
    state.config.mysql.dbname = dbname
    state.config.save()
    return {"success": True, "message": "数据库配置已更新", "update": state.config.update}


@router.post("/api/config/sheet-filter")
async def update_sheet_filter(filters: list[str] = Body(...)):
    state.config.sheet_filter = filters
    state.config.save()
    return {"success": True, "message": "Sheet 过滤规则已更新", "update": state.config.update}


@router.post("/api/config/extract-fields")
async def update_extract_fields(fields: list[dict[str, Any]] = Body(...)):
    state.config.extract_fields = fields
    state.config.save()
    return {"success": True, "message": "字段映射配置已更新", "update": state.config.update}


@router.get("/api/config/download")
async def download_config():
    if not CONFIG_FILE.exists():
        raise HTTPException(status_code=404, detail="配置文件不存在")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Configure_{timestamp}.json"
    return FileResponse(path=str(CONFIG_FILE), filename=filename, media_type="application/json")


@router.post("/api/config/upload")
async def upload_config(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="只支持 JSON 格式的配置文件")

    try:
        data = json.loads((await file.read()).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("配置文件格式错误：必须是 JSON 对象")

        _apply_config_data(data)
        state.config.save()
        return {"success": True, "message": "配置文件上传成功", "update": state.config.update}
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="配置文件格式错误：不是有效的 JSON 文件") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"上传失败: {exc}") from exc


def _apply_config_data(data: dict[str, Any]) -> None:
    mysql_data = data.get("MySQL_DBInfo")
    if isinstance(mysql_data, dict):
        for key in ("host", "port", "user", "passwd", "dbname"):
            if key in mysql_data:
                setattr(state.config.mysql, key, mysql_data[key])

    if "SheetFilter" in data:
        state.config.sheet_filter = data["SheetFilter"] if isinstance(data["SheetFilter"], list) else []

    if "ExtractField" in data:
        state.config.extract_fields = data["ExtractField"] if isinstance(data["ExtractField"], list) else []

