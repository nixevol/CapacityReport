import base64
import configparser
import hashlib
import hmac
import json
import time
from typing import Optional

from app.config import BASE_DIR


SECRET_KEY = "CapaReportSecretKey2026"
AUTH_INI_PATH = BASE_DIR / "auth.ini"
DEFAULT_USERNAME = "root"
DEFAULT_PASSWORD = "Capacity"


def _ensure_auth_ini() -> None:
    if AUTH_INI_PATH.exists():
        return

    cfg = configparser.ConfigParser()
    cfg["auth"] = {"username": DEFAULT_USERNAME, "password": DEFAULT_PASSWORD}
    with AUTH_INI_PATH.open("w", encoding="utf-8") as file:
        cfg.write(file)


def get_auth_config() -> dict[str, str]:
    _ensure_auth_ini()
    cfg = configparser.ConfigParser()
    cfg.read(AUTH_INI_PATH, encoding="utf-8")
    return {
        "username": cfg.get("auth", "username", fallback=DEFAULT_USERNAME),
        "password": cfg.get("auth", "password", fallback=DEFAULT_PASSWORD),
    }


def save_auth_password(new_password: str) -> None:
    _ensure_auth_ini()
    cfg = configparser.ConfigParser()
    cfg.read(AUTH_INI_PATH, encoding="utf-8")
    cfg.set("auth", "password", new_password)
    with AUTH_INI_PATH.open("w", encoding="utf-8") as file:
        cfg.write(file)


def create_jwt_token(data: dict, expires_in: int = 86400 * 30) -> str:
    header = _encode_json({"alg": "HS256", "typ": "JWT"})
    payload_data = data.copy()
    payload_data["exp"] = int(time.time()) + expires_in
    payload = _encode_json(payload_data)
    signature = _sign(header, payload)
    return f"{header}.{payload}.{signature}"


def verify_jwt_token(token: str) -> Optional[dict]:
    try:
        header, payload, signature = token.split(".")
        if not hmac.compare_digest(signature, _sign(header, payload)):
            return None

        payload_padded = payload + "=" * ((4 - len(payload) % 4) % 4)
        data = json.loads(base64.urlsafe_b64decode(payload_padded).decode())
        if data.get("exp", 0) < int(time.time()):
            return None
        return data
    except Exception:
        return None


def _encode_json(data: dict) -> str:
    raw = json.dumps(data, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _sign(header: str, payload: str) -> str:
    raw = hmac.new(
        SECRET_KEY.encode(),
        f"{header}.{payload}".encode(),
        hashlib.sha256,
    ).digest()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")
