"""本地授权期限校验。"""
import base64
import hashlib
import hmac
import json
import re
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any

from app.config import BASE_DIR


DEFAULT_EXPIRES_ON = date(2026, 6, 20)
EXTEND_DAYS = 30
LICENSE_FILE = BASE_DIR / "license.dat"
_SECRET = b"CapacityReport local license v1"
_ZIP_DATE_RE = re.compile(r"(?<!\d)(20\d{10}(?:\d{2})?)(?!\d)")


class LicenseError(Exception):
    """授权校验错误。"""

    code = "LICENSE_ERROR"

    def to_detail(self) -> dict[str, Any]:
        return {"code": self.code, "message": str(self)}


class LicenseExpiredError(LicenseError):
    """数据日期超过授权到期日期。"""

    code = "LICENSE_EXPIRED"

    def __init__(self, expires_on: date, current_date: date):
        self.expires_on = expires_on
        self.current_date = current_date
        super().__init__(
            f"授权已过期：数据日期 {current_date.isoformat()} 已超过到期日期 {expires_on.isoformat()}"
        )

    def to_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "expires_on": self.expires_on.isoformat(),
            "current_date": self.current_date.isoformat(),
            "key_label": format_key_label(self.expires_on),
        }


class InvalidActivationCodeError(LicenseError):
    """激活码错误。"""

    code = "LICENSE_INVALID"

    def __init__(self, expires_on: date):
        self.expires_on = expires_on
        super().__init__("激活码无效，请按当前 key 重新计算后输入")

    def to_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": str(self),
            "expires_on": self.expires_on.isoformat(),
            "key_label": format_key_label(self.expires_on),
        }


@dataclass(frozen=True)
class LicenseInfo:
    expires_on: date
    current_date: date | None = None
    zip_count: int = 0

    @property
    def key_label(self) -> str:
        return format_key_label(self.expires_on)

    def to_dict(self) -> dict[str, Any]:
        return {
            "expires_on": self.expires_on.isoformat(),
            "key_label": self.key_label,
            "current_date": self.current_date.isoformat() if self.current_date else None,
            "zip_count": self.zip_count,
        }


def get_license_info() -> LicenseInfo:
    return LicenseInfo(expires_on=read_expires_on())


def activate(code: str) -> LicenseInfo:
    expires_on = read_expires_on()
    expected = activation_hash(expires_on)
    normalized_code = (code or "").strip().lower()
    if not hmac.compare_digest(normalized_code, expected):
        raise InvalidActivationCodeError(expires_on)

    new_expires_on = expires_on + timedelta(days=EXTEND_DAYS)
    write_expires_on(new_expires_on)
    return LicenseInfo(expires_on=new_expires_on)


def check_processing_allowed(work_dir: Path) -> LicenseInfo:
    expires_on = read_expires_on()
    zip_count, current_date = extract_max_zip_date(work_dir)
    info = LicenseInfo(expires_on=expires_on, current_date=current_date, zip_count=zip_count)

    if current_date and current_date > expires_on:
        raise LicenseExpiredError(expires_on, current_date)

    return info


def extract_max_zip_date(work_dir: Path) -> tuple[int, date | None]:
    max_date: date | None = None
    zip_count = 0
    for zip_file in work_dir.rglob("*.zip"):
        zip_count += 1
        for raw_value in _ZIP_DATE_RE.findall(zip_file.name):
            parsed_date = _parse_zip_timestamp(raw_value)
            if parsed_date and (max_date is None or parsed_date > max_date):
                max_date = parsed_date

    return zip_count, max_date


def activation_hash(expires_on: date) -> str:
    return hashlib.sha256(format_key_label(expires_on).encode("utf-8")).hexdigest()


def format_key_label(value: date) -> str:
    return value.strftime("%Y/%m/%d")


def read_expires_on() -> date:
    if not LICENSE_FILE.exists():
        write_expires_on(DEFAULT_EXPIRES_ON)
        return DEFAULT_EXPIRES_ON

    try:
        encrypted = base64.urlsafe_b64decode(LICENSE_FILE.read_text(encoding="utf-8").encode("ascii"))
        raw = _xor_bytes(encrypted)
        data = json.loads(raw.decode("utf-8"))
        payload = data["payload"]
        signature = data["signature"]
        payload_raw = _dump_json(payload)
        expected_signature = hmac.new(_SECRET, payload_raw, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected_signature):
            raise ValueError("signature mismatch")

        return date.fromisoformat(str(payload["expires_on"]))
    except Exception:
        write_expires_on(DEFAULT_EXPIRES_ON)
        return DEFAULT_EXPIRES_ON


def write_expires_on(expires_on: date) -> None:
    payload = {"expires_on": expires_on.isoformat()}
    payload_raw = _dump_json(payload)
    data = {
        "payload": payload,
        "signature": hmac.new(_SECRET, payload_raw, hashlib.sha256).hexdigest(),
    }
    encrypted = _xor_bytes(_dump_json(data))
    LICENSE_FILE.write_text(base64.urlsafe_b64encode(encrypted).decode("ascii"), encoding="utf-8")


def _parse_zip_timestamp(value: str) -> date | None:
    fmt = "%Y%m%d%H%M%S" if len(value) == 14 else "%Y%m%d%H%M"
    try:
        return datetime.strptime(value, fmt).date()
    except ValueError:
        return None


def _dump_json(data: dict[str, Any]) -> bytes:
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _xor_bytes(data: bytes) -> bytes:
    output = bytearray()
    counter = 0
    while len(output) < len(data):
        block = hashlib.sha256(_SECRET + counter.to_bytes(4, "big")).digest()
        output.extend(block)
        counter += 1
    return bytes(value ^ key for value, key in zip(data, output))
