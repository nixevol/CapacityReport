from datetime import datetime
from typing import Optional

import pandas as pd
from fastapi import APIRouter, Body, HTTPException
from fastapi.responses import FileResponse

from app import state
from app.config import CACHE_DIR
from app.database import DatabaseManager


router = APIRouter(tags=["database"])


@router.post("/api/database/test")
async def test_database():
    db = DatabaseManager(state.config)
    try:
        success, message = db.test_connection()
        return {"success": success, "message": message}
    finally:
        db.dispose()


@router.get("/api/database/info")
async def get_database_info():
    db = DatabaseManager(state.config)
    try:
        return {"success": True, **db.get_server_info()}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
    finally:
        db.dispose()


@router.get("/api/database/tables")
@router.post("/api/database/tables")
async def get_tables():
    db = DatabaseManager(state.config)
    try:
        return {"tables": db.get_tables()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.dispose()


@router.post("/api/database/table/info")
async def get_table_info(table_name: str = Body(..., embed=True)):
    db = DatabaseManager(state.config)
    try:
        return db.get_table_info(table_name)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.dispose()


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
    finally:
        db.dispose()


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
    finally:
        db.dispose()


@router.post("/api/database/table/truncate")
async def truncate_table(table_name: str = Body(..., embed=True)):
    db = DatabaseManager(state.config)
    try:
        db.truncate_table(table_name)
        return {"success": True, "message": f"表 {table_name} 已清空"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.dispose()


@router.post("/api/database/table/drop")
async def drop_table(table_name: str = Body(..., embed=True)):
    db = DatabaseManager(state.config)
    try:
        db.drop_table(table_name)
        return {"success": True, "message": f"表 {table_name} 已删除"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.dispose()


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
    finally:
        db.dispose()


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
    finally:
        db.dispose()


@router.post("/api/download")
async def download_table(
    table_name: str = Body(..., embed=True),
    file_format: str = Body("csv", alias="format"),
):
    db = DatabaseManager(state.config)
    try:
        result = db.query_table(table_name, page=1, page_size=1000000)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        db.dispose()

    df = pd.DataFrame(result["data"])
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{table_name}_{timestamp}.{file_format}"
    filepath = CACHE_DIR / filename

    if file_format == "csv":
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        media_type = "text/csv"
    else:
        df.to_excel(filepath, index=False)
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    return FileResponse(path=str(filepath), filename=filename, media_type=media_type)

