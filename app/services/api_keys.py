import hashlib
import secrets
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import APIKey


def _hash_key(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()


def generate_api_key() -> str:
    """Return a newly generated API key string (prefix + random secret)."""
    return f"ak_{secrets.token_urlsafe(32)}"


def create_api_key(
    db: Session,
    *,
    name: str,
    created_by_user_id: Optional[int],
    metadata: Optional[dict] = None,
) -> tuple[APIKey, str]:
    """
    Create and persist a new API key.
    Returns (model, raw_key) where raw_key is only revealed at creation time.
    """
    raw_key = generate_api_key()
    key_hash = _hash_key(raw_key)
    prefix = raw_key[:12]

    api_key = APIKey(
        name=name,
        prefix=prefix,
        key_hash=key_hash,
        is_active=True,
        created_by_user_id=created_by_user_id,
        metadata_json=metadata,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key, raw_key


def verify_api_key(db: Session, raw_key: str) -> Optional[APIKey]:
    """Return APIKey if valid/active/not expired; otherwise None."""
    if not raw_key:
        return None
    key_hash = _hash_key(raw_key)
    now = datetime.now(timezone.utc)
    api_key = (
        db.query(APIKey)
        .filter(
            APIKey.key_hash == key_hash,
            APIKey.is_active.is_(True),
        )
        .first()
    )
    if not api_key:
        return None
    if api_key.expires_at and api_key.expires_at <= now:
        return None
    api_key.last_used_at = now
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return api_key


def serialize_api_key(api_key: APIKey) -> dict:
    return {
        "id": api_key.id,
        "name": api_key.name,
        "prefix": api_key.prefix,
        "is_active": bool(api_key.is_active),
        "created_at": api_key.created_at.isoformat() if api_key.created_at else None,
        "last_used_at": api_key.last_used_at.isoformat() if api_key.last_used_at else None,
        "created_by_user_id": api_key.created_by_user_id,
    }
