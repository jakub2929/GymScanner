from fastapi import APIRouter, Depends, HTTPException, Request, status as http_status
from sqlalchemy.orm import Session
from sqlalchemy import and_
from pydantic import BaseModel
from app.database import get_db
from app.models import AccessToken, AccessLog, Payment, User
from datetime import datetime, timezone, timedelta
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# Cooldown duration in seconds
COOLDOWN_SECONDS = 60


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
            )
            return VerifyResponse(
                allowed=False,
                reason="no_credits",
                credits_left=0,
                cooldown_seconds_left=None,
            )

        if not token.is_valid(user_credits=user.credits):
            log_access(
                db,
                token_id=token.id,
                token_string=token_str,
                status="deny",
                reason="Token invalid or no credits",
                ip_address=client_ip,
                user_agent=user_agent,
                direction=direction,
                scanner_id=scanner_id,
                raw_data=raw_data,
            )
            return VerifyResponse(
                allowed=False,
                reason="invalid_token",
                credits_left=user.credits or 0,
                cooldown_seconds_left=None,
            )

        try:
            if user.credits is None or user.credits <= 0:
                db.rollback()
                return VerifyResponse(
                    allowed=False,
                    reason="no_credits",
                    credits_left=0,
                    cooldown_seconds_left=None,
                )

            user.credits = max(0, user.credits - 1)
            credits_after = user.credits

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
                reason=f"Access granted (credits remaining: {credits_after})",
                ip_address=client_ip,
                user_agent=user_agent,
                direction=direction,
                scanner_id=scanner_id,
                raw_data=raw_data,
                commit=False,
            )

            db.commit()
            return VerifyResponse(
                allowed=True,
                reason="ok",
                credits_left=credits_after,
                cooldown_seconds_left=COOLDOWN_SECONDS,
                user_name=user.name,
                user_email=user.email,
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
    token_str = verify_request.token
    return await process_verification(token_str, request, db, direction="in")

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
