from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from app.database import get_db
from app.models import AccessToken, AccessLog, User
from app.services.membership import MembershipService, serialize_membership_for_response
from app.services.presence_sessions import PresenceSessionService
from app.services.presence import set_presence
from datetime import datetime, timezone, timedelta
import logging
import os
import time
from collections import deque

logger = logging.getLogger(__name__)

router = APIRouter()

# Cooldown duration in seconds
COOLDOWN_SECONDS = 60
RATE_LIMIT_PER_MINUTE = int(os.getenv("VERIFY_RATE_LIMIT_PER_MINUTE", "120"))
_rate_limit_window_seconds = 60
_rate_limit_buckets: dict[str, deque[float]] = {}


def _get_api_verify_key() -> str | None:
    """Return API key from env (API_VERIFY_KEY preferred, TURNSTILE_API_KEY as fallback)."""
    return os.getenv("API_VERIFY_KEY") or os.getenv("TURNSTILE_API_KEY")


def _enforce_rate_limit(key: str):
    """Simple sliding window rate limit per API key."""
    if RATE_LIMIT_PER_MINUTE <= 0:
        return
    now = time.time()
    bucket = _rate_limit_buckets.setdefault(key, deque())
    window_start = now - _rate_limit_window_seconds
    while bucket and bucket[0] < window_start:
        bucket.popleft()
    if len(bucket) >= RATE_LIMIT_PER_MINUTE:
        raise HTTPException(
            status_code=http_status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded",
        )
    bucket.append(now)


def _require_api_key(request: Request):
    """Require global API key for /api/verify (protects PIN/QR endpoint)."""
    expected = _get_api_verify_key()
    provided = request.headers.get("X-API-KEY")
    if not expected:
        raise HTTPException(
            status_code=http_status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="API key not configured",
        )
    if provided != expected:
        raise HTTPException(
            status_code=http_status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized",
        )
    _enforce_rate_limit(provided)


def log_access(
    db: Session,
    *,
    token_id: int | None,
    token_string: str,
    status: str,
    reason: str | None,
    ip_address: str | None,
    user_agent: str | None,
    direction: str = "in",
    scanner_id: str | None = None,
    raw_data: str | None = None,
    commit: bool = True,
    metadata: dict | None = None,
):
    """Persist access log entry with optional commit control."""
    try:
        access_log = AccessLog(
            token_id=token_id,
            token_string=token_string,
            status=status,
            reason=reason,
            ip_address=ip_address,
            user_agent=user_agent,
            direction=direction,
            scanner_id=scanner_id,
            raw_data=raw_data,
            metadata_json=metadata,
        )
        db.add(access_log)
        if commit:
            db.commit()
    except Exception as e:
        logger.error(f"Error logging access attempt: {e}", exc_info=True)
        db.rollback()

class VerifyRequest(BaseModel):
    token: str
    
    class Config:
        # Allow any string, no pattern validation
        json_schema_extra = {
            "example": {
                "token": "550e8400-e29b-41d4-a716-446655440000"
            }
        }

class MembershipInfo(BaseModel):
    has_membership: bool
    membership_id: int | None = None
    package_id: int | None = None
    package_name: str | None = None
    package_slug: str | None = None
    package_type: str | None = None
    status: str | None = None
    membership_type: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    daily_limit_enabled: bool | None = None
    daily_limit: int | None = None
    daily_usage_count: int | None = None
    sessions_total: int | None = None
    sessions_used: int | None = None
    auto_renew: bool | None = None
    notes: str | None = None
    metadata: dict | None = None
    reason: str | None = None
    message: str | None = None
    daily_limit_hit: bool | None = None


class VerifyResponse(BaseModel):
    allowed: bool  # True = access granted, False = access denied
    reason: str  # "ok" | "no_credits" | "cooldown" | "invalid_token" | "token_not_found" | "token_deactivated" | "user_not_found"
    credits_left: int  # Number of credits remaining after this scan
    cooldown_seconds_left: int | None = None  # Seconds until cooldown expires (None if no cooldown)
    user_name: str | None = None
    user_email: str | None = None
    open_door: bool | None = None
    door_open_duration: int | None = None
    user: dict | None = None
    message: str | None = None
    membership: MembershipInfo | None = None


