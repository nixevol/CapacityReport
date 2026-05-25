import argparse
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse

from app import state
from app.api.routers import (
    api_tokens,
    auth,
    cache,
    config,
    database,
    health,
    history,
    license,
    remote,
    script,
    tasks,
    upload,
)
from app.auth import extract_access_token, resolve_access_context, resolve_login_context
from app.config import BASE_DIR
from app.services.api_tokens import touch_token_usage


APP_VERSION = "3.0.0"
APP_HOST = "0.0.0.0"
APP_PORT = 9081
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
LOGIN_ONLY_API_PREFIXES = (
    "/api/config",
    "/api/change-password",
    "/api/license",
    "/api/tokens",
)
LOGIN_ONLY_API_PATHS = {"/api/openapi.json", "/api/docs-ui", "/api/docs-info"}
TAG_LABELS = {
    "auth": "认证",
    "upload": "数据处理",
    "remote": "远程数据",
    "tasks": "任务状态",
    "history": "处理历史",
    "database": "数据库",
    "script": "脚本",
    "config": "系统配置",
    "cache": "缓存",
    "license": "授权",
    "api-tokens": "API Token",
    "health": "健康检查",
}
OPENAPI_TAGS = [
    {"name": "认证", "description": "登录、修改密码等登录态接口。"},
    {"name": "数据处理", "description": "上传源数据并启动容量报表处理流程。"},
    {"name": "远程数据", "description": "测试 FTP/SFTP 连接，并从远程目录下载后自动处理。"},
    {"name": "任务状态", "description": "查看当前任务、处理进度和日志。"},
    {"name": "处理历史", "description": "查询、下载和清理历史处理记录及原始数据。"},
    {"name": "数据库", "description": "列出表、查询表、导出表和执行 SQL。API Token 可调用这些业务接口。"},
    {"name": "脚本", "description": "查看、保存和手动执行报表 SQL 脚本。"},
    {"name": "系统配置", "description": "数据库、远程数据源、过滤规则、字段映射等配置。仅登录态可调用。"},
    {"name": "缓存", "description": "查看服务端缓存占用。"},
    {"name": "授权", "description": "查看和延长程序授权有效期。仅登录态可调用。"},
    {"name": "API Token", "description": "生成、复制、启停、编辑、重生成和批量删除 API Token。仅登录态可调用。"},
    {"name": "健康检查", "description": "服务健康状态检查。"},
]
OPENAPI_OPERATION_DOCS = {
    ("post", "/api/login"): {
        "summary": "登录系统",
        "description": "使用系统账号密码登录，成功后返回登录 JWT。",
        "example": {"username": "root", "password": "capacity"},
    },
    ("post", "/api/change-password"): {
        "summary": "修改登录密码",
        "description": "修改当前登录用户密码，需要登录 JWT，不支持 API Token 调用。",
        "example": {"current_password": "capacity", "new_password": "new-password"},
    },
    ("get", "/health"): {"summary": "健康检查", "description": "返回服务进程是否可用。"},
    ("post", "/api/upload/create"): {
        "summary": "创建上传会话",
        "description": "创建一个待上传的数据处理会话，返回 session_id。通常用于分批上传文件。",
    },
    ("post", "/api/upload"): {
        "summary": "上传源数据文件",
        "description": "上传 ZIP、CSV 或 Excel 数据文件。可传 session_id 追加到已有上传会话；不传则自动创建并锁定任务。",
        "request_description": "multipart/form-data，files 为一个或多个文件，session_id 可选。",
    },
    ("post", "/api/upload/complete/{session_id}"): {
        "summary": "完成上传会话",
        "description": "标记上传会话文件数量，用于前端展示。",
        "parameters": {"session_id": "上传会话 ID。"},
    },
    ("post", "/api/process/start"): {
        "summary": "开始处理已上传数据",
        "description": "对指定上传会话目录执行解压、入库和报表 SQL 脚本。",
        "example": {"task_id": "20260519_172457"},
    },
    ("post", "/api/process/status"): {
        "summary": "查询处理任务状态",
        "description": "返回任务阶段、状态、日志和错误详情。",
        "example": {"task_id": "20260519_172457"},
    },
    ("get", "/api/process/active"): {
        "summary": "查询当前活跃任务",
        "description": "返回当前是否有上传、远程下载、处理或脚本任务正在执行。",
    },
    ("get", "/api/task/status"): {
        "summary": "查询全局任务锁",
        "description": "返回全局任务锁状态、任务 ID、阶段和最近日志。",
    },
    ("post", "/api/task/lock"): {
        "summary": "锁定任务",
        "description": "内部接口：手动占用全局任务锁。",
        "example": {"task_id": "manual-task"},
    },
    ("post", "/api/task/unlock"): {
        "summary": "释放任务锁",
        "description": "内部接口：释放全局任务锁。传 task_id 时只释放匹配的任务。",
        "example": {"task_id": "manual-task"},
    },
    ("post", "/api/remote/test"): {
        "summary": "测试远程数据源",
        "description": "测试 FTP/SFTP 连接。请求体为空时使用系统设置中的远程数据源配置。",
        "example": {
            "protocol": "sftp",
            "host": "127.0.0.1",
            "port": 22,
            "user": "user",
            "passwd": "your-password",
            "remote_dir": "/CapacityReportData",
            "passive": True,
            "timeout": 30,
            "auto_delete_source": False,
        },
    },
    ("post", "/api/remote/start"): {
        "summary": "远程下载并处理",
        "description": "从已配置的 FTP/SFTP 目录递归下载源数据，然后自动执行完整处理流程。",
    },
    ("post", "/api/history"): {
        "summary": "查询处理历史",
        "description": "按最近时间返回处理历史记录。",
        "example": {"limit": 50},
    },
    ("post", "/api/history/detail"): {
        "summary": "查询历史详情",
        "description": "返回指定历史记录的基础信息和完整日志。",
        "example": {"record_id": "20260519_172457"},
    },
    ("post", "/api/history/download"): {
        "summary": "下载历史原始数据",
        "description": "将历史记录对应工作目录压缩为 ZIP 后下载，下载响应完成后自动清理临时压缩包。",
        "example": {"record_id": "20260519_172457"},
    },
    ("post", "/api/history/size"): {
        "summary": "查询历史目录大小",
        "description": "统计指定历史记录工作目录的文件数和占用空间。",
        "example": {"record_id": "20260519_172457"},
    },
    ("post", "/api/history/delete"): {
        "summary": "删除历史记录",
        "description": "删除指定处理历史及其本地缓存数据。",
        "example": {"record_id": "20260519_172457"},
    },
    ("post", "/api/history/clear"): {"summary": "清空处理历史", "description": "删除全部处理历史及其缓存数据。"},
    ("get", "/api/database/info"): {
        "summary": "查询数据库信息",
        "description": "返回 MySQL 版本、LOAD DATA INFILE 可用性等诊断信息。",
    },
    ("post", "/api/database/test"): {"summary": "测试数据库连接", "description": "测试当前数据库配置是否可连接。"},
    ("get", "/api/database/tables"): {"summary": "列出所有数据表", "description": "返回当前数据库中的全部表名。"},
    ("post", "/api/database/tables"): {"summary": "列出所有数据表", "description": "返回当前数据库中的全部表名。"},
    ("post", "/api/database/table/info"): {
        "summary": "查询数据表结构",
        "description": "返回指定表的字段结构和行数。",
        "example": {"table_name": "4G_结果表"},
    },
    ("post", "/api/database/table/data"): {
        "summary": "分页查询数据表",
        "description": "按页读取指定表数据，可指定排序字段和排序方向。",
        "example": {
            "table_name": "4G_结果表",
            "page": 1,
            "page_size": 50,
            "order_by": "日均流量（GB）",
            "order_dir": "DESC",
        },
    },
    ("post", "/api/database/table/query"): {
        "summary": "按条件查询数据表",
        "description": "支持分页、排序和字段模糊查询。filters 的 key 为字段名，value 为模糊匹配值。",
        "example": {
            "table_name": "4G_结果表",
            "page": 1,
            "page_size": 50,
            "filters": {"小区名称": "广州"},
            "order_by": "日均流量（GB）",
            "order_dir": "DESC",
        },
    },
    ("post", "/api/database/table/truncate"): {
        "summary": "清空数据表",
        "description": "保留表结构，删除指定表的全部数据。",
        "example": {"table_name": "4G_UD"},
    },
    ("post", "/api/database/table/drop"): {
        "summary": "删除数据表",
        "description": "删除指定数据表。",
        "example": {"table_name": "4G_UD"},
    },
    ("post", "/api/database/table/drop-all"): {"summary": "删除全部数据表", "description": "删除当前数据库中的全部表。"},
    ("post", "/api/database/execute"): {
        "summary": "执行自定义 SQL",
        "description": "执行任意 SQL，包括 SELECT、UPDATE、INSERT、DROP 等。请仅在可信内网环境使用。",
        "example": {"sql": "SELECT * FROM `4G_结果表` LIMIT 10"},
    },
    ("post", "/api/download"): {
        "summary": "导出数据表",
        "description": "导出 CSV 或 XLSX。CSV 每次只能导出一张表，XLSX 可选择多张表并按表名分 sheet。",
        "example": {"format": "xlsx", "table_names": ["4G_结果表", "5G_结果表"]},
    },
    ("get", "/api/script/content"): {"summary": "读取 SQL 脚本", "description": "读取当前 ReportScript.sql 内容和修改时间。"},
    ("post", "/api/script/save"): {
        "summary": "保存 SQL 脚本",
        "description": "覆盖保存 ReportScript.sql 内容。",
        "example": {"content": "SELECT 1;"},
    },
    ("post", "/api/script/execute"): {"summary": "手动执行 SQL 脚本", "description": "直接执行当前 ReportScript.sql，并返回脚本任务 ID。"},
    ("get", "/api/config"): {"summary": "读取基础配置", "description": "读取当前系统基础配置。仅登录态可访问。"},
    ("get", "/api/config/full"): {"summary": "读取完整配置", "description": "读取数据库、远程数据源、历史保留、过滤规则和字段映射配置。"},
    ("post", "/api/config/mysql"): {
        "summary": "保存数据库配置",
        "description": "更新 MySQL 连接配置。",
        "example": {"host": "capacity-mysql", "port": 3306, "user": "root", "passwd": "your-password", "dbname": "CapacityReport"},
    },
    ("post", "/api/config/remote"): {
        "summary": "保存远程数据源配置",
        "description": "更新 FTP/SFTP 自动下载配置。",
        "example": {
            "enabled": True,
            "protocol": "sftp",
            "host": "127.0.0.1",
            "port": 22,
            "user": "user",
            "passwd": "your-password",
            "remote_dir": "/CapacityReportData",
            "passive": True,
            "timeout": 30,
            "auto_delete_source": False,
        },
    },
    ("post", "/api/config/history-retention"): {
        "summary": "保存历史保留配置",
        "description": "设置处理历史是否自动清理，以及保留最近多少次记录。",
        "example": {"enabled": True, "keep_count": 20},
    },
    ("post", "/api/config/sheet-filter"): {
        "summary": "保存 Sheet 过滤规则",
        "description": "设置需要跳过处理的 Sheet 关键字列表。",
        "example": ["指标(计数器)", "Template"],
    },
    ("post", "/api/config/extract-fields"): {
        "summary": "保存字段映射配置",
        "description": "设置 Excel/CSV 源字段到数据库字段的映射规则。",
        "example": [{"Field": "日期时间", "Extract": ["开始时间"], "Type": "datetime"}],
    },
    ("get", "/api/config/download"): {
        "summary": "下载配置文件",
        "description": "下载当前 Configure.json，并附带 ApiTokens，用于迁移或恢复 API Token 配置。",
    },
    ("post", "/api/config/upload"): {
        "summary": "上传配置文件",
        "description": "上传并应用 Configure.json。文件中包含 ApiTokens 时会同步恢复 API Token。仅登录态可访问。",
        "request_description": "multipart/form-data，file 为 Configure.json 文件。",
    },
    ("get", "/api/cache/size"): {"summary": "查询缓存大小", "description": "统计当前 cache 目录的大小、文件数和目录数。"},
    ("get", "/api/license/status"): {"summary": "查询授权状态", "description": "返回当前授权到期日期和激活 key 标签。"},
    ("post", "/api/license/activate"): {
        "summary": "激活授权延期",
        "description": "提交激活码，将授权到期日期延长 30 天。",
        "example": {"code": "sha256-value"},
    },
    ("get", "/api/tokens"): {"summary": "列出 API Token", "description": "返回已创建 Token 列表，包含可复制的完整 Token。仅登录态可访问。"},
    ("post", "/api/tokens/create"): {
        "summary": "生成 API Token",
        "description": "创建新的 API Token。完整 Token 会保存到本地，后续可在列表中重复复制。",
        "example": {"name": "外部系统接入", "permanent": True, "expires_at": None, "enabled": True},
    },
    ("post", "/api/tokens/update"): {
        "summary": "编辑 API Token",
        "description": "修改 Token 名称、启停状态和有效期。",
        "example": {"id": "token-id", "name": "外部系统接入", "permanent": False, "expires_at": "2026-12-31", "enabled": True},
    },
    ("post", "/api/tokens/regenerate"): {
        "summary": "重生成 API Token",
        "description": "重生成完整 Token，旧 Token 立即失效。",
        "example": {"id": "token-id"},
    },
    ("post", "/api/tokens/delete"): {
        "summary": "删除 API Token",
        "description": "删除指定 Token。",
        "example": {"id": "token-id"},
    },
    ("post", "/api/tokens/batch-delete"): {
        "summary": "批量删除 API Token",
        "description": "按 ID 批量删除 Token。",
        "example": {"ids": ["token-id-1", "token-id-2"]},
    },
    ("get", "/api/docs-info"): {"summary": "查询 API 文档入口", "description": "返回 API 文档和 OpenAPI JSON 地址。仅登录态可访问。"},
}


