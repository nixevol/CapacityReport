"""
CapacityReport - 容量报表处理程序
FastAPI 主入口
"""
import os
import sys
import signal
import shutil
import asyncio
import subprocess
import platform
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional
from threading import Thread

from fastapi import FastAPI, File, UploadFile, HTTPException, Query, Body
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware

from app.config import AppConfig, CACHE_DIR, BASE_DIR
from app.database import DatabaseManager
from app.processor import DataProcessor, ProcessLogger
from app.history import HistoryManager


# 创建应用
app = FastAPI(
    title="CapacityReport",
    description="容量报表数据处理系统",
    version="2.0.0"
)

# CORS 配置
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 静态文件
STATIC_DIR = BASE_DIR / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# 全局状态
config = AppConfig.load()
history_manager = HistoryManager()
processing_tasks: Dict[str, Dict[str, Any]] = {}

# 全局任务锁定状态（上传中或处理中）
global_task_lock: Dict[str, Any] = {
    "locked": False,
    "task_id": None,
    "stage": None,  # "uploading" 或 "processing"
    "started_at": None
}


# ==================== 健康检查 ====================

@app.get("/health")
async def health_check():
    """
    健康检查接口（用于 Docker/K8s 健康检查）
    
    返回:
        - status: 服务状态 (healthy/unhealthy)
        - timestamp: 当前时间戳
        - version: 应用版本
        - checks: 各组件检查结果
    """
    checks = {
        "app": {"status": "ok"},
        "database": {"status": "unknown"},
    }
    
    # 检查数据库连接
    try:
        db_manager = DatabaseManager(config.mysql_config)
        server_info = db_manager.get_server_info()
        if server_info:
            checks["database"] = {
                "status": "ok",
                "version": server_info.get("version", "unknown"),
                "load_data_infile": server_info.get("load_data_support", False)
            }
        else:
            checks["database"] = {"status": "error", "message": "无法获取数据库信息"}
    except Exception as e:
        checks["database"] = {"status": "error", "message": str(e)}
    
    # 综合判断健康状态
    is_healthy = all(
        c.get("status") == "ok" 
        for c in checks.values()
    )
    
    return {
        "status": "healthy" if is_healthy else "unhealthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "uptime_pid": os.getpid(),
        "checks": checks
    }


# ==================== 页面路由 ====================

@app.get("/", response_class=HTMLResponse)
async def index():
    """返回主页"""
    index_file = STATIC_DIR / "index.html"
    if index_file.exists():
        return HTMLResponse(content=index_file.read_text(encoding='utf-8'))
    return HTMLResponse(content="<h1>CapacityReport</h1><p>Static files not found.</p>")


# ==================== 文件上传 API ====================

# 存储进行中的上传任务
upload_sessions: Dict[str, Dict[str, Any]] = {}


