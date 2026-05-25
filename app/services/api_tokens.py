import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import asdict, dataclass
from datetime import date, datetime, time, timedelta, timezone
from threading import RLock
from typing import Any

from app.config import BASE_DIR


API_TOKENS_PATH = BASE_DIR / "api_tokens.json"
API_TOKEN_PREFIX = "cap_"
API_TOKEN_SECRET = "CapaReportApiTokenSecret2026"
_STORE_LOCK = RLock()


@dataclass
class ApiTokenRecord:
    id: str
    name: str
    token_hash: str
    prefix: str
    suffix: str
    created_at: str
    expires_at: str | None
    enabled: bool
    last_used_at: str | None = None
    last_used_from: str | None = None
    token: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def ensure_store() -> None:
    if API_TOKENS_PATH.exists():
        return
    with _STORE_LOCK:
        if API_TOKENS_PATH.exists():
            return
        API_TOKENS_PATH.write_text(json.dumps({"tokens": []}, ensure_ascii=False, indent=2), encoding="utf-8")


def list_tokens() -> list[dict[str, Any]]:
    with _STORE_LOCK:
        return [record_to_public_dict(record) for record in _load_records()]


def export_tokens() -> list[dict[str, Any]]:
    with _STORE_LOCK:
        return [record.to_dict() for record in _load_records()]


def import_tokens(items: Any) -> int:
    if not isinstance(items, list):
        return 0

    records: list[ApiTokenRecord] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        record = _record_from_dict(item)
        if record.token_hash:
            records.append(record)

    with _STORE_LOCK:
        _save_records(records)
    return len(records)


def create_token(
    name: str,
    expires_in_days: int | None = None,
    enabled: bool = True,
    expires_at: str | None = None,
) -> tuple[str, dict[str, Any]]:
    raw_token = generate_raw_token()
    resolved_expires_at = normalize_expiration(expires_at)
    if resolved_expires_at is None and expires_in_days is not None:
        resolved_expires_at = expires_at_from_days(expires_in_days)

    record = ApiTokenRecord(
        id=secrets.token_hex(8),
        name=name.strip() or "未命名 Token",
        token_hash=hash_token(raw_token),
        prefix=raw_token[:12],
        suffix=raw_token[-12:],
        created_at=utc_now(),
        expires_at=resolved_expires_at,
        enabled=bool(enabled),
        token=raw_token,
    )

    with _STORE_LOCK:
        records = _load_records()
        records.append(record)
        _save_records(records)

    return raw_token, record_to_public_dict(record)


def update_token(token_id: str, **changes: Any) -> dict[str, Any]:
    with _STORE_LOCK:
        records = _load_records()
        for index, record in enumerate(records):
            if record.id != token_id:
                continue

            if "name" in changes and isinstance(changes["name"], str):
                record.name = changes["name"].strip() or record.name
            if "enabled" in changes:
                record.enabled = bool(changes["enabled"])
            if "expires_at" in changes:
                record.expires_at = normalize_expiration(changes["expires_at"])

            records[index] = record
            _save_records(records)
            return record_to_public_dict(record)

    raise KeyError(f"Token not found: {token_id}")


def delete_token(token_id: str) -> None:
    with _STORE_LOCK:
        records = [record for record in _load_records() if record.id != token_id]
        _save_records(records)


def delete_tokens(token_ids: list[str]) -> int:
    token_id_set = {str(token_id).strip() for token_id in token_ids if str(token_id).strip()}
    if not token_id_set:
        return 0

    with _STORE_LOCK:
        records = _load_records()
        kept_records = [record for record in records if record.id not in token_id_set]
        _save_records(kept_records)
        return len(records) - len(kept_records)


def regenerate_token(token_id: str) -> tuple[str, dict[str, Any]]:
    with _STORE_LOCK:
        records = _load_records()
        for index, record in enumerate(records):
            if record.id != token_id:
                continue

            raw_token = generate_raw_token()
            record.token_hash = hash_token(raw_token)
            record.prefix = raw_token[:12]
            record.suffix = raw_token[-12:]
            record.token = raw_token
            record.created_at = utc_now()
            record.last_used_at = None
            record.last_used_from = None
            records[index] = record
            _save_records(records)
            return raw_token, record_to_public_dict(record)

    raise KeyError(f"Token not found: {token_id}")