def create_app() -> FastAPI:
    app = FastAPI(
        title="CapacityReport",
        description="容量报表数据处理系统",
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )
    app.openapi = lambda: custom_openapi(app)  # type: ignore[method-assign]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(auth_middleware)
    register_routes(app)
    register_frontend(app)
    return app


async def auth_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

    path = request.url.path
    if path == "/api/login":
        return await call_next(request)

    if _is_login_only_api(path):
        if resolve_login_context(request) is None:
            return JSONResponse(status_code=401, content={"detail": "未登录或登录已过期"})
        return await call_next(request)

    if path.startswith("/api/"):
        access_context = resolve_access_context(request)
        if access_context is None:
            return JSONResponse(status_code=401, content={"detail": "未授权，请提供有效的 Token"})

        request.state.auth_context = access_context
        if access_context.kind == "api_token":
            access_token = extract_access_token(request)
            if access_token:
                client_host = request.client.host if request.client else None
                touch_token_usage(access_token, client_host)

    return await call_next(request)


def register_routes(app: FastAPI) -> None:
    routers = [
        api_tokens.router,
        auth.router,
        health.router,
        upload.router,
        remote.router,
        tasks.router,
        history.router,
        license.router,
        database.router,
        config.router,
        cache.router,
        script.router,
    ]
    for router in routers:
        app.include_router(router)


