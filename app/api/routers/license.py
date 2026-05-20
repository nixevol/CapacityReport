from fastapi import APIRouter, Body, HTTPException

from app.services.license import InvalidActivationCodeError, activate, get_license_info


router = APIRouter(tags=["license"])


@router.get("/api/license/status")
async def get_license_status():
    info = get_license_info()
    return {"success": True, **info.to_dict()}


@router.post("/api/license/activate")
async def activate_license(code: str = Body(..., embed=True)):
    try:
        info = activate(code)
    except InvalidActivationCodeError as exc:
        raise HTTPException(status_code=400, detail=exc.to_detail()) from exc

    return {
        "success": True,
        "message": "激活成功，到期日期已延长 30 天",
        **info.to_dict(),
    }
