from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from app.auth import resolve_login_context
from app.services.api_tokens import create_token, delete_token, list_tokens, regenerate_token, update_token


router = APIRouter(tags=["api-tokens"])


def _require_login(request: Request) -> None:
    if resolve_login_context(request) is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")


def _bad_expiration_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail="到期日期格式无效，请使用 YYYY-MM-DD 或 ISO 日期时间")


@router.get("/api/tokens")
async def get_tokens(request: Request):
    _require_login(request)
    return {"success": True, "tokens": list_tokens()}


@router.post("/api/tokens/create")
async def create_api_token(request: Request, payload: dict[str, Any] = Body(...)):
    _require_login(request)
    name = str(payload.get("name", "")).strip()
    expires_at = payload.get("expires_at")
    enabled = bool(payload.get("enabled", True))
    permanent = bool(payload.get("permanent", False))
    expires_in_days = payload.get("expires_in_days")
    raw_expires_at = None if permanent else (str(expires_at).strip() if expires_at else None)

    try:
        raw_token, record = create_token(
            name=name,
            expires_at=raw_expires_at,
            enabled=enabled,
            expires_in_days=int(expires_in_days) if expires_in_days is not None else None,
        )
    except ValueError as exc:
        raise _bad_expiration_error(exc) from exc
    return {
        "success": True,
        "message": "API Token 创建成功",
        "token": raw_token,
        "record": record,
    }


@router.post("/api/tokens/update")
async def update_api_token(request: Request, payload: dict[str, Any] = Body(...)):
    _require_login(request)
    token_id = str(payload.get("id", "")).strip()
    if not token_id:
        raise HTTPException(status_code=400, detail="缺少 Token ID")

    try:
        record = update_token(
            token_id,
            name=payload.get("name"),
            enabled=payload.get("enabled"),
            expires_at=None if payload.get("permanent") else payload.get("expires_at"),
        )
        return {"success": True, "message": "API Token 已更新", "record": record}
    except ValueError as exc:
        raise _bad_expiration_error(exc) from exc
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/tokens/regenerate")
async def regenerate_api_token(request: Request, payload: dict[str, Any] = Body(...)):
    _require_login(request)
    token_id = str(payload.get("id", "")).strip()
    if not token_id:
        raise HTTPException(status_code=400, detail="缺少 Token ID")

    try:
        raw_token, record = regenerate_token(token_id)
        return {
            "success": True,
            "message": "API Token 已重新生成",
            "token": raw_token,
            "record": record,
        }
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/api/tokens/delete")
async def delete_api_token(request: Request, payload: dict[str, Any] = Body(...)):
    _require_login(request)
    token_id = str(payload.get("id", "")).strip()
    if not token_id:
        raise HTTPException(status_code=400, detail="缺少 Token ID")

    delete_token(token_id)
    return {"success": True, "message": "API Token 已删除"}


@router.get("/api/docs-info")
async def docs_info(request: Request):
    _require_login(request)
    return {
        "success": True,
        "docs_url": "/api/docs-ui",
        "openapi_url": "/api/openapi.json",
        "token_header": "Authorization: Bearer <token>",
        "alt_header": "X-API-Token: <token>",
        "note": "API 文档仅登录后可访问。",
    }