@app.post("/api/upload/create")
async def create_upload_session():
    """
    创建上传会话
    返回 session_id，后续上传文件使用这个 ID
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    session_id = timestamp
    work_dir = CACHE_DIR / timestamp
    work_dir.mkdir(parents=True, exist_ok=True)
    
    upload_sessions[session_id] = {
        "work_dir": work_dir,
        "files": [],
        "created_at": datetime.now().isoformat()
    }
    
    return {
        "success": True,
        "session_id": session_id,
        "work_dir": str(work_dir)
    }


@app.post("/api/upload")
async def upload_files(
    files: List[UploadFile] = File(...),
    session_id: Optional[str] = None
):
    """
    上传文件
    支持多文件上传，会保持目录结构
    如果提供 session_id，则追加到现有会话
    上传前会检查并锁定全局任务状态
    """
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")
    
    is_new_session = False
    # 检查全局锁定状态（如果是新会话）
    if not session_id or session_id not in upload_sessions:
        if global_task_lock["locked"]:
            raise HTTPException(status_code=409, detail="已有任务在运行，请等待当前任务完成")
        
        # 创建新会话并立即锁定
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        session_id = timestamp
        work_dir = CACHE_DIR / timestamp
        work_dir.mkdir(parents=True, exist_ok=True)
        
        # 立即锁定全局任务
        global_task_lock["locked"] = True
        global_task_lock["task_id"] = session_id
        global_task_lock["stage"] = "uploading"
        global_task_lock["started_at"] = datetime.now().isoformat()
        is_new_session = True
        
        upload_sessions[session_id] = {
            "work_dir": work_dir,
            "files": [],
            "created_at": datetime.now().isoformat()
        }
        session = upload_sessions[session_id]
    else:
        # 使用现有会话（追加文件）
        work_dir = upload_sessions[session_id]["work_dir"]
        session = upload_sessions[session_id]
        # 验证会话是否属于当前锁定的任务
        if global_task_lock["locked"] and global_task_lock["task_id"] != session_id:
            raise HTTPException(status_code=409, detail="已有其他任务在运行")
    
    try:
        saved_files = []
        for file in files:
            # 保持目录结构
            # 文件名可能包含路径，如 "4G/data.xlsx"
            file_path = work_dir / file.filename
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # 保存文件
            content = await file.read()
            file_path.write_bytes(content)
            saved_files.append(file.filename)
            session["files"].append(file.filename)
        
        # 创建或更新历史记录（使用 session_id 作为记录 ID）
        record = history_manager.get(session_id)
        if not record:
            record = history_manager.create(work_dir, len(session["files"]), record_id=session_id)
        else:
            history_manager.update(session_id, file_count=len(session["files"]))
        
        return {
            "success": True,
            "task_id": session_id,
            "session_id": session_id,
            "work_dir": str(work_dir),
            "file_count": len(saved_files),
            "total_files": len(session["files"]),
            "files": saved_files
        }
    except Exception as e:
        # 上传失败，如果是新会话则解锁
        if is_new_session:
            global_task_lock["locked"] = False
            global_task_lock["task_id"] = None
            global_task_lock["stage"] = None
            global_task_lock["started_at"] = None
        raise HTTPException(status_code=500, detail=f"上传失败: {str(e)}")


@app.post("/api/upload/complete/{session_id}")
async def complete_upload_session(session_id: str):
    """
    完成上传会话
    """
    if session_id not in upload_sessions:
        raise HTTPException(status_code=404, detail="上传会话不存在")
    
    session = upload_sessions[session_id]
    
    # 更新历史记录
    history_manager.update(session_id, file_count=len(session["files"]))
    
    # 清理会话（保留一段时间）
    # upload_sessions.pop(session_id, None)
    
    return {
        "success": True,
        "session_id": session_id,
        "total_files": len(session["files"])
    }


# ==================== 处理任务 API ====================

@app.get("/api/routes")
async def list_routes():
    """列出所有注册的路由（调试用）"""
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append({
                "path": route.path,
                "name": route.name if hasattr(route, 'name') else None,
                "methods": list(route.methods) if hasattr(route, 'methods') else None
            })
    return {"routes": routes}


@app.post("/api/process/start/test")
async def test_process_start():
    """测试 /api/process/start 路由是否可访问"""
    return {"success": True, "message": "/api/process/start 路由可访问"}


@app.get("/api/task/test")
async def test_task_api():
    """测试任务API是否正常工作"""
    return {"success": True, "message": "任务API正常工作", "lock_status": global_task_lock}


@app.get("/api/task/status")
async def get_global_task_status():
    """获取全局任务状态（是否有任务在上传或处理中）"""
    # 自动清理：如果任务已完成但还锁定，则自动解锁
    if global_task_lock["locked"]:
        task_id = global_task_lock["task_id"]
        if task_id:
            # 检查任务是否已完成
            record = history_manager.get(task_id)
            if record and record.status in ["completed", "failed"]:
                # 任务已完成但还锁定，自动解锁
                global_task_lock["locked"] = False
                global_task_lock["task_id"] = None
                global_task_lock["stage"] = None
                global_task_lock["started_at"] = None
                return {"has_active": False}
            
            # 检查内存中的任务状态
            if task_id in processing_tasks:
                task_status = processing_tasks[task_id].get("status")
                if task_status in ["completed", "failed"]:
                    # 任务已完成但还锁定，自动解锁
                    global_task_lock["locked"] = False
                    global_task_lock["task_id"] = None
                    global_task_lock["stage"] = None
                    global_task_lock["started_at"] = None
                    return {"has_active": False}
        
        # 任务还在进行中
        return {
            "has_active": True,
            "task_id": global_task_lock["task_id"],
            "stage": global_task_lock["stage"],
            "started_at": global_task_lock["started_at"],
            "logs": []
        }
    
    # 检查内存中正在处理的任务
    active_tasks = {k: v for k, v in processing_tasks.items() if v.get("status") == "processing"}
    if active_tasks:
        task_id = list(active_tasks.keys())[0]
        return {
            "has_active": True,
            "task_id": task_id,
            "stage": "processing",
            "logs": active_tasks[task_id].get("logs", [])
        }
    
    # 不检查历史记录，因为历史记录可能是旧的状态
    # 如果服务器重启，历史记录中的 "processing" 状态可能是过期的
    
    return {"has_active": False}


@app.post("/api/task/lock")
async def lock_task(task_id: str = Body(..., embed=True)):
    """锁定全局任务状态（开始上传时调用）"""
    if global_task_lock["locked"]:
        raise HTTPException(status_code=409, detail="已有任务在运行")
    
    global_task_lock["locked"] = True
    global_task_lock["task_id"] = task_id
    global_task_lock["stage"] = "uploading"
    global_task_lock["started_at"] = datetime.now().isoformat()
    
    return {"success": True, "message": "任务已锁定"}


@app.post("/api/task/unlock")
async def unlock_task(task_id: str = Body(None, embed=True)):
    """解锁全局任务状态（上传失败或取消时调用）"""
    # 只有锁定者或管理员可以解锁
    if task_id and global_task_lock["task_id"] != task_id:
        raise HTTPException(status_code=403, detail="无权解锁此任务")
    
    global_task_lock["locked"] = False
    global_task_lock["task_id"] = None
    global_task_lock["stage"] = None
    global_task_lock["started_at"] = None
    
    return {"success": True, "message": "任务已解锁"}


@app.get("/api/process/active")
async def get_active_task():
    """获取当前正在进行的任务（全局状态）- 兼容旧接口"""
    return await get_global_task_status()


@app.post("/api/process/start")
async def start_processing(task_id: str = Body(..., embed=True)):
    """启动数据处理任务（task_id 放在 POST body 中）"""
    record = history_manager.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    if record.status == "processing":
        raise HTTPException(status_code=400, detail="任务正在处理中")
    
    work_dir = Path(record.work_dir)
    if not work_dir.exists():
        raise HTTPException(status_code=400, detail="工作目录不存在")
    
    # 创建日志记录器（实时写入 log.txt）
    log_file = work_dir / "log.txt"
    logs: List[str] = []
    def log_callback(msg: str):
        logs.append(msg)
        processing_tasks[task_id] = {"logs": logs, "status": "processing"}
    
    logger = ProcessLogger(log_file=log_file, callback=log_callback)
    
    # 更新状态
    history_manager.update(task_id, status="processing")
    processing_tasks[task_id] = {"logs": logs, "status": "processing"}
    
    # 更新全局锁定状态为处理中
    global_task_lock["locked"] = True
    global_task_lock["task_id"] = task_id
    global_task_lock["stage"] = "processing"
    global_task_lock["started_at"] = datetime.now().isoformat()
    
    # 在后台线程执行处理
    def run_processing():
        try:
            processor = DataProcessor(config, work_dir, logger)
            result = processor.process()
            
            # 更新历史记录（日志已写入文件，不需要再保存）
            status = "completed" if result.get("success") else "failed"
            history_manager.update(
                task_id,
                status=status,
                elapsed_time=result.get("elapsed_time", 0),
                error=result.get("error"),
                result_tables=["4G_结果表", "5G_结果表"]
            )
            # 从文件读取最新日志
            logs_from_file = history_manager.get_logs(task_id)
            processing_tasks[task_id] = {"logs": logs_from_file, "status": status}
            # 处理完成，解锁全局状态
            global_task_lock["locked"] = False
            global_task_lock["task_id"] = None
            global_task_lock["stage"] = None
            global_task_lock["started_at"] = None
        except Exception as e:
            history_manager.update(task_id, status="failed", error=str(e))
            # 从文件读取最新日志
            logs_from_file = history_manager.get_logs(task_id)
            processing_tasks[task_id] = {"logs": logs_from_file, "status": "failed"}
            # 处理失败，解锁全局状态
            global_task_lock["locked"] = False
            global_task_lock["task_id"] = None
            global_task_lock["stage"] = None
            global_task_lock["started_at"] = None
    
    thread = Thread(target=run_processing)
    thread.start()
    
    return {"success": True, "message": "处理任务已启动", "task_id": task_id}


@app.post("/api/process/status")
async def get_processing_status(task_id: str = Body(..., embed=True)):
    """获取处理任务状态和日志（task_id 放在 POST body 中）"""
    # 优先从文件读取日志（实时写入，保证最新）
    logs = history_manager.get_logs(task_id)
    
    # 检查内存中的实时状态（用于获取状态）
    if task_id in processing_tasks:
        return {
            "task_id": task_id,
            "status": processing_tasks[task_id]["status"],
            "logs": logs  # 使用文件中的日志
        }
    
    # 从历史记录获取
    record = history_manager.get(task_id)
    if not record:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return {
        "task_id": task_id,
        "status": record.status,
        "logs": logs,
        "elapsed_time": record.elapsed_time,
        "error": record.error
    }


# ==================== 历史记录 API ====================

@app.post("/api/history")
async def get_history(limit: int = Body(50, embed=True)):
    """获取处理历史记录"""
    records = history_manager.list(limit)
    return {"records": records}


@app.post("/api/history/delete")
async def delete_history(record_id: str = Body(..., embed=True)):
    """删除历史记录"""
    if history_manager.delete(record_id):
        return {"success": True, "message": "删除成功"}
    raise HTTPException(status_code=404, detail="记录不存在")


@app.post("/api/history/clear")
async def clear_history():
    """清空所有历史记录"""
    count = history_manager.clear()
    return {"success": True, "deleted": count}


@app.post("/api/history/detail")
async def get_history_detail(record_id: str = Body(..., embed=True)):
    """获取历史记录详情（record_id 放在 POST body 中）"""
    record = history_manager.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    # 从文件读取日志
    logs = history_manager.get_logs(record_id)
    result = record.to_dict()
    result["logs"] = logs
    
    return result


# ==================== 数据库管理 API ====================

@app.post("/api/database/test")
async def test_database():
    """测试数据库连接"""
    db = DatabaseManager(config)
    success, message = db.test_connection()
    db.dispose()
    return {"success": success, "message": message}


@app.get("/api/database/info")
async def get_database_info():
    """获取数据库服务器信息（包括是否支持 LOAD DATA INFILE）"""
    db = DatabaseManager(config)
    try:
        info = db.get_server_info()
        return {"success": True, **info}
    except Exception as e:
        return {"success": False, "error": str(e)}
    finally:
        db.dispose()


@app.get("/api/database/tables")
@app.post("/api/database/tables")
async def get_tables():
    """获取所有表（支持 GET 和 POST，无需传参）"""
    try:
        db = DatabaseManager(config)
        tables = db.get_tables()
        db.dispose()
        return {"tables": tables}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/database/table/info")
async def get_table_info(table_name: str = Body(..., embed=True)):
    """获取表信息（table_name 放在 POST body 中）"""
    try:
        db = DatabaseManager(config)
        info = db.get_table_info(table_name)
        db.dispose()
        return info
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/database/table/data")
async def query_table_data(
    table_name: str = Body(..., embed=True),
    page: int = Body(1),
    page_size: int = Body(50),
    order_by: Optional[str] = Body(None),
    order_dir: str = Body("ASC")
):
    """分页查询表数据（参数放在 POST body 中）"""
    try:
        db = DatabaseManager(config)
        result = db.query_table(table_name, page, page_size, order_by=order_by, order_dir=order_dir)
        db.dispose()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/database/table/query")
async def query_table_with_filter(
    table_name: str = Body(..., embed=True),
    page: int = Body(1),
    page_size: int = Body(50),
    filters: Dict[str, str] = Body(default={}),
    order_by: Optional[str] = Body(None),
    order_dir: str = Body("ASC")
):
    """带筛选条件查询表数据（参数放在 POST body 中）"""
    try:
        db = DatabaseManager(config)
        result = db.query_table(table_name, page, page_size, filters=filters, order_by=order_by, order_dir=order_dir)
        db.dispose()
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/database/table/truncate")
async def truncate_table(table_name: str = Body(..., embed=True)):
    """清空表数据（table_name 放在 POST body 中）"""
    try:
        db = DatabaseManager(config)
        db.truncate_table(table_name)
        db.dispose()
        return {"success": True, "message": f"表 {table_name} 已清空"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/database/table/drop")
async def drop_table(table_name: str = Body(..., embed=True)):
    """删除表（table_name 放在 POST body 中）"""
    try:
        db = DatabaseManager(config)
        db.drop_table(table_name)
        db.dispose()
        return {"success": True, "message": f"表 {table_name} 已删除"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/database/execute")
async def execute_sql(sql: str = Body(..., embed=True)):
    """执行自定义 SQL"""
    try:
        db = DatabaseManager(config)
        success, result = db.execute_sql(sql)
        db.dispose()
        
        if success:
            return {"success": True, "result": result}
        else:
            raise HTTPException(status_code=400, detail=result)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 下载功能 API ====================

@app.post("/api/download")
async def download_table(
    table_name: str = Body(..., embed=True),
    format: str = Body("csv")
):
    """下载表数据（table_name/format 放在 POST body 中）"""
    try:
        db = DatabaseManager(config)
        result = db.query_table(table_name, page=1, page_size=1000000)  # 获取所有数据
        db.dispose()
        
        import pandas as pd
        df = pd.DataFrame(result["data"])
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{table_name}_{timestamp}.{format}"
        filepath = CACHE_DIR / filename
        
        if format == "csv":
            df.to_csv(filepath, index=False, encoding='utf-8-sig')
            media_type = "text/csv"
        else:
            df.to_excel(filepath, index=False)
            media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        
        return FileResponse(
            path=str(filepath),
            filename=filename,
            media_type=media_type
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ==================== 配置 API ====================

@app.get("/api/config")
async def get_config():
    """获取当前配置（隐藏密码）"""
    return config.to_dict()


@app.get("/api/config/full")
async def get_config_full():
    """获取完整配置（包含密码，用于编辑回显）"""
    return config.to_dict_full()


@app.post("/api/config/mysql")
async def update_mysql_config(
    host: str = Body(...),
    port: int = Body(...),
    user: str = Body(...),
    passwd: str = Body(...),
    dbname: str = Body(...)
):
    """更新数据库配置"""
    global config
    
    config.mysql.host = host
    config.mysql.port = port
    config.mysql.user = user
    config.mysql.passwd = passwd
    config.mysql.dbname = dbname
    config.save()
    
    return {"success": True, "message": "数据库配置已更新", "update": config.update}


@app.post("/api/config/sheet-filter")
async def update_sheet_filter(filters: List[str] = Body(...)):
    """更新 Sheet 过滤规则"""
    global config
    
    config.sheet_filter = filters
    config.save()
    
    return {"success": True, "message": "Sheet 过滤规则已更新", "update": config.update}


@app.post("/api/config/extract-fields")
async def update_extract_fields(fields: List[Dict[str, Any]] = Body(...)):
    """更新字段映射配置"""
    global config
    
    config.extract_fields = fields
    config.save()
    
    return {"success": True, "message": "字段映射配置已更新", "update": config.update}


# ==================== 清理 API ====================

@app.get("/api/cache/size")
async def get_cache_size():
    """获取 cache 目录占用大小"""
    try:
        total_size = 0
        file_count = 0
        dir_count = 0
        
        # 如果 cache 目录不存在，直接返回 0
        if not CACHE_DIR.exists():
            return {
                "success": True,
                "size_bytes": 0,
                "size_formatted": "0 B",
                "file_count": 0,
                "dir_count": 0
            }
        
        def get_dir_size(path: Path):
            """递归计算目录大小"""
            nonlocal total_size, file_count, dir_count
            try:
                if path.is_file():
                    total_size += path.stat().st_size
                    file_count += 1
                elif path.is_dir():
                    dir_count += 1
                    for item in path.iterdir():
                        get_dir_size(item)
            except (PermissionError, OSError):
                pass
        
        # 计算 cache 目录大小（排除 history.json）
        try:
            for item in CACHE_DIR.iterdir():
                if item.name != "history.json":
                    get_dir_size(item)
        except (PermissionError, OSError) as e:
            # 如果无法访问目录，返回 0 而不是失败
            pass
        
        # 格式化大小
        def format_size(size_bytes):
            if size_bytes == 0:
                return "0 B"
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size_bytes < 1024.0:
                    return f"{size_bytes:.2f} {unit}"
                size_bytes /= 1024.0
            return f"{size_bytes:.2f} PB"
        
        return {
            "success": True,
            "size_bytes": total_size,
            "size_formatted": format_size(total_size),
            "file_count": file_count,
            "dir_count": dir_count
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "size_formatted": "计算失败"
        }


def get_dir_size(path: Path) -> int:
    """递归计算目录大小"""
    total_size = 0
    try:
        if path.is_file():
            total_size += path.stat().st_size
        elif path.is_dir():
            for item in path.iterdir():
                total_size += get_dir_size(item)
    except (PermissionError, OSError):
        pass
    return total_size


def format_size(size_bytes: int) -> str:
    """格式化文件大小"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} PB"