def register_frontend(app: FastAPI) -> None:
    @app.get("/api/openapi.json", include_in_schema=False)
    async def serve_openapi(request: Request):
        if resolve_login_context(request) is None:
            return JSONResponse(status_code=401, content={"detail": "未登录或登录已过期"})
        return JSONResponse(app.openapi())

    @app.get("/api/docs-ui", include_in_schema=False)
    async def serve_docs_ui(request: Request):
        if resolve_login_context(request) is None:
            return JSONResponse(status_code=401, content={"detail": "未登录或登录已过期"})
        return RedirectResponse(url="/api-docs", status_code=302)

    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(path: str = ""):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")
        return _serve_frontend_path(path)


def _serve_frontend_path(path: str):
    if not FRONTEND_DIST_DIR.exists():
        return JSONResponse(
            status_code=503,
            content={"detail": "前端构建产物不存在，请先执行 cd frontend && npm install && npm run build"},
        )

    requested_file = _safe_file(FRONTEND_DIST_DIR, path)
    if requested_file and requested_file.exists() and requested_file.is_file():
        return FileResponse(str(requested_file))

    index_file = FRONTEND_DIST_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    return JSONResponse(status_code=503, content={"detail": "前端入口文件不存在"})


def _safe_file(root: Path, path: str) -> Path | None:
    if not path:
        return None

    root = root.resolve()
    requested = (root / path).resolve()
    try:
        requested.relative_to(root)
    except ValueError:
        return None
    return requested


