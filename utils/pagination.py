import base64
import json
from datetime import datetime


def _pad_base64(value: str) -> str:
    padding = (-len(value)) % 4
    return value + ("=" * padding)


def encode_cursor(created_at: datetime, item_id: int) -> str:
    payload = {
        "created_at": created_at.isoformat(),
        "id": item_id,
    }
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None) -> tuple[datetime, int] | None:
    if not cursor:
        return None

    try:
        raw = base64.urlsafe_b64decode(_pad_base64(cursor)).decode("utf-8")
        payload = json.loads(raw)
        created_at = datetime.fromisoformat(payload["created_at"])
        item_id = int(payload["id"])
        return created_at, item_id
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return None
