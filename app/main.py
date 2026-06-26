import argparse
import os
from contextlib import asynccontextmanager
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app import state
from app.api.routers import (
    auth,
    cache,
    cell_data,
    config,
    dashboard,
    database,
    health,
    history,
    license,
    remote,
    script,
    tasks,
    upload,
)
from app.auth import resolve_access_context, resolve_login_context
from app.config import BASE_DIR
from app.services.auto_scheduler import AutoScheduler


APP_VERSION = "3.0.0"
APP_HOST = "0.0.0.0"
APP_PORT = 9081
# Code/frontend live in the image (/app); runtime state lives on the data volume (BASE_DIR=/data).
FRONTEND_DIST_DIR = Path(os.environ.get("CAPAREPORT_FRONTEND_DIR") or (BASE_DIR / "frontend" / "dist"))
LOGIN_ONLY_API_PREFIXES = (
    "/api/config",
    "/api/change-password",
    "/api/license",
)


@asynccontextmanager
async def app_lifespan(app: FastAPI):
    try:
        from app.config import AppConfig
        from app.db_init import ensure_required_tables
        ensure_required_tables(AppConfig.load())
    except Exception as exc:  # noqa: BLE001
        print(f"[前置检查] 启动检查异常：{exc}")
    state.auto_scheduler = AutoScheduler()
    state.auto_scheduler.start()
    try:
        yield
    finally:
        if state.auto_scheduler is not None:
            state.auto_scheduler.stop()


def create_app() -> FastAPI:
    app = FastAPI(
        title="CapacityReport",
        description="容量报表数据处理系统",
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=app_lifespan,
    )

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

    return await call_next(request)


def register_routes(app: FastAPI) -> None:
    routers = [
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
        cell_data.router,
        dashboard.router,
        script.router,
    ]
    for router in routers:
        app.include_router(router)


def register_frontend(app: FastAPI) -> None:
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
    return path.startswith(LOGIN_ONLY_API_PREFIXES)


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