def _is_login_only_api(path: str) -> bool:
    return path in LOGIN_ONLY_API_PATHS or path.startswith(LOGIN_ONLY_API_PREFIXES)


def custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    schema = get_openapi(
        title="CapacityReport API",
        version=app.version,
        description=(
            "容量报表数据处理系统接口文档。业务接口支持登录 JWT 或 API Token；"
            "系统配置、授权、Token 管理和文档本身仅支持登录态访问。"
        ),
        routes=app.routes,
    )
    schema["tags"] = OPENAPI_TAGS
    components = schema.setdefault("components", {})
    security_schemes = components.setdefault("securitySchemes", {})
    security_schemes["BearerAuth"] = {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "登录 JWT 或 API Token，均可通过 Authorization: Bearer <token> 传递；API Token 也支持 X-API-Token: <token>。",
    }
    security_schemes["ApiTokenHeader"] = {
        "type": "apiKey",
        "in": "header",
        "name": "X-API-Token",
        "description": "API Token 也可以通过 X-API-Token 请求头传递。",
    }

    for path, methods in schema.get("paths", {}).items():
        for method, operation in methods.items():
            if not isinstance(operation, dict):
                continue

            operation["tags"] = [TAG_LABELS.get(tag, tag) for tag in operation.get("tags", [])]
            operation["operationId"] = _make_operation_id(method, path)

            if path.startswith("/api/") and path not in {"/api/login"}:
                operation["security"] = (
                    [{"BearerAuth": []}]
                    if _is_login_only_api(path)
                    else [{"BearerAuth": []}, {"ApiTokenHeader": []}]
                )

            _apply_operation_doc(operation, OPENAPI_OPERATION_DOCS.get((method.lower(), path), {}))

    app.openapi_schema = schema
    return schema


