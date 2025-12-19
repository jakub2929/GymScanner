import hashlib
import hmac
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import CalcomSettings, CalcomWebhookEvent, CalcomAdminSettings


def get_or_create_settings(db: Session) -> CalcomSettings:
    settings = db.query(CalcomSettings).first()
    if settings:
        return settings
    settings = CalcomSettings(is_enabled=False)
    db.add(settings)
    db.commit()
    db.refresh(settings)
    return settings


def get_or_create_admin_settings(db: Session, admin_id: int) -> CalcomAdminSettings:
    admin_settings = db.query(CalcomAdminSettings).filter(CalcomAdminSettings.admin_id == admin_id).first()
    if admin_settings:
        return admin_settings
    admin_settings = CalcomAdminSettings(admin_id=admin_id, is_enabled=False)
    db.add(admin_settings)
    db.commit()
    db.refresh(admin_settings)
    return admin_settings


def update_settings(
    db: Session,
    *,
    is_enabled: Optional[bool] = None,
    webhook_secret: Optional[str] = None,
    embed_code: Optional[str] = None,
) -> CalcomSettings:
    settings = get_or_create_settings(db)
    if is_enabled is not None:
        settings.is_enabled = is_enabled
    if webhook_secret is not None:
        settings.webhook_secret = webhook_secret
    if embed_code is not None:
        settings.embed_code = embed_code
    settings.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(settings)
    return settings


def update_admin_settings(
    db: Session,
    *,
    admin_id: int,
    is_enabled: Optional[bool] = None,
    embed_code: Optional[str] = None,
) -> CalcomAdminSettings:
    admin_settings = get_or_create_admin_settings(db, admin_id)
    if is_enabled is not None:
        admin_settings.is_enabled = is_enabled
    if embed_code is not None:
        admin_settings.embed_code = embed_code
    admin_settings.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(admin_settings)
    return admin_settings


def verify_signature(signature: str, body: bytes, secret: str) -> bool:
    """
    Cal.com webhooks use HMAC SHA256. Signatures are often in the format:
    - "sha256=<hex>"
    - "<hex>"
    """
    if not signature or not secret:
        return False
    cleaned = signature.strip()
    if "=" in cleaned:
        cleaned = cleaned.split("=", 1)[1]
    computed = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(computed, cleaned)


def record_webhook_event(
    db: Session,
    *,
    admin_id: Optional[int],
    event_id: Optional[str],
    event_type: Optional[str],
    payload_hash: str,
    payload: dict,
    status: str = "received",
    error_message: Optional[str] = None,
) -> CalcomWebhookEvent:
    existing: Optional[CalcomWebhookEvent] = None
    if event_id:
        existing = db.query(CalcomWebhookEvent).filter(CalcomWebhookEvent.event_id == event_id).first()
    if not existing:
        existing = (
            db.query(CalcomWebhookEvent)
            .filter(CalcomWebhookEvent.payload_hash == payload_hash, CalcomWebhookEvent.status != "errored")
            .first()
        )

    now = datetime.now(timezone.utc)
    if existing:
        existing.status = "duplicate"
        existing.received_at = now
        db.commit()
        db.refresh(existing)
        return existing

    event = CalcomWebhookEvent(
        admin_id=admin_id,
        event_id=event_id,
        event_type=event_type,
        payload_hash=payload_hash,
        payload=payload,
        status=status,
        error_message=error_message,
        received_at=now,
    )
    db.add(event)
    db.commit()
    db.refresh(event)
    return event


def list_recent_events(db: Session, limit: int = 20) -> list[CalcomWebhookEvent]:
    return (
        db.query(CalcomWebhookEvent)
        .order_by(CalcomWebhookEvent.received_at.desc(), CalcomWebhookEvent.id.desc())
        .limit(limit)
        .all()
    )
