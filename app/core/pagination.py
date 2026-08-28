import base64
import json
import uuid
from datetime import UTC, datetime
from typing import Any


def encode_cursor(created_at: datetime, entity_id: uuid.UUID) -> str:
    """Encodes created_at timestamp and entity UUID into an opaque base64 cursor."""
    payload = {
        "ts": created_at.astimezone(UTC).isoformat(),
        "id": str(entity_id),
    }
    raw_bytes = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw_bytes).decode("utf-8")


def decode_cursor(cursor_str: str) -> tuple[datetime, uuid.UUID] | None:
    """Decodes opaque base64 cursor back into created_at timestamp and entity UUID."""
    try:
        raw_bytes = base64.urlsafe_b64decode(cursor_str.encode("utf-8"))
        payload: dict[str, Any] = json.loads(raw_bytes.decode("utf-8"))
        ts = datetime.fromisoformat(payload["ts"])
        entity_id = uuid.UUID(payload["id"])
        return ts, entity_id
    except Exception:
        return None
