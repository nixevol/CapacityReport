from pathlib import Path
import argparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app import state
from app.api.routers import auth, cache, config, database, health, history, license, remote, script, tasks, upload
from app.auth import verify_jwt_token
from app.config import BASE_DIR


APP_VERSION = "3.0.0"
APP_HOST = "0.0.0.0"
APP_PORT = 9081
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"


def create_app() -> FastAPI:
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
    register_frontend(app)
    return app


async def jwt_middleware(request: Request, call_next):
    if request.method == "OPTIONS":
        return await call_next(request)

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
