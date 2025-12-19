from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import User, CalcomWebhookEvent
from app.routes.admin import require_admin
from app.services.calcom import (
    get_or_create_settings,
    get_or_create_admin_settings,
    list_recent_events,
    record_webhook_event,
    update_admin_settings,
    update_settings,
    verify_signature,
)

router = APIRouter()

BOOKING_EVENT_TYPES = {"BOOKING_CREATED", "BOOKING_RESCHEDULED", "BOOKING_CANCELLED"}
BOOKING_EVENT_TYPES_ALL = BOOKING_EVENT_TYPES.union({val.lower() for val in BOOKING_EVENT_TYPES})


class CalcomSettingsResponse(BaseModel):
    is_enabled: bool  # per-admin toggle
    has_secret: bool
    webhook_url: str
    admin_webhook_url: str | None = None
    embed_code: str | None = None
    last_event_type: str | None = None
    last_event_id: str | None = None
    last_received_at: str | None = None
    last_error: str | None = None


class CalcomSettingsUpdate(BaseModel):
    is_enabled: bool | None = None
    webhook_secret: str | None = Field(default=None, min_length=8, max_length=256)
    embed_code: str | None = None


class CalcomPublicResponse(BaseModel):
    is_enabled: bool
    embed_code: str | None = None
    providers: list[dict] | None = None


class CalcomEventResponse(BaseModel):
    id: int
    admin_id: int | None = None
    event_id: str | None
    event_type: str | None
    status: str
    received_at: str | None
    error_message: str | None = None


class CalcomBookingResponse(BaseModel):
    id: int
    admin_id: int | None = None
    event_id: str | None = None
    event_type: str | None = None
    status: str | None = None
    booking_id: str | None = None
    uid: str | None = None
    ical_uid: str | None = None
    reschedule_uid: str | None = None
    location: str | None = None
    title: str | None = None
    organizer_name: str | None = None
    organizer_email: str | None = None
    attendee_name: str | None = None
    attendee_email: str | None = None
    attendee_phone: str | None = None
    start_time: str | None = None
    end_time: str | None = None
    timezone: str | None = None
    notes: str | None = None
    reschedule_reason: str | None = None
    cancel_reason: str | None = None
    created_at: str | None = None
    received_at: str | None = None
    history: list[dict] | None = None
    raw_payload: dict | None = None


def _serialize_settings(
    settings,
    admin_settings,
    webhook_url: str,
    has_secret: bool,
    admin_webhook_url: str | None,
) -> CalcomSettingsResponse:
    return CalcomSettingsResponse(
        is_enabled=bool(admin_settings.is_enabled),
        has_secret=has_secret,
        webhook_url=webhook_url,
        admin_webhook_url=admin_webhook_url,
        embed_code=admin_settings.embed_code,
        last_event_type=settings.last_event_type,
        last_event_id=settings.last_event_id,
        last_received_at=settings.last_received_at.isoformat() if settings.last_received_at else None,
        last_error=settings.last_error,
    )


def _serialize_event(event) -> CalcomEventResponse:
    return CalcomEventResponse(
        id=event.id,
        admin_id=event.admin_id,
        event_id=event.event_id,
        event_type=event.event_type,
        status=event.status,
        received_at=event.received_at.isoformat() if event.received_at else None,
        error_message=event.error_message,
    )


def _extract_event_info(payload: dict) -> tuple[Optional[str], Optional[str]]:
    event_type = (
        payload.get("triggerEvent")
        or payload.get("event")
        or payload.get("type")
        or payload.get("action")
        or "unknown"
    )
    event_id = (
        payload.get("id")
        or payload.get("eventId")
        or payload.get("bookingId")
        or payload.get("uid")
        or (payload.get("booking") or {}).get("id")
        or (payload.get("booking") or {}).get("uid")
    )
    return event_type, event_id


def _normalize_payload_body(payload: dict) -> dict:
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("payload"), dict):
        return payload["payload"]
    if isinstance(payload.get("data"), dict):
        return payload["data"]
    if isinstance(payload.get("booking"), dict):
        return payload["booking"]
    return payload


def _from_responses(responses: dict, key: str) -> Optional[str]:
    if not isinstance(responses, dict):
        return None
    entry = responses.get(key) or responses.get(key.lower())
    if isinstance(entry, dict):
        val = entry.get("value")
        if val is not None and val != "":
            return str(val)
    if isinstance(entry, str) and entry.strip():
        return entry
    return None


