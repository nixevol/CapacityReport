from pathlib import Path
import socket
from typing import Literal

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app import state
from app.api.routers import auth, cache, config, database, health, history, script, service, tasks, upload
from app.auth import verify_jwt_token
from app.config import BASE_DIR


APP_VERSION = "2.0.2"
APP_HOST = "0.0.0.0"
NEW_FRONTEND_PORT = 9081
OLD_FRONTEND_PORT = 9082
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
FRONTEND_OLD_DIR = BASE_DIR / "frontend_old"
FrontendMode = Literal["new", "old", "split"]


def create_app(frontend_mode: FrontendMode = "new") -> FastAPI:
    app = FastAPI(
        title="CapacityReport",
        description="容量报表数据处理系统",
        version=APP_VERSION,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.middleware("http")(jwt_middleware)
    register_routes(app)
    register_frontend(app, frontend_mode)
    return app


async def jwt_middleware(request: Request, call_next):
    path = request.url.path
    if path.startswith("/api/") and path != "/api/login":
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return JSONResponse(status_code=401, content={"detail": "未授权，请提供有效的 Token"})

        token = auth_header.split(" ", 1)[1]
        if not verify_jwt_token(token):
            return JSONResponse(status_code=401, content={"detail": "Token 无效或已过期"})

    return await call_next(request)


def register_routes(app: FastAPI) -> None:
    routers = [
        auth.router,
        health.router,
        upload.router,
        tasks.router,
        history.router,
        database.router,
        config.router,
        cache.router,
        service.router,
        script.router,
    ]
    for router in routers:
        app.include_router(router)


def register_frontend(app: FastAPI, frontend_mode: FrontendMode) -> None:
    @app.get("/old", include_in_schema=False)
    async def serve_old_frontend(request: Request):
        if not _should_serve_old_frontend(request, frontend_mode):
            raise HTTPException(status_code=404, detail=f"旧版前端请访问 {OLD_FRONTEND_PORT} 端口")
        return _serve_old_index()

    @app.get("/old/{path:path}", include_in_schema=False)
    async def serve_old_frontend_file(request: Request, path: str):
        if not _should_serve_old_frontend(request, frontend_mode):
            raise HTTPException(status_code=404, detail=f"旧版前端请访问 {OLD_FRONTEND_PORT} 端口")
        return _serve_old_file(path)

    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_frontend(request: Request, path: str = ""):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")

        if _should_serve_old_frontend(request, frontend_mode):
            return _serve_old_frontend_path(path)

        return _serve_new_frontend_path(path)


def _should_serve_old_frontend(request: Request, frontend_mode: FrontendMode) -> bool:
    if frontend_mode == "old":
        return True
    if frontend_mode == "new":
        return False
    return _request_port(request) == OLD_FRONTEND_PORT


def _request_port(request: Request) -> int | None:
    server = request.scope.get("server")
    if isinstance(server, tuple) and len(server) >= 2:
        return server[1]
    return request.url.port


def _serve_new_frontend_path(path: str):
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


def _serve_old_frontend_path(path: str):
    if not path:
        return _serve_old_index()

    requested_file = _safe_file(FRONTEND_OLD_DIR, path)
    if requested_file and requested_file.exists() and requested_file.is_file():
        return FileResponse(str(requested_file))

    return _serve_old_index()


def _serve_old_file(path: str):
    requested_file = _safe_file(FRONTEND_OLD_DIR, path)
    if requested_file and requested_file.exists() and requested_file.is_file():
        return FileResponse(str(requested_file))
    raise HTTPException(status_code=404, detail="旧版前端文件不存在")


def _serve_old_index():
    if not FRONTEND_OLD_DIR.exists():
        return JSONResponse(status_code=503, content={"detail": "旧版前端目录不存在"})

    index_file = FRONTEND_OLD_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    return JSONResponse(status_code=503, content={"detail": "旧版前端入口文件不存在"})


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


def _create_listen_socket(port: int) -> socket.socket:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((APP_HOST, port))
    sock.listen(2048)
    sock.set_inheritable(True)
    return sock


def run_split_frontend_servers() -> None:
    sockets = [_create_listen_socket(NEW_FRONTEND_PORT), _create_listen_socket(OLD_FRONTEND_PORT)]
    config = uvicorn.Config(split_app, host=APP_HOST, port=NEW_FRONTEND_PORT, reload=False)
    server = uvicorn.Server(config)
    server.run(sockets=sockets)


app = create_app("new")
old_app = create_app("old")
split_app = create_app("split")


if __name__ == "__main__":
    print(f"CapacityReport v{APP_VERSION}")
    print(f"配置更新时间: {state.config.update}")
    print(f"新版前端: http://localhost:{NEW_FRONTEND_PORT}")
    print(f"旧版前端: http://localhost:{OLD_FRONTEND_PORT}")
    run_split_frontend_servers()
