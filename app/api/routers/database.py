import re
from contextlib import suppress
from datetime import datetime
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from app import state
from app.config import CACHE_DIR
from app.database import DatabaseManager


router = APIRouter(tags=["database"])
INVALID_SHEET_NAME_CHARS = re.compile(r"[:\\/?*\[\]]")


def _remove_file(path: Path) -> None:
    with suppress(OSError):
        path.unlink()


def _resolve_requested_tables(
    table_name: Optional[str],
    table_names: Optional[list[str]],
) -> list[str]:
    names = table_names if table_names is not None else ([table_name] if table_name else [])
    return [name.strip() for name in names if isinstance(name, str) and name.strip()]


def _make_sheet_name(table_name: str, used_names: set[str]) -> str:
    base = INVALID_SHEET_NAME_CHARS.sub("_", table_name).strip("'").strip() or "Sheet"
    base = base[:31]
    sheet_name = base
    index = 2

    while sheet_name in used_names:
        suffix = f"_{index}"
        sheet_name = f"{base[:31 - len(suffix)]}{suffix}" or f"Sheet_{index}"
        index += 1

    used_names.add(sheet_name)
    return sheet_name


def _dataframe_from_table(db: DatabaseManager, table_name: str) -> pd.DataFrame:
    result = db.query_table(table_name, page=1, page_size=1000000)
    table_info = db.get_table_info(table_name)
    columns = [str(column["Field"]) for column in table_info["columns"]]
    return pd.DataFrame(result["data"], columns=columns)


@router.post("/api/database/test")
async def test_database():
    db = DatabaseManager(state.config)
    success, message = db.test_connection()
    return {"success": success, "message": message}


@router.get("/api/database/info")
async def get_database_info():
    db = DatabaseManager(state.config)
    try:
        return {"success": True, **db.get_server_info()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


@router.get("/api/database/tables")
@router.post("/api/database/tables")
async def get_tables():
    db = DatabaseManager(state.config)
    try:
        return {"tables": db.get_tables()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/database/table/info")
async def get_table_info(table_name: str = Body(..., embed=True)):
    db = DatabaseManager(state.config)
    try:
        return db.get_table_info(table_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/database/table/data")
async def query_table_data(
    table_name: str = Body(..., embed=True),
    page: int = Body(1),
    page_size: int = Body(50),
    order_by: Optional[str] = Body(None),
    order_dir: str = Body("ASC"),
):
    db = DatabaseManager(state.config)
    try:
        return db.query_table(table_name, page, page_size, order_by=order_by, order_dir=order_dir)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/database/table/query")
async def query_table_with_filter(
    table_name: str = Body(..., embed=True),
    page: int = Body(1),
    page_size: int = Body(50),
    filters: Optional[dict[str, str]] = Body(None),
    order_by: Optional[str] = Body(None),
    order_dir: str = Body("ASC"),
):
    db = DatabaseManager(state.config)
    try:
        return db.query_table(
            table_name,
            page,
            page_size,
            filters=filters or {},
            order_by=order_by,
            order_dir=order_dir,
        )
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/database/table/truncate")
async def truncate_table(table_name: str = Body(..., embed=True)):
    db = DatabaseManager(state.config)
    try:
        db.truncate_table(table_name)
        return {"success": True, "message": f"表 {table_name} 已清空"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/database/table/drop")
async def drop_table(table_name: str = Body(..., embed=True)):
    db = DatabaseManager(state.config)
    try:
        db.drop_table(table_name)
        return {"success": True, "message": f"表 {table_name} 已删除"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/database/table/drop-all")
async def drop_all_tables():
    db = DatabaseManager(state.config)
    try:
        result = db.drop_all_tables()
        return {
            "success": True,
            "message": f"已删除 {result['dropped_count']} 个表",
            "dropped_count": result["dropped_count"],
            "tables": result["tables"],
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/database/execute")
async def execute_sql(sql: str = Body(..., embed=True)):
    db = DatabaseManager(state.config)
    try:
        success, result = db.execute_sql(sql)
        if success:
            return {"success": True, "result": result}
        raise HTTPException(status_code=400, detail=result)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@router.post("/api/download")
async def download_table(
    table_name: Optional[str] = Body(None, embed=True),
    table_names: Optional[list[str]] = Body(None, embed=True),
    file_format: str = Body("csv", alias="format"),
):
    if file_format not in {"csv", "xlsx"}:
        raise HTTPException(status_code=400, detail="不支持的导出格式")

    requested_tables = _resolve_requested_tables(table_name, table_names)
    if not requested_tables:
        raise HTTPException(status_code=400, detail="请选择要导出的数据表")
    if file_format == "csv" and len(requested_tables) != 1:
        raise HTTPException(status_code=400, detail="CSV 每次只能导出一张表")

    db = DatabaseManager(state.config)
    try:
        available_tables = set(db.get_tables())
        missing_tables = [name for name in requested_tables if name not in available_tables]
        if missing_tables:
            raise HTTPException(status_code=400, detail=f"数据表不存在: {', '.join(missing_tables)}")

        table_frames = {
            name: _dataframe_from_table(db, name)
            for name in requested_tables
        }
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename_prefix = requested_tables[0] if len(requested_tables) == 1 else "tables"
    filename = f"{filename_prefix}_{timestamp}.{file_format}"
    filepath = CACHE_DIR / filename
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    try:
        if file_format == "csv":
            table_frames[requested_tables[0]].to_csv(filepath, index=False, encoding="utf-8-sig")
            media_type = "text/csv"
        else:
            used_sheet_names: set[str] = set()
            with pd.ExcelWriter(filepath) as writer:
                for name, df in table_frames.items():
                    df.to_excel(writer, sheet_name=_make_sheet_name(name, used_sheet_names), index=False)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    except Exception:
        _remove_file(filepath)
        raise

    return FileResponse(
        path=str(filepath),
        filename=filename,
        media_type=media_type,
        background=BackgroundTask(_remove_file, filepath),
    )