class MembershipCheckResponse(BaseModel):
    allowed: bool
    reason: str
    membership: MembershipInfo | None = None
    message: str | None = None

async def process_verification(
    token_str: str,
    request: Request,
    db: Session,
    *,
    direction: str = "in",
    scanner_id: str | None = None,
    raw_data: str | None = None,
) -> VerifyResponse:
    """
    Shared verification logic for web scanner and turnstile scanner.
    direction/scanner_id/raw_data are used for richer logging.
    """
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)

    try:
        token = db.query(AccessToken).filter(AccessToken.token == token_str).first()
        if not token:
            log_access(
                db,
                token_id=None,
                token_string=token_str,
                status="deny",
                reason="Token not found",
                ip_address=client_ip,
                user_agent=user_agent,
                direction=direction,
                scanner_id=scanner_id,
                raw_data=raw_data,
            )
            return VerifyResponse(
                allowed=False,
                reason="token_not_found",
                credits_left=0,
                cooldown_seconds_left=None,
            )

        if not token.is_active:
            log_access(
                db,
                token_id=token.id,
                token_string=token_str,
                status="deny",
                reason="Token deactivated",
                ip_address=client_ip,
                user_agent=user_agent,
                direction=direction,
                scanner_id=scanner_id,
                raw_data=raw_data,
            )
            return VerifyResponse(
                allowed=False,
                reason="token_deactivated",
                credits_left=0,
                cooldown_seconds_left=None,
            )

        user = db.query(User).filter(User.id == token.user_id).first()
        if not user:
            log_access(
                db,
                token_id=None,
                token_string=token_str,
                status="deny",
                reason="User not found",
                ip_address=client_ip,
                user_agent=user_agent,
                direction=direction,
                scanner_id=scanner_id,
                raw_data=raw_data,
            )
            return VerifyResponse(
                allowed=False,
                reason="user_not_found",
                credits_left=0,
                cooldown_seconds_left=None,
            )

        user_active_tokens = (
            db.query(AccessToken)
            .filter(
                and_(
                    AccessToken.user_id == user.id,
                    AccessToken.is_active == True,
                    AccessToken.last_scan_at.isnot(None),
                )
            )
            .order_by(AccessToken.last_scan_at.desc())
            .first()
        )

        cooldown_seconds_left = None
        if user_active_tokens and user_active_tokens.last_scan_at:
            last_scan_time = user_active_tokens.last_scan_at
            if last_scan_time.tzinfo is None:
                last_scan_time = last_scan_time.replace(tzinfo=timezone.utc)

            now = datetime.now(timezone.utc)
            time_since_last_scan = now - last_scan_time
            if time_since_last_scan.total_seconds() < COOLDOWN_SECONDS:
                cooldown_seconds_left = int(
                    COOLDOWN_SECONDS - time_since_last_scan.total_seconds()
                )
                log_access(
                    db,
                    token_id=token.id,
                    token_string=token_str,
                    status="deny",
                    reason=f"Cooldown active ({cooldown_seconds_left}s remaining)",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    direction=direction,
                    scanner_id=scanner_id,
                    raw_data=raw_data,
                )
                return VerifyResponse(
                    allowed=False,
                    reason="cooldown",
                    credits_left=user.credits or 0,
                    cooldown_seconds_left=cooldown_seconds_left,
                )

        membership_service = MembershipService(db)
        now_ts = datetime.now(timezone.utc)
        membership = membership_service.get_active_membership(user.id, now_ts)
        membership_metadata = {"membership_id": membership.id, "package_id": membership.package_id} if membership else None
        membership_payload = None
        access_via_membership = False

        if membership:
            verdict = membership_service.can_consume_entry(membership, at_ts=now_ts)
            membership_payload = serialize_membership_for_response(
                membership,
                reason=verdict.reason,
                daily_limit_hit=verdict.daily_limit_hit,
            )
            if not verdict.allowed:
                log_access(
                    db,
                    token_id=token.id,
                    token_string=token_str,
                    status="deny",
                    reason=f"Membership denied ({verdict.reason})",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    direction=direction,
                    scanner_id=scanner_id,
                    raw_data=raw_data,
                    metadata=membership_metadata,
                )
                return VerifyResponse(
                    allowed=False,
                    reason=verdict.reason or "membership_denied",
                    credits_left=user.credits or 0,
                    cooldown_seconds_left=None,
                    user_name=user.name,
                    user_email=user.email,
                    message=membership_payload.get("message") if membership_payload else None,
                    membership=membership_payload,
                )
            access_via_membership = True
        else:
            membership_payload = serialize_membership_for_response(None, reason="membership_missing")

        if not access_via_membership:
            # Kreditová logika: pouze kontrola, bez odečtu
            if user.credits is None or user.credits <= 0:
                log_access(
                    db,
                    token_id=token.id,
                    token_string=token_str,
                    status="deny",
                    reason="No credits available",
                    ip_address=client_ip,
                    user_agent=user_agent,
                    direction=direction,
                    scanner_id=scanner_id,
                    raw_data=raw_data,
                    metadata=membership_metadata,
                )
                return VerifyResponse(
                    allowed=False,
                    reason="no_credits",
                    credits_left=user.credits or 0,
                    cooldown_seconds_left=None,
                    message=membership_payload.get("message") if membership_payload else None,
                    membership=membership_payload,
                )

        try:
            credits_after = user.credits or 0

            now = datetime.now(timezone.utc)
            token.used_at = now
            token.scan_count = (token.scan_count or 0) + 1
            token.last_scan_at = now

            db.query(AccessToken).filter(
                and_(AccessToken.user_id == user.id, AccessToken.is_active == True)
            ).update({"last_scan_at": now}, synchronize_session=False)

            log_access(
                db,
                token_id=token.id,
                token_string=token_str,
                status="allow",
                reason="membership_ok" if access_via_membership else f"Access granted (credits remaining: {credits_after})",
                ip_address=client_ip,
                user_agent=user_agent,
                direction=direction,
                scanner_id=scanner_id,
                raw_data=raw_data,
                commit=False,
                metadata=membership_metadata,
            )

            if access_via_membership and membership:
                membership_service.record_entry_usage(membership, at_ts=now)

            db.commit()
            return VerifyResponse(
                allowed=True,
                reason="ok",
                credits_left=credits_after,
                cooldown_seconds_left=COOLDOWN_SECONDS,
                user_name=user.name,
                user_email=user.email,
                message=membership_payload.get("message") if membership_payload else None,
                membership=membership_payload,
            )

        except Exception as e:
            logger.error(f"Error processing access grant: {e}", exc_info=True)
            db.rollback()
            return VerifyResponse(
                allowed=False,
                reason="invalid_token",
                credits_left=user.credits or 0,
                cooldown_seconds_left=None,
            )

    except Exception as e:
        logger.error(f"Unexpected error in verify_token: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}",
        )