@app.post("/api/history/size")
async def get_history_size(record_id: str = Body(..., embed=True)):
    """获取单个历史记录的占用大小"""
    record = history_manager.get(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    
    work_dir = Path(record.work_dir)
    if not work_dir.exists():
        return {"success": True, "size": 0, "size_formatted": "0 B"}
    
    try:
        size = get_dir_size(work_dir)
        return {
            "success": True,
            "size": size,
            "size_formatted": format_size(size)
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "size_formatted": "计算失败"
        }


# ==================== 服务管理 API ====================

def is_supervisor_running() -> bool:
    """检查是否在 supervisor 环境下运行"""
    # 检查 supervisor socket 文件是否存在
    supervisor_sock = Path("/var/run/supervisor.sock")
    if supervisor_sock.exists():
        return True
    
    # 检查环境变量
    if os.environ.get("SUPERVISOR_ENABLED") == "1":
        return True
    
    # 检查父进程是否是 supervisord
    try:
        import psutil  # pyright: ignore[reportMissingModuleSource]
        current = psutil.Process()
        parent = current.parent()
        if parent and "supervisor" in parent.name().lower():
            return True
    except:
        pass
    
    return False


def restart_via_supervisor() -> tuple:
    """通过 supervisor 重启服务"""
    try:
        result = subprocess.run(
            ["supervisorctl", "restart", "fastapi"],
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, "服务正在通过 supervisor 重启..."
        else:
            return False, f"重启失败: {result.stderr or result.stdout}"
    except subprocess.TimeoutExpired:
        return False, "重启操作超时"
    except FileNotFoundError:
        return False, "找不到 supervisorctl 命令"
    except Exception as e:
        return False, f"重启异常: {str(e)}"


def restart_via_signal() -> tuple:
    """通过信号重启服务（适用于非 supervisor 环境）"""
    try:
        # 获取当前进程 PID
        pid = os.getpid()
        
        if platform.system() == "Windows":
            # Windows: 通过结束进程的方式触发重启
            # 需要配合外部重启机制（如 Docker restart policy 或 bat 脚本）
            os._exit(0)
        else:
            # Linux/Mac: 发送 SIGHUP 信号让进程重启
            # 或者直接退出，依赖外部重启机制
            os.kill(pid, signal.SIGTERM)
        
        return True, "服务正在重启..."
    except Exception as e:
        return False, f"重启失败: {str(e)}"


@app.post("/api/service/restart")
async def restart_service():
    """
    重启服务
    - 在 supervisor 环境下使用 supervisorctl restart
    - 在非 supervisor 环境下发送信号或退出进程
    """
    # 检查是否在 supervisor 环境下
    if is_supervisor_running():
        success, message = restart_via_supervisor()
    else:
        # 非 supervisor 环境，使用延迟退出
        # 先返回响应，然后在后台线程中退出进程
        def delayed_exit():
            import time
            time.sleep(1)  # 等待响应发送完成
            if platform.system() == "Windows":
                os._exit(0)
            else:
                os.kill(os.getpid(), signal.SIGTERM)
        
        thread = Thread(target=delayed_exit, daemon=True)
        thread.start()
        
        return {
            "success": True,
            "message": "服务正在重启，请稍后刷新页面...",
            "method": "signal"
        }
    
    return {
        "success": success,
        "message": message,
        "method": "supervisor" if is_supervisor_running() else "signal"
    }


@app.get("/api/service/status")
async def get_service_status():
    """获取服务运行状态"""
    return {
        "status": "running",
        "version": "2.0.0",
        "platform": platform.system(),
        "supervisor": is_supervisor_running(),
        "pid": os.getpid(),
        "python_version": platform.python_version()
    }


# ==================== SQL 脚本编辑 API ====================

@app.get("/api/script/content")
async def get_script_content():
    """获取 SQL 脚本内容"""
    from app.config import SQL_SCRIPT
    
    try:
        if SQL_SCRIPT.exists():
            content = SQL_SCRIPT.read_text(encoding='utf-8')
            # 获取文件修改时间
            mtime = SQL_SCRIPT.stat().st_mtime
            from datetime import datetime
            modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            return {
                "success": True,
                "content": content,
                "modified": modified,
                "path": str(SQL_SCRIPT)
            }
        else:
            return {
                "success": True,
                "content": "# SQL 脚本文件不存在，请在此编写脚本\n",
                "modified": None,
                "path": str(SQL_SCRIPT)
            }
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/script/save")
async def save_script_content(content: str = Body(..., embed=True)):
    """保存 SQL 脚本内容"""
    from app.config import SQL_SCRIPT
    
    try:
        # 备份原文件
        if SQL_SCRIPT.exists():
            backup_path = SQL_SCRIPT.with_suffix('.sql.bak')
            import shutil
            shutil.copy(SQL_SCRIPT, backup_path)
        
        # 保存新内容
        SQL_SCRIPT.write_text(content, encoding='utf-8')
        
        # 获取新的修改时间
        mtime = SQL_SCRIPT.stat().st_mtime
        from datetime import datetime
        modified = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
        
        return {
            "success": True,
            "message": "脚本保存成功",
            "modified": modified
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


# ==================== 启动入口 ====================

if __name__ == "__main__":
    import uvicorn
    print(f"CapacityReport v2.0.0")
    print(f"配置更新时间: {config.update}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=9081, reload=False)
