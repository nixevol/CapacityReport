from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app import state
from app.api.routers import auth, cache, config, database, health, history, script, service, tasks, upload
from app.auth import verify_jwt_token
from app.config import BASE_DIR


APP_VERSION = "2.0.2"
FRONTEND_DIST_DIR = BASE_DIR / "frontend" / "dist"
FRONTEND_ASSETS_DIR = FRONTEND_DIST_DIR / "assets"
FRONTEND_OLD_DIR = BASE_DIR / "frontend_old"


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


def register_frontend(app: FastAPI) -> None:
    @app.get("/old", include_in_schema=False)
    async def serve_old_frontend():
        index_file = FRONTEND_OLD_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return JSONResponse(status_code=503, content={"detail": "旧版前端入口文件不存在"})

    if FRONTEND_OLD_DIR.exists():
        app.mount("/old", StaticFiles(directory=str(FRONTEND_OLD_DIR), html=True), name="frontend_old")

    if FRONTEND_ASSETS_DIR.exists():
        app.mount("/assets", StaticFiles(directory=str(FRONTEND_ASSETS_DIR)), name="assets")

    @app.get("/", include_in_schema=False)
    @app.get("/{path:path}", include_in_schema=False)
    async def serve_spa(path: str = ""):
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="接口不存在")

        if not FRONTEND_DIST_DIR.exists():
            return JSONResponse(
                status_code=503,
                content={
                    "detail": "前端构建产物不存在，请先执行 cd frontend && npm install && npm run build"
                },
            )

        requested_file = _safe_frontend_file(path)
        if requested_file and requested_file.exists() and requested_file.is_file():
            return FileResponse(str(requested_file))

        index_file = FRONTEND_DIST_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))

        return JSONResponse(status_code=503, content={"detail": "前端入口文件不存在"})


def _safe_frontend_file(path: str) -> Path | None:
    if not path:
        return None

    requested = (FRONTEND_DIST_DIR / path).resolve()
    try:
        requested.relative_to(FRONTEND_DIST_DIR.resolve())
    except ValueError:
        return None
    return requested


app = create_app()


if __name__ == "__main__":
    print(f"CapacityReport v{APP_VERSION}")
    print(f"配置更新时间: {state.config.update}")
    uvicorn.run("app.main:app", host="0.0.0.0", port=9081, reload=False)
