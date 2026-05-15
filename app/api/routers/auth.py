from fastapi import APIRouter, Body
from fastapi.responses import JSONResponse

from app.auth import create_jwt_token, get_auth_config, save_auth_password


router = APIRouter(tags=["auth"])


@router.post("/api/login")
async def login(
    username: str = Body(..., embed=True),
    password: str = Body(..., embed=True),
):
    auth = get_auth_config()
    if username != auth["username"] or password != auth["password"]:
        return JSONResponse(status_code=401, content={"detail": "账号或密码错误"})

    token = create_jwt_token({"user": username})
    return {"success": True, "token": token}


@router.post("/api/change-password")
async def change_password(
    current_password: str = Body(..., embed=True),
    new_password: str = Body(..., embed=True),
):
    auth = get_auth_config()
    if current_password != auth["password"]:
        return JSONResponse(status_code=400, content={"detail": "当前密码错误"})
    if len(new_password) < 4:
        return JSONResponse(status_code=400, content={"detail": "新密码长度不能少于 4 位"})

    save_auth_password(new_password)
    return {"success": True, "message": "密码修改成功"}