@router.post("/verify", response_model=VerifyResponse)
async def verify_token(
    verify_request: VerifyRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verify a QR code token for turnstile access.
    Returns allowed: true/false with reason and credits_left.
    Implements 60-second cooldown on user level (all tokens of same user share cooldown).
    Logs all access attempts for audit purposes.
    """
    _require_api_key(request)
    token_str = verify_request.token
    return await process_verification(token_str, request, db, direction="in")


def _membership_check(
    token_str: str,
    db: Session,
    *,
    record_usage: bool,
    direction: str,
) -> MembershipCheckResponse:
    """
    Shared membership verification.
    record_usage=True => zaznamená spotřebu vstupu (daily/session).
    record_usage=False => pouze ověří.
    direction: "entry" nebo "exit" pro správu presence.
    """
    token = db.query(AccessToken).filter(AccessToken.token == token_str.strip()).first()
    if not token:
        return MembershipCheckResponse(
            allowed=False,
            reason="token_not_found",
            membership=None,
            message=None,
        )
    if not token.is_active:
        return MembershipCheckResponse(
            allowed=False,
            reason="token_deactivated",
            membership=None,
            message=None,
        )

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        return MembershipCheckResponse(
            allowed=False,
            reason="user_not_found",
            membership=None,
            message=None,
        )

    now_ts = datetime.now(timezone.utc)
    membership_service = MembershipService(db)
    membership = membership_service.get_active_membership(user.id, now_ts)
    if not membership:
        membership_payload = serialize_membership_for_response(None, reason="membership_missing")
        return MembershipCheckResponse(
            allowed=False,
            reason="membership_missing",
            membership=membership_payload,
            message=membership_payload.get("message") if membership_payload else None,
        )

    verdict = membership_service.can_consume_entry(membership, at_ts=now_ts)
    reason_for_payload = verdict.reason
    if direction == "exit" and verdict.reason == "daily_limit":
        # U výstupu ignorujeme denní limit – dovolíme odejít a nevracíme hlášku o limitu.
        verdict.allowed = True
        verdict.daily_limit_hit = False
        reason_for_payload = None
    membership_payload = serialize_membership_for_response(
        membership,
        reason=reason_for_payload,
        daily_limit_hit=verdict.daily_limit_hit,
    )
    if not verdict.allowed:
        return MembershipCheckResponse(
            allowed=False,
            reason=verdict.reason or "membership_denied",
            membership=membership_payload,
            message=membership_payload.get("message") if membership_payload else None,
        )

    presence_service = PresenceSessionService(db)
    active_session = presence_service.find_active_session(user.id)
    has_changes = False

    if direction == "entry":
        if record_usage:
            membership_service.record_entry_usage(membership, at_ts=now_ts)
            has_changes = True
        if not active_session:
            presence_service.start_session(
                user=user,
                token=token,
                membership=membership,
                access_log=None,
                scanned_at=now_ts,
                metadata={"source": "api_entry"},
            )
            has_changes = True
        set_presence(db, user, True, now_ts)
        has_changes = True
    elif direction == "exit":
        if active_session:
            presence_service.end_session(
                session=active_session,
                access_log=None,
                scanned_at=now_ts,
                status="closed",
                notes=None,
            )
            has_changes = True
        set_presence(db, user, False, now_ts)
        has_changes = True

    if has_changes:
        db.commit()

    return MembershipCheckResponse(
        allowed=True,
        reason="ok",
        membership=membership_payload,
        message=membership_payload.get("message") if membership_payload else None,
    )


@router.post("/verify/entry", response_model=MembershipCheckResponse)
async def verify_entry(
    verify_request: VerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Ověření pro vstup (odečítá denní limit/sessions při úspěchu).
    Requires X-API-KEY.
    """
    _require_api_key(request)
    return _membership_check(verify_request.token, db, record_usage=True, direction="entry")


@router.post("/verify/exit", response_model=MembershipCheckResponse)
async def verify_exit(
    verify_request: VerifyRequest,
    request: Request,
    db: Session = Depends(get_db),
):
    """
    Ověření pro odchod (neodečítá vstup, jen validuje).
    Requires X-API-KEY.
    """
    _require_api_key(request)
    return _membership_check(verify_request.token, db, record_usage=False, direction="exit")
@router.get("/access_logs")
async def get_access_logs(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get recent access logs (for admin/debugging purposes)"""
    try:
        logs = db.query(AccessLog).order_by(AccessLog.created_at.desc()).limit(limit).all()
        
        return [
            {
                "id": log.id,
                "token_string": log.token_string,
                "status": log.status,
                "reason": log.reason,
                "ip_address": log.ip_address,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]
    except Exception as e:
        logger.error(f"Error fetching access logs: {e}", exc_info=True)
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error fetching access logs"
        )
