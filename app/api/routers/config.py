import json
from datetime import datetime
from typing import Any
from urllib.parse import quote

from fastapi import APIRouter, Body, HTTPException, UploadFile, File
from fastapi.responses import Response

from app import state
from app.config import (
    DataMappingsConfig,
    HistoryRetentionConfig,
    MetrixConfig,
    RemoteDataConfig,
    SOURCE_TYPES,
    WAREHOUSE_TYPES,
)


router = APIRouter(tags=["config"])


@router.get("/api/config")
async def get_config():
    return state.current_config().to_dict()


@router.get("/api/config/full")
async def get_config_full():
    return state.current_config().to_dict_full()


@router.post("/api/config/mysql")
async def update_mysql_config(
    host: str = Body(...),
    port: int = Body(...),
    user: str = Body(...),
    passwd: str = Body(...),
    dbname: str = Body(...),
):
    state.reload_config()
    state.config.mysql.host = host
    state.config.mysql.port = port
    state.config.mysql.user = user
    state.config.mysql.passwd = passwd
    state.config.mysql.dbname = dbname
    state.config.save()
    return {"success": True, "message": "数据库配置已更新", "update": state.config.update}


@router.post("/api/config/remote")
async def update_remote_config(config: dict[str, Any] = Body(...)):
    state.reload_config()
    state.config.remote_data = RemoteDataConfig.from_dict(config)
    state.config.save()
    return {"success": True, "message": "远程数据配置已更新", "update": state.config.update}


@router.post("/api/config/backend")
async def update_backend(
    source_type: str = Body(...),
    warehouse_type: str = Body(...),
):
    if source_type not in SOURCE_TYPES:
        raise HTTPException(status_code=400, detail="不支持的源类型")
    if warehouse_type not in WAREHOUSE_TYPES:
        raise HTTPException(status_code=400, detail="不支持的仓库类型")
    state.reload_config()
    state.config.source_type = source_type
    state.config.warehouse_type = warehouse_type
    state.config.save()
    return {"success": True, "message": "后端类型已更新", "update": state.config.update}


@router.post("/api/config/metrix")
async def update_metrix_config(config: dict[str, Any] = Body(...)):
    state.reload_config()
    state.config.metrix = MetrixConfig.from_dict(config)
    state.config.save()
    return {"success": True, "message": "Metrix 连接配置已更新", "update": state.config.update}


@router.post("/api/config/data-mappings")
async def update_data_mappings_config(config: dict[str, Any] = Body(...)):
    state.reload_config()
    current = state.config.data_mappings.normalized()
    payload = dict(config)
    if "table_field_mappings" not in payload:
        payload["table_field_mappings"] = current.table_field_mappings
    state.config.data_mappings = DataMappingsConfig.from_dict(payload)
    state.config.save()
    return {"success": True, "message": "数据目录映射已更新", "update": state.config.update}


@router.post("/api/config/history-retention")
async def update_history_retention(config: dict[str, Any] = Body(...)):
    state.reload_config()
    state.config.history_retention = HistoryRetentionConfig.from_dict(config)
    state.config.save()
    return {"success": True, "message": "处理历史保留配置已更新", "update": state.config.update}


@router.post("/api/config/sheet-filter")
async def update_sheet_filter(filters: list[str] = Body(...)):
    state.reload_config()
    state.config.sheet_filter = filters
    state.config.save()
    return {"success": True, "message": "Sheet 过滤规则已更新", "update": state.config.update}


@router.post("/api/config/extract-fields")
async def update_extract_fields(fields: list[dict[str, Any]] = Body(...)):
    state.reload_config()
    state.config.extract_fields = fields
    state.config.save()
    return {"success": True, "message": "字段映射配置已更新", "update": state.config.update}


@router.get("/api/config/download")
async def download_config():
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"Configure_{timestamp}.json"
    config_data = state.current_config().to_file_dict()
    content = json.dumps(config_data, ensure_ascii=False, indent=2)
    return Response(
        content=content,
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}"},
    )


@router.post("/api/config/upload")
async def upload_config(file: UploadFile = File(...)):
    if not file.filename or not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="只支持 JSON 格式的配置文件")

    try:
        data = json.loads((await file.read()).decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("配置文件格式错误：必须是 JSON 对象")

        state.reload_config()
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
    if data.get("SourceType") in SOURCE_TYPES:
        state.config.source_type = data["SourceType"]
    if data.get("WarehouseType") in WAREHOUSE_TYPES:
        state.config.warehouse_type = data["WarehouseType"]

    metrix_data = data.get("Metrix")
    if isinstance(metrix_data, dict):
        state.config.metrix = MetrixConfig.from_dict(metrix_data)

    data_mappings = data.get("DataMappings")
    if isinstance(data_mappings, dict):
        state.config.data_mappings = DataMappingsConfig.from_dict(data_mappings)

    mysql_data = data.get("MySQL_DBInfo")
    if isinstance(mysql_data, dict):
        for key in ("host", "port", "user", "passwd", "dbname"):
            if key in mysql_data:
                setattr(state.config.mysql, key, mysql_data[key])

    if "SheetFilter" in data:
        state.config.sheet_filter = data["SheetFilter"] if isinstance(data["SheetFilter"], list) else []

    if "ExtractField" in data:
        state.config.extract_fields = data["ExtractField"] if isinstance(data["ExtractField"], list) else []

    remote_data = data.get("RemoteData")
    if isinstance(remote_data, dict):
        state.config.remote_data = RemoteDataConfig.from_dict(remote_data)

    history_retention = data.get("HistoryRetention")
    if isinstance(history_retention, dict):
        state.config.history_retention = HistoryRetentionConfig.from_dict(history_retention)