def _extract_location(payload_body: dict, responses: dict) -> Optional[str]:
    loc = payload_body.get("location")
    if isinstance(loc, dict):
        if loc.get("value"):
            return str(loc.get("value"))
        if loc.get("optionValue"):
            return str(loc.get("optionValue"))
    if isinstance(loc, str) and loc.strip():
        return loc
    resp_loc = _from_responses(responses, "location")
    return resp_loc


def _to_iso(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        dt = datetime.fromisoformat(normalized)
        return dt.isoformat()
    except Exception:
        return value


def _normalize_status(event_type: Optional[str]) -> str | None:
    if not event_type:
        return None
    upper = event_type.upper()
    if "CANCEL" in upper:
        return "cancelled"
    if "RESCHEDULE" in upper:
        return "rescheduled"
    if "CREATED" in upper:
        return "created"
    return event_type.lower()


def _parse_iso_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        return datetime.fromisoformat(normalized)
    except Exception:
        return None


def _booking_key(parsed: CalcomBookingResponse) -> str:
    def normalize(val: Optional[str]) -> Optional[str]:
        if val is None:
            return None
        cleaned = str(val).strip().lower()
        if cleaned.endswith("@cal.com"):
            cleaned = cleaned.rsplit("@", 1)[0]
        return cleaned or None

    return (
        normalize(parsed.ical_uid)
        or normalize(parsed.reschedule_uid)
        or normalize(parsed.uid)
        or normalize(parsed.booking_id)
        or normalize(parsed.event_id)
        or normalize(parsed.received_at)
        or str(parsed.id)
    )


def _booking_from_event(event) -> Optional[CalcomBookingResponse]:
    raw_payload = event.payload or {}
    payload_body = _normalize_payload_body(raw_payload)
    if not isinstance(payload_body, dict):
        return None

    responses = payload_body.get("responses") or {}
    attendees = payload_body.get("attendees") or []
    first_attendee = attendees[0] if attendees else {}
    organizer = payload_body.get("organizer") or {}

    attendee_name = (
        _from_responses(responses, "name")
        or first_attendee.get("name")
        or first_attendee.get("firstName")
        or first_attendee.get("lastName")
    )
    attendee_email = _from_responses(responses, "email") or first_attendee.get("email")
    attendee_phone = (
        _from_responses(responses, "attendeePhoneNumber")
        or _from_responses(responses, "phone")
        or first_attendee.get("phone")
    )
    reschedule_reason = (
        payload_body.get("rescheduleReason")
        or _from_responses(responses, "rescheduleReason")
        or payload_body.get("reschedule_reason")
    )
    cancel_reason = payload_body.get("cancellationReason") or _from_responses(responses, "cancellationReason")
    notes = payload_body.get("additionalNotes") or _from_responses(responses, "notes") or payload_body.get("description")

    title = payload_body.get("eventTitle") or payload_body.get("title") or payload_body.get("type")
    booking_id = payload_body.get("bookingId") or payload_body.get("id")
    start_time = payload_body.get("startTime") or payload_body.get("start_time")
    end_time = payload_body.get("endTime") or payload_body.get("end_time")
    timezone = organizer.get("timeZone") or first_attendee.get("timeZone")
    location = _extract_location(payload_body, responses)

    status_label = _normalize_status(event.event_type)

    reschedule_uid = payload_body.get("rescheduleUid") or raw_payload.get("rescheduleUid")
    uid = payload_body.get("uid") or reschedule_uid or payload_body.get("iCalUID")
    ical_uid = payload_body.get("iCalUID") or raw_payload.get("iCalUID") or reschedule_uid
    return CalcomBookingResponse(
        id=event.id,
        admin_id=event.admin_id,
        event_id=event.event_id,
        event_type=event.event_type,
        status=status_label,
        booking_id=str(booking_id) if booking_id is not None else None,
        uid=uid,
        ical_uid=ical_uid,
        reschedule_uid=reschedule_uid,
        title=title,
        organizer_name=organizer.get("name"),
        organizer_email=organizer.get("email"),
        attendee_name=attendee_name,
        attendee_email=attendee_email,
        attendee_phone=attendee_phone,
        start_time=_to_iso(start_time),
        end_time=_to_iso(end_time),
        timezone=timezone,
        location=location,
        notes=notes,
        reschedule_reason=reschedule_reason,
        cancel_reason=cancel_reason,
        created_at=_to_iso(raw_payload.get("createdAt") or payload_body.get("createdAt")),
        received_at=event.received_at.isoformat() if event.received_at else None,
        history=[],
        raw_payload=raw_payload,
    )


async def _handle_webhook(request: Request, db: Session, admin_id: Optional[int] = None):
    target_admin = None
    if admin_id is not None:
        from app.models import User

        target_admin = db.query(User).filter(User.id == admin_id).first()
        if not target_admin:
            raise HTTPException(status_code=404, detail="Admin not found")
        if not target_admin.is_admin:
            raise HTTPException(status_code=403, detail="Webhook admin must be an admin user")
        admin_settings = get_or_create_admin_settings(db, target_admin.id)
        if not admin_settings.is_enabled:
            raise HTTPException(status_code=503, detail="Cal.com integration is disabled for this admin")
    else:
        # If hitting generic endpoint, require global enable + at least one admin enabled
        enabled_any = db.query(User).filter(User.is_admin.is_(True)).count() > 0
        if not enabled_any:
            raise HTTPException(status_code=503, detail="Cal.com integration disabled")

    settings = get_or_create_settings(db)
    if not settings.is_enabled:
        raise HTTPException(status_code=503, detail="Cal.com integration is disabled")

    secret = settings.webhook_secret or os.getenv("CALCOM_WEBHOOK_SECRET")
    if not secret:
        raise HTTPException(status_code=403, detail="Webhook secret is not configured")

    raw_body = await request.body()
    signature = (
        request.headers.get("x-cal-signature")
        or request.headers.get("x-hook-signature")
        or request.headers.get("x-cal-signature-256")
    )
    if not signature or not verify_signature(signature, raw_body, secret):
        raise HTTPException(status_code=401, detail="Invalid webhook signature")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type, event_id = _extract_event_info(payload)
    payload_hash = hashlib.sha256(raw_body).hexdigest()

    try:
        event = record_webhook_event(
            db,
            admin_id=admin_id,
            event_id=event_id,
            event_type=event_type,
            payload_hash=payload_hash,
            payload=payload,
            status="received",
        )
        settings.last_event_type = event_type
        settings.last_event_id = event_id or event.event_id
        settings.last_received_at = datetime.now(timezone.utc)
        settings.last_error = None
        db.commit()
        stored = event.status != "duplicate"
        return {"status": "ok", "stored": stored, "event_type": event_type, "event_id": settings.last_event_id}
    except Exception as exc:  # noqa: BLE001
        settings.last_error = str(exc)
        settings.last_received_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to record webhook event")


@router.post("/integrations/calcom/webhook", name="calcom_webhook_handler")
async def calcom_webhook_handler(request: Request, db: Session = Depends(get_db)):
    return await _handle_webhook(request, db, admin_id=None)


@router.post("/integrations/calcom/webhook/{admin_id}", name="calcom_webhook_handler_with_admin")
async def calcom_webhook_handler_with_admin(admin_id: int, request: Request, db: Session = Depends(get_db)):
    return await _handle_webhook(request, db, admin_id=admin_id)


@router.get("/admin/calcom/settings", response_model=CalcomSettingsResponse)
def get_calcom_settings(request: Request, db: Session = Depends(get_db), current_admin: User = Depends(require_admin)):
    settings = get_or_create_settings(db)
    admin_settings = get_or_create_admin_settings(db, current_admin.id)
    webhook_url = str(request.url_for("calcom_webhook_handler"))
    admin_webhook_url = None
    if current_admin and current_admin.id:
        admin_webhook_url = str(
            request.url_for("calcom_webhook_handler_with_admin", admin_id=current_admin.id)
        )
    has_secret = bool(settings.webhook_secret or os.getenv("CALCOM_WEBHOOK_SECRET"))
    return _serialize_settings(settings, admin_settings, webhook_url, has_secret, admin_webhook_url)


@router.post("/admin/calcom/settings", response_model=CalcomSettingsResponse)
def update_calcom_settings(
    request: Request,
    payload: CalcomSettingsUpdate,
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
):
    settings = get_or_create_settings(db)
    admin_settings = get_or_create_admin_settings(db, current_admin.id)
    current_secret = settings.webhook_secret or os.getenv("CALCOM_WEBHOOK_SECRET")
    if payload.is_enabled and not (payload.webhook_secret or current_secret):
        raise HTTPException(status_code=400, detail="Webhook secret must be set before enabling Cal.com integration")

    # global secret stays in calcom_settings
    updated = update_settings(
        db,
        is_enabled=settings.is_enabled,  # keep legacy value unchanged
        webhook_secret=payload.webhook_secret if payload.webhook_secret is not None else None,
        embed_code=settings.embed_code,
    )
    updated_admin = update_admin_settings(
        db,
        admin_id=current_admin.id,
        is_enabled=payload.is_enabled,
        embed_code=payload.embed_code if payload.embed_code is not None else admin_settings.embed_code,
    )
    webhook_url = str(request.url_for("calcom_webhook_handler"))
    has_secret = bool(updated.webhook_secret or os.getenv("CALCOM_WEBHOOK_SECRET"))
    admin_webhook_url = None
    if current_admin and current_admin.id:
        admin_webhook_url = str(
            request.url_for("calcom_webhook_handler_with_admin", admin_id=current_admin.id)
        )
    return _serialize_settings(updated, updated_admin, webhook_url, has_secret, admin_webhook_url)


@router.get("/admin/calcom/events", response_model=list[CalcomEventResponse])
def list_calcom_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
    limit: int = Query(default=20, ge=1, le=100),
):
    events = list_recent_events(db, limit=limit)
    return [_serialize_event(evt) for evt in events]