def verify_api_token(raw_token: str) -> dict[str, Any] | None:
    ensure_store()
    token_hash = hash_token(raw_token)
    now = datetime.now(timezone.utc)
    with _STORE_LOCK:
        for record in _load_records():
            if not record.enabled or record.token_hash != token_hash:
                continue

            expires_at = parse_datetime(record.expires_at)
            if expires_at and expires_at < now:
                continue

            return record_to_context(record)

    return None


def touch_token_usage(raw_token: str, source: str | None = None) -> None:
    token_hash = hash_token(raw_token)
    now = utc_now()
    with _STORE_LOCK:
        records = _load_records()
        updated = False
        for index, record in enumerate(records):
            if record.token_hash != token_hash:
                continue
            record.last_used_at = now
            record.last_used_from = source or record.last_used_from
            records[index] = record
            updated = True
            break
        if updated:
            _save_records(records)


def generate_raw_token() -> str:
    return API_TOKEN_PREFIX + secrets.token_urlsafe(36)


def hash_token(raw_token: str) -> str:
    digest = hmac.new(API_TOKEN_SECRET.encode(), raw_token.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")


def normalize_expiration(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = str(value).strip()
    if not trimmed:
        return None
    parsed = parse_datetime(trimmed)
    if parsed is None:
        raise ValueError("Invalid expiration date")
    return parsed.isoformat(timespec="seconds")


def expires_at_from_days(days: int) -> str:
    safe_days = max(int(days), 1)
    expires_at = datetime.now(timezone.utc) + timedelta(days=safe_days)
    return expires_at.isoformat(timespec="seconds")


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed_date = date.fromisoformat(value)
        except ValueError:
            return None
        parsed = datetime.combine(parsed_date, time.max)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def record_to_public_dict(record: ApiTokenRecord, include_hash: bool = False) -> dict[str, Any]:
    expires_at = parse_datetime(record.expires_at)
    data = {
        "id": record.id,
        "name": record.name,
        "prefix": record.prefix,
        "suffix": record.suffix,
        "created_at": record.created_at,
        "expires_at": record.expires_at,
        "enabled": record.enabled,
        "last_used_at": record.last_used_at,
        "last_used_from": record.last_used_from,
        "expired": bool(expires_at and expires_at < datetime.now(timezone.utc)),
        "token": record.token,
        "token_available": bool(record.token),
    }
    if include_hash:
        data["token_hash"] = record.token_hash
    return data


def record_to_context(record: ApiTokenRecord) -> dict[str, Any]:
    return {
        "token_id": record.id,
        "name": record.name,
        "created_at": record.created_at,
        "expires_at": record.expires_at,
        "token_type": "api_token",
    }


def _load_records() -> list[ApiTokenRecord]:
    ensure_store()
    try:
        raw = json.loads(API_TOKENS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        raw = {"tokens": []}

    tokens = raw.get("tokens", []) if isinstance(raw, dict) else []
    records: list[ApiTokenRecord] = []
    for item in tokens:
        if not isinstance(item, dict):
            continue
        record = _record_from_dict(item)
        if record.token_hash:
            records.append(record)

    records.sort(key=lambda record: record.created_at, reverse=True)
    return records


def _record_from_dict(item: dict[str, Any]) -> ApiTokenRecord:
    raw_token = str(item.get("token") or "").strip() or None
    token_hash = str(item.get("token_hash") or "").strip()
    if raw_token and not token_hash:
        token_hash = hash_token(raw_token)

    prefix = str(item.get("prefix") or "")
    suffix = str(item.get("suffix") or "")
    if raw_token:
        prefix = prefix or raw_token[:12]
        suffix = suffix or raw_token[-12:]

    return ApiTokenRecord(
        id=str(item.get("id", "")) or secrets.token_hex(8),
        name=str(item.get("name", "未命名 Token")),
        token_hash=token_hash,
        prefix=prefix,
        suffix=suffix,
        created_at=str(item.get("created_at", utc_now())),
        expires_at=item.get("expires_at"),
        enabled=bool(item.get("enabled", True)),
        last_used_at=item.get("last_used_at"),
        last_used_from=item.get("last_used_from"),
        token=raw_token,
    )


def _save_records(records: list[ApiTokenRecord]) -> None:
    payload = {"tokens": [record.to_dict() for record in records]}
    API_TOKENS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
