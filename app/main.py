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
        return RedirectResponse(url="/api-center", status_code=302)

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

    schema = get_openapi(title=app.title, version=app.version, description=app.description, routes=app.routes)
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
        if not path.startswith("/api/") or path in {"/api/login"}:
            continue
        security = [{"BearerAuth": []}] if _is_login_only_api(path) else [{"BearerAuth": []}, {"ApiTokenHeader": []}]
        for operation in methods.values():
            if isinstance(operation, dict):
                operation["security"] = security

    app.openapi_schema = schema
    return schema


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