@router.get("/admin/calcom/bookings", response_model=list[CalcomBookingResponse])
def list_calcom_bookings(
    db: Session = Depends(get_db),
    current_admin: User = Depends(require_admin),
    limit: int = Query(default=50, ge=1, le=200),
):
    events = (
        db.query(CalcomWebhookEvent)
        .filter(CalcomWebhookEvent.event_type.in_(BOOKING_EVENT_TYPES_ALL))
        .filter(CalcomWebhookEvent.status != "duplicate")
        .filter(or_(CalcomWebhookEvent.admin_id == current_admin.id, CalcomWebhookEvent.admin_id.is_(None)))
        .order_by(CalcomWebhookEvent.received_at.desc(), CalcomWebhookEvent.id.desc())
        .limit(limit)
        .all()
    )
    grouped: dict[str, CalcomBookingResponse] = {}
    for evt in events:
        parsed = _booking_from_event(evt)
        if not parsed:
            continue
        key = _booking_key(parsed)
        existing = grouped.get(key)
        history_item = {
            "event_type": parsed.event_type,
            "status": parsed.status,
            "received_at": parsed.received_at,
            "notes": parsed.notes,
            "reschedule_reason": parsed.reschedule_reason,
            "cancel_reason": parsed.cancel_reason,
            "start_time": parsed.start_time,
            "end_time": parsed.end_time,
            "location": parsed.location,
            "raw_payload": parsed.raw_payload,
        }
        if existing:
            existing.history = (existing.history or []) + [history_item]

            existing_dt = _parse_iso_dt(existing.received_at)
            parsed_dt = _parse_iso_dt(parsed.received_at)
            is_parsed_newer = parsed_dt and (not existing_dt or parsed_dt > existing_dt)

            if is_parsed_newer or not existing.status:
                existing.status = parsed.status or existing.status
                existing.event_type = parsed.event_type or existing.event_type
                existing.received_at = parsed.received_at or existing.received_at
            if not existing.reschedule_uid and parsed.reschedule_uid:
                existing.reschedule_uid = parsed.reschedule_uid

            # Start/end/location should only move forward when parsed event is newer (e.g., reschedule)
            if is_parsed_newer:
                if parsed.start_time:
                    existing.start_time = parsed.start_time
                if parsed.end_time:
                    existing.end_time = parsed.end_time
                if parsed.location:
                    existing.location = parsed.location

            # Notes / reasons: keep the latest available info
            if is_parsed_newer or existing.notes is None:
                if parsed.notes is not None:
                    existing.notes = parsed.notes
            if is_parsed_newer or existing.reschedule_reason is None:
                if parsed.reschedule_reason is not None:
                    existing.reschedule_reason = parsed.reschedule_reason
            if is_parsed_newer or existing.cancel_reason is None:
                if parsed.cancel_reason is not None:
                    existing.cancel_reason = parsed.cancel_reason

            if is_parsed_newer and parsed.raw_payload:
                existing.raw_payload = parsed.raw_payload
        else:
            parsed.history = [history_item]
            grouped[key] = parsed

    def sort_key(item: CalcomBookingResponse):
        start = _parse_iso_dt(item.start_time)
        if start:
            return start
        recv = _parse_iso_dt(item.received_at)
        return recv or datetime.min

    return sorted(grouped.values(), key=sort_key, reverse=True)