def _make_operation_id(method: str, path: str) -> str:
    normalized_path = (
        path.strip("/")
        .replace("/", "_")
        .replace("-", "_")
        .replace("{", "")
        .replace("}", "")
    )
    return f"{method.lower()}_{normalized_path or 'root'}"


def _apply_operation_doc(operation: dict, doc: dict) -> None:
    if not doc:
        return

    for key in ("summary", "description"):
        value = doc.get(key)
        if value:
            operation[key] = value

    request_description = doc.get("request_description")
    if request_description and isinstance(operation.get("requestBody"), dict):
        operation["requestBody"]["description"] = request_description

    if "example" in doc:
        _set_request_example(operation, doc["example"])

    parameter_descriptions = doc.get("parameters")
    if isinstance(parameter_descriptions, dict):
        _set_parameter_descriptions(operation, parameter_descriptions)


def _set_request_example(operation: dict, example: object) -> None:
    request_body = operation.get("requestBody")
    if not isinstance(request_body, dict):
        return

    content = request_body.get("content")
    if not isinstance(content, dict):
        return

    media = content.get("application/json")
    if not isinstance(media, dict):
        media = next((value for value in content.values() if isinstance(value, dict)), None)
    if isinstance(media, dict):
        media["example"] = example


def _set_parameter_descriptions(operation: dict, descriptions: dict[str, str]) -> None:
    parameters = operation.get("parameters")
    if not isinstance(parameters, list):
        return

    for parameter in parameters:
        if not isinstance(parameter, dict):
            continue
        name = parameter.get("name")
        if isinstance(name, str) and name in descriptions:
            parameter["description"] = descriptions[name]


app = create_app()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="CapacityReport server")
    parser.add_argument("--host", default=APP_HOST, help="Host to bind")
    parser.add_argument("--port", default=APP_PORT, type=int, help="Port to bind")
    return parser.parse_args()


def run_server(host: str = APP_HOST, port: int = APP_PORT) -> None:
    print(f"CapacityReport v{APP_VERSION}")
    print(f"Config update: {state.current_config().update}")
    print(f"Frontend: http://localhost:{port}")
    uvicorn.run(app, host=host, port=port, reload=False)


if __name__ == "__main__":
    args = parse_args()
    run_server(args.host, args.port)
