import json
import re
from datetime import datetime
from typing import Any
from urllib.parse import quote

import pymysql
from fastapi import APIRouter, Body, HTTPException, UploadFile, File
from fastapi.responses import Response

from app import state
from app.config import (
    CellDataConfig,
    DataMappingsConfig,
    DEFAULT_CELL_DATA_MAPPING,
    HistoryRetentionConfig,
    MetrixConfig,
    MySQLConfig,
    RemoteDataConfig,
    SOURCE_TYPES,
    WAREHOUSE_TYPES,
)
from app.services.remote_download import RemoteDataDownloader


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


@router.post("/api/config/cell-data/remote")
async def update_cell_data_remote_config(config: dict[str, Any] = Body(...)):
    state.reload_config()
    current = state.config.cell_data.normalized()
    state.config.cell_data = CellDataConfig(
        remote_data=RemoteDataConfig.from_dict(config),
        mysql=current.mysql,
        scan_paths=current.scan_paths,
        year_dir_regex=current.year_dir_regex,
        month_dir_regex=current.month_dir_regex,
        day_dir_regex=current.day_dir_regex,
        file_name_regex=current.file_name_regex,
        file_time_regex=current.file_time_regex,
        mapping=current.mapping,
    ).normalized()
    state.config.save()
    return {"success": True, "message": "CellData 远程数据源配置已更新", "update": state.config.update}


@router.post("/api/config/cell-data/mysql")
async def update_cell_data_mysql_config(config: dict[str, Any] = Body(...)):
    state.reload_config()
    current = state.config.cell_data.normalized()
    state.config.cell_data = CellDataConfig(
        remote_data=current.remote_data,
        mysql=MySQLConfig.from_dict(config, default_dbname="celldata"),
        scan_paths=current.scan_paths,
        year_dir_regex=current.year_dir_regex,
        month_dir_regex=current.month_dir_regex,
        day_dir_regex=current.day_dir_regex,
        file_name_regex=current.file_name_regex,
        file_time_regex=current.file_time_regex,
        mapping=current.mapping,
    ).normalized()
    state.config.save()
    return {"success": True, "message": "CellData 数据库配置已更新", "update": state.config.update}


@router.post("/api/config/cell-data/remote/test")
async def test_cell_data_remote_connection(config: dict[str, Any] | None = Body(None)):
    try:
        remote_config = RemoteDataConfig.from_dict(config) if config else state.current_config().cell_data.remote_data
        RemoteDataDownloader(remote_config).test_connection()
        return {"success": True, "message": "CellData 远程服务器连接成功"}
    except Exception as exc:
        return {"success": False, "message": f"连接失败: {exc}"}


@router.post("/api/config/cell-data/mysql/test")
async def test_cell_data_mysql_connection(config: dict[str, Any] | None = Body(None)):
    mysql_config = MySQLConfig.from_dict(config, default_dbname="celldata") if config else state.current_config().cell_data.mysql
    return _test_mysql_config(mysql_config)


@router.post("/api/config/cell-data/settings")
async def update_cell_data_settings(config: dict[str, Any] = Body(...)):
    validation = _validate_cell_data_settings(config)
    if not validation["success"]:
        raise HTTPException(status_code=400, detail=validation["message"])
    state.reload_config()
    current = state.config.cell_data.normalized()
    state.config.cell_data = CellDataConfig(
        remote_data=current.remote_data,
        mysql=current.mysql,
        scan_paths=config.get("scan_paths", current.scan_paths),
        year_dir_regex=str(config.get("year_dir_regex", current.year_dir_regex)),
        month_dir_regex=str(config.get("month_dir_regex", current.month_dir_regex)),
        day_dir_regex=str(config.get("day_dir_regex", current.day_dir_regex)),
        file_name_regex=str(config.get("file_name_regex", current.file_name_regex)),
        file_time_regex=str(config.get("file_time_regex", current.file_time_regex)),
        mapping=config.get("mapping", current.mapping),
    ).normalized()
    state.config.save()
    return {"success": True, "message": "CellData 规则已更新", "update": state.config.update}