@router.get("/calcom/my-bookings", response_model=list[CalcomBookingResponse])
def list_my_calcom_bookings(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=200),
):
    user_email = (current_user.email or "").lower()
    events = (
        db.query(CalcomWebhookEvent)
        .filter(CalcomWebhookEvent.event_type.in_(BOOKING_EVENT_TYPES_ALL))
        .filter(CalcomWebhookEvent.status != "duplicate")
        .order_by(CalcomWebhookEvent.received_at.desc(), CalcomWebhookEvent.id.desc())
        .limit(limit)
        .all()
    )
    grouped: dict[str, CalcomBookingResponse] = {}
    for evt in events:
        parsed = _booking_from_event(evt)
        if not parsed or not parsed.attendee_email or parsed.attendee_email.lower() != user_email:
            continue
        key = _booking_key(parsed)
        existing = grouped.get(key)
        history_item = {
            "event_type": parsed.event_type,
            "status": parsed.status,
            "received_at": parsed.received_at,
            "notes": parsed.notes,
            "reschedule_reason": parsed.reschedule_reason,
            "cancel_reason": parsed.cancel_reason,
            "start_time": parsed.start_time,
            "end_time": parsed.end_time,
            "location": parsed.location,
            "raw_payload": parsed.raw_payload,
        }
        if existing:
            existing.history = (existing.history or []) + [history_item]

            existing_dt = _parse_iso_dt(existing.received_at)
            parsed_dt = _parse_iso_dt(parsed.received_at)
            is_parsed_newer = parsed_dt and (not existing_dt or parsed_dt > existing_dt)

            if is_parsed_newer or not existing.status:
                existing.status = parsed.status or existing.status
                existing.event_type = parsed.event_type or existing.event_type
                existing.received_at = parsed.received_at or existing.received_at

            if not existing.reschedule_uid and parsed.reschedule_uid:
                existing.reschedule_uid = parsed.reschedule_uid

            if is_parsed_newer:
                if parsed.start_time:
                    existing.start_time = parsed.start_time
                if parsed.end_time:
                    existing.end_time = parsed.end_time
                if parsed.location:
                    existing.location = parsed.location

            if is_parsed_newer or existing.notes is None:
                if parsed.notes is not None:
                    existing.notes = parsed.notes
            if is_parsed_newer or existing.reschedule_reason is None:
                if parsed.reschedule_reason is not None:
                    existing.reschedule_reason = parsed.reschedule_reason
            if is_parsed_newer or existing.cancel_reason is None:
                if parsed.cancel_reason is not None:
                    existing.cancel_reason = parsed.cancel_reason

            if is_parsed_newer and parsed.raw_payload:
                existing.raw_payload = parsed.raw_payload
        else:
            parsed.history = [history_item]
            grouped[key] = parsed

    def sort_key(item: CalcomBookingResponse):
        start = _parse_iso_dt(item.start_time)
        if start:
            return start
        recv = _parse_iso_dt(item.received_at)
        return recv or datetime.min

    return sorted(grouped.values(), key=sort_key, reverse=True)


