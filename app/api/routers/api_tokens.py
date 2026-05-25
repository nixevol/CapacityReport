from typing import Any

from fastapi import APIRouter, Body, HTTPException, Request

from app.auth import resolve_login_context
from app.services.api_tokens import create_token, delete_token, delete_tokens, list_tokens, regenerate_token, update_token


router = APIRouter(tags=["api-tokens"])


def _require_login(request: Request) -> None:
    if resolve_login_context(request) is None:
        raise HTTPException(status_code=401, detail="未登录或登录已过期")


def _bad_expiration_error(exc: ValueError) -> HTTPException:
    return HTTPException(status_code=400, detail="到期日期格式无效，请使用 YYYY-MM-DD 或 ISO 日期时间")


def _resolve_expires_at(payload: dict[str, Any]) -> str | None:
    if bool(payload.get("permanent", False)):
        return None

    expires_at = str(payload.get("expires_at") or "").strip()
    if not expires_at:
        raise HTTPException(status_code=400, detail="请选择 Token 到期日期，或设置为永久有效")
    return expires_at


@router.get("/api/tokens")
async def get_tokens(request: Request):
    _require_login(request)
    return {"success": True, "tokens": list_tokens()}


@router.post("/api/tokens/create")
async def create_api_token(request: Request, payload: dict[str, Any] = Body(...)):
    _require_login(request)
    name = str(payload.get("name", "")).strip()
    enabled = bool(payload.get("enabled", True))
    raw_expires_at = _resolve_expires_at(payload)

    try:
        raw_token, record = create_token(
            name=name,
            expires_at=raw_expires_at,
            enabled=enabled,
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

    changes: dict[str, Any] = {}
    if "name" in payload:
        changes["name"] = payload.get("name")
    if "enabled" in payload:
        changes["enabled"] = payload.get("enabled")
    if "permanent" in payload or "expires_at" in payload:
        changes["expires_at"] = _resolve_expires_at(payload)

    try:
        record = update_token(token_id, **changes)
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


@router.post("/api/tokens/batch-delete")
async def batch_delete_api_tokens(request: Request, payload: dict[str, Any] = Body(...)):
    _require_login(request)
    token_ids = payload.get("ids", [])
    if not isinstance(token_ids, list) or not token_ids:
        raise HTTPException(status_code=400, detail="请选择要删除的 Token")

    deleted_count = delete_tokens([str(token_id) for token_id in token_ids])
    return {"success": True, "message": f"已删除 {deleted_count} 个 API Token", "deleted_count": deleted_count}


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