@router.post("/api/config/cell-data/settings/validate")
async def validate_cell_data_settings(config: dict[str, Any] = Body(...)):
    return _validate_cell_data_settings(config)


@router.get("/api/config/cell-data/mapping/default")
async def get_default_cell_data_mapping():
    return DEFAULT_CELL_DATA_MAPPING


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
        state.config.mysql = MySQLConfig.from_dict(mysql_data)

    if "SheetFilter" in data:
        state.config.sheet_filter = data["SheetFilter"] if isinstance(data["SheetFilter"], list) else []

    if "ExtractField" in data:
        state.config.extract_fields = data["ExtractField"] if isinstance(data["ExtractField"], list) else []

    remote_data = data.get("RemoteData")
    if isinstance(remote_data, dict):
        state.config.remote_data = RemoteDataConfig.from_dict(remote_data)

    cell_data = data.get("CellData")
    if isinstance(cell_data, dict):
        state.config.cell_data = CellDataConfig.from_dict(cell_data)

    history_retention = data.get("HistoryRetention")
    if isinstance(history_retention, dict):
        state.config.history_retention = HistoryRetentionConfig.from_dict(history_retention)


def _test_mysql_config(config: MySQLConfig) -> dict[str, Any]:
    normalized = config.normalized()
    try:
        conn = pymysql.connect(
            host=normalized.host,
            port=normalized.port,
            user=normalized.user,
            password=normalized.passwd,
            database=normalized.dbname,
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            connect_timeout=10,
        )
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
        finally:
            conn.close()
        return {"success": True, "message": "连接成功"}
    except Exception as exc:
        return {"success": False, "message": str(exc)}


def _validate_cell_data_settings(config: dict[str, Any]) -> dict[str, Any]:
    scan_paths = config.get("scan_paths", [])
    if not isinstance(scan_paths, list) or not any(str(path).strip() for path in scan_paths):
        return {"success": False, "message": "请至少配置一个扫描路径"}

    for key in ("year_dir_regex", "month_dir_regex", "day_dir_regex", "file_name_regex", "file_time_regex"):
        try:
            re.compile(str(config.get(key, "")))
        except re.error as exc:
            return {"success": False, "message": f"{key} 正则无效: {exc}"}

    mapping = config.get("mapping")
    if not isinstance(mapping, dict):
        return {"success": False, "message": "映射规则必须是 JSON 对象"}
    if not str(mapping.get("target_table", "")).strip():
        return {"success": False, "message": "映射规则缺少 target_table"}
    key_config = mapping.get("key")
    if not isinstance(key_config, dict) or not key_config.get("field") or not key_config.get("expr"):
        return {"success": False, "message": "映射规则缺少 key.field 或 key.expr"}
    sources = mapping.get("sources")
    if not isinstance(sources, list) or not sources:
        return {"success": False, "message": "映射规则至少需要一个 sources 项"}

    for index, source in enumerate(sources, 1):
        if not isinstance(source, dict):
            return {"success": False, "message": f"sources 第 {index} 项必须是对象"}
        if not source.get("band") or not source.get("file_prefix"):
            return {"success": False, "message": f"sources 第 {index} 项缺少 band 或 file_prefix"}
        fields = source.get("fields")
        if not isinstance(fields, dict) or not fields:
            return {"success": False, "message": f"sources 第 {index} 项缺少 fields"}
        for target, rule in fields.items():
            if not str(target).strip():
                return {"success": False, "message": f"sources 第 {index} 项存在空目标字段"}
            if isinstance(rule, str) and rule.strip():
                continue
            if isinstance(rule, dict) and "value" in rule:
                continue
            return {"success": False, "message": f"{target} 的映射规则无效"}
    return {"success": True, "message": "映射规则有效"}