@router.get("/calcom/public", response_model=CalcomPublicResponse)
def calcom_public_settings(db: Session = Depends(get_db)):
    settings = get_or_create_settings(db)
    if not settings.is_enabled:
        return CalcomPublicResponse(is_enabled=False, embed_code=None, providers=[])

    admins = db.query(User).filter(User.is_admin.is_(True)).all()
    providers: list[dict] = []
    for admin in admins:
        admin_settings = get_or_create_admin_settings(db, admin.id)
        if not admin_settings.is_enabled:
            continue
        admin_embed = (admin_settings.embed_code or "").strip() or (settings.embed_code or "").strip()
        if not admin_embed:
            continue

        admin_embed_is_url = False
        admin_embed_origin = None
        admin_embed_path = None
        if admin_embed.startswith("http://") or admin_embed.startswith("https://"):
            parsed_admin = urlparse(admin_embed)
            admin_embed_is_url = True
            admin_embed_origin = f"{parsed_admin.scheme}://{parsed_admin.netloc}"
            admin_embed_path = parsed_admin.path.lstrip("/")

        providers.append(
            {
                "admin_id": admin.id,
                "name": admin.name or (admin.email.split("@")[0] if admin.email else f"Admin {admin.id}"),
                "email": admin.email,
                "embed_code": admin_embed,
                "embed_is_url": admin_embed_is_url,
                "embed_origin": admin_embed_origin,
                "embed_path": admin_embed_path,
            }
        )

    return CalcomPublicResponse(
        is_enabled=True,
        embed_code=settings.embed_code,
        providers=providers,
    )
