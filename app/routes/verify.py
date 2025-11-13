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
    
    # Get client IP and user agent for logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    
    try:
        # Find token in database
        token = db.query(AccessToken).filter(AccessToken.token == token_str).first()
        
        if not token:
            # Log failed attempt
            try:
                access_log = AccessLog(
                    token_string=token_str,
                    status="deny",
                    reason="Token not found",
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                db.add(access_log)
                db.commit()
            except Exception as e:
                logger.error(f"Error logging access attempt: {e}")
                db.rollback()
            
            return VerifyResponse(
                allowed=False,
                reason="token_not_found",
                credits_left=0,
                cooldown_seconds_left=None
            )
        
        if not token.is_active:
            try:
                access_log = AccessLog(
                    token_id=token.id,
                    token_string=token_str,
                    status="deny",
                    reason="Token deactivated",
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                db.add(access_log)
                db.commit()
            except Exception as e:
                logger.error(f"Error logging access attempt: {e}")
                db.rollback()
            
            return VerifyResponse(
                allowed=False,
                reason="token_deactivated",
                credits_left=0,
                cooldown_seconds_left=None
            )
        
        # Get user information
        user = db.query(User).filter(User.id == token.user_id).first()
        if not user:
            try:
                access_log = AccessLog(
                    token_string=token_str,
                    status="deny",
                    reason="User not found",
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                db.add(access_log)
                db.commit()
            except Exception as e:
                logger.error(f"Error logging access attempt: {e}")
                db.rollback()
            
            return VerifyResponse(
                allowed=False,
                reason="user_not_found",
                credits_left=0,
                cooldown_seconds_left=None
            )
        
        # Check cooldown on user level (all active tokens of same user)
        # Find the most recent last_scan_at among all active tokens of this user
        user_active_tokens = db.query(AccessToken).filter(
            and_(
                AccessToken.user_id == user.id,
                AccessToken.is_active == True,
                AccessToken.last_scan_at.isnot(None)
            )
        ).order_by(AccessToken.last_scan_at.desc()).first()
        
        cooldown_seconds_left = None
        if user_active_tokens and user_active_tokens.last_scan_at:
            # Ensure last_scan_at is timezone-aware (convert naive to aware if needed)
            last_scan_time = user_active_tokens.last_scan_at
            if last_scan_time.tzinfo is None:
                # Naive datetime - assume UTC
                last_scan_time = last_scan_time.replace(tzinfo=timezone.utc)
            
            now = datetime.now(timezone.utc)
            time_since_last_scan = now - last_scan_time
            if time_since_last_scan.total_seconds() < COOLDOWN_SECONDS:
                cooldown_seconds_left = int(COOLDOWN_SECONDS - time_since_last_scan.total_seconds())
                
                # Log cooldown deny
                try:
                    access_log = AccessLog(
                        token_id=token.id,
                        token_string=token_str,
                        status="deny",
                        reason=f"Cooldown active ({cooldown_seconds_left}s remaining)",
                        ip_address=client_ip,
                        user_agent=user_agent
                    )
                    db.add(access_log)
                    db.commit()
                except Exception as e:
                    logger.error(f"Error logging access attempt: {e}")
                    db.rollback()
                
                return VerifyResponse(
                    allowed=False,
                    reason="cooldown",
                    credits_left=user.credits or 0,
                    cooldown_seconds_left=cooldown_seconds_left
                )
        
        # Check if user has credits (credit system: 1 credit = 1 workout)
        if user.credits is None or user.credits <= 0:
            try:
                access_log = AccessLog(
                    token_id=token.id,
                    token_string=token_str,
                    status="deny",
                    reason="No credits available",
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                db.add(access_log)
                db.commit()
            except Exception as e:
                logger.error(f"Error logging access attempt: {e}")
                db.rollback()
            
            return VerifyResponse(
                allowed=False,
                reason="no_credits",
                credits_left=0,
                cooldown_seconds_left=None
            )
        
        # Check if token is valid (active and user has credits)
        if not token.is_valid(user_credits=user.credits):
            try:
                access_log = AccessLog(
                    token_id=token.id,
                    token_string=token_str,
                    status="deny",
                    reason="Token invalid or no credits",
                    ip_address=client_ip,
                    user_agent=user_agent
                )
                db.add(access_log)
                db.commit()
            except Exception as e:
                logger.error(f"Error logging access attempt: {e}")
                db.rollback()
            
            return VerifyResponse(
                allowed=False,
                reason="invalid_token",
                credits_left=user.credits or 0,
                cooldown_seconds_left=None
            )
        
        # Token is valid, user has credits, and cooldown has passed
        # Use transaction for atomic operations
        try:
            # Deduct credit (1 credit = 1 workout)
            # Double-check credits before deducting (should not happen, but safety check)
            if user.credits is None or user.credits <= 0:
                db.rollback()
                return VerifyResponse(
                    allowed=False,
                    reason="no_credits",
                    credits_left=0,
                    cooldown_seconds_left=None
                )
            
            # Deduct credit (ensures it never goes below 0)
            user.credits = max(0, user.credits - 1)
            credits_after = user.credits
            
            # Update token tracking
            now = datetime.now(timezone.utc)
            token.used_at = now
            token.scan_count = (token.scan_count or 0) + 1
            
            # Set last_scan_at for THIS token (will be used for cooldown check)
            token.last_scan_at = now
            
            # Also update last_scan_at for ALL active tokens of this user (cooldown is user-level)
            db.query(AccessToken).filter(
                and_(
                    AccessToken.user_id == user.id,
                    AccessToken.is_active == True
                )
            ).update({"last_scan_at": now}, synchronize_session=False)
            
            # Log successful access
            access_log = AccessLog(
                token_id=token.id,
                token_string=token_str,
                status="allow",
                reason=f"Access granted (credits remaining: {credits_after})",
                ip_address=client_ip,
                user_agent=user_agent
            )
            db.add(access_log)
            
            # Commit all changes atomically
            db.commit()
            
            return VerifyResponse(
                allowed=True,
                reason="ok",
                credits_left=credits_after,
                cooldown_seconds_left=COOLDOWN_SECONDS,  # Cooldown just started
                user_name=user.name,
                user_email=user.email
            )
            
        except Exception as e:
            logger.error(f"Error processing access grant: {e}", exc_info=True)
            db.rollback()
            # Return error response but don't raise HTTPException (it's not a 500 case)
            return VerifyResponse(
                allowed=False,
                reason="invalid_token",
                credits_left=user.credits or 0,
                cooldown_seconds_left=None
            )
            
    except Exception as e:
        logger.error(f"Unexpected error in verify_token: {e}", exc_info=True)
        db.rollback()
        # This is a real server error - return 500
        raise HTTPException(
            status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )

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
