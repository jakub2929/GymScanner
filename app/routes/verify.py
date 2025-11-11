from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import AccessToken, AccessLog, Payment, User
from datetime import datetime, timezone

router = APIRouter()

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
    status: str  # "allow" or "deny"
    reason: str
    user_name: str = None
    user_email: str = None
    expires_at: str = None

@router.post("/verify", response_model=VerifyResponse)
async def verify_token(
    verify_request: VerifyRequest,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    Verify a QR code token for turnstile access.
    Returns 'allow' or 'deny' with a reason.
    Logs all access attempts for audit purposes.
    """
    token_str = verify_request.token
    
    # Get client IP and user agent for logging
    client_ip = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent", None)
    
    # Find token in database
    token = db.query(AccessToken).filter(AccessToken.token == token_str).first()
    
    if not token:
        # Log failed attempt
        access_log = AccessLog(
            token_string=token_str,
            status="deny",
            reason="Token not found",
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(access_log)
        db.commit()
        
        return VerifyResponse(
            status="deny",
            reason="Token not found"
        )
    
    if not token.is_active:
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
        return VerifyResponse(status="deny", reason="Token deactivated")
    
    # Check if token is valid (only check expiration, not usage)
    if not token.is_valid():
        now = datetime.now(timezone.utc)
        # Ensure expires_at is timezone-aware for comparison
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        reason = "Token expired"
        
        # Log failed attempt
        access_log = AccessLog(
            token_id=token.id,
            token_string=token_str,
            status="deny",
            reason=reason,
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(access_log)
        db.commit()
        
        return VerifyResponse(
            status="deny",
            reason=reason
        )
    
    # Verify payment is still valid
    payment = db.query(Payment).filter(Payment.id == token.payment_id).first()
    if not payment or payment.status != "completed":
        # Log failed attempt
        access_log = AccessLog(
            token_id=token.id,
            token_string=token_str,
            status="deny",
            reason="Payment not valid",
            ip_address=client_ip,
            user_agent=user_agent
        )
        db.add(access_log)
        db.commit()
        
        return VerifyResponse(
            status="deny",
            reason="Payment not valid"
        )
    
    # Token is valid - allow access (don't mark as used, allow multiple scans)
    # Only update used_at for logging purposes, but don't set is_used = True
    # This allows the token to be used multiple times within validity period
    
    # Get user information
    user = db.query(User).filter(User.id == token.user_id).first()
    
    # Log successful access
    access_log = AccessLog(
        token_id=token.id,
        token_string=token_str,
        status="allow",
        reason="Token valid and payment confirmed",
        ip_address=client_ip,
        user_agent=user_agent
    )
    db.add(access_log)
    
    # Update used_at timestamp for tracking, but keep token usable
    token.used_at = datetime.now(timezone.utc)
    token.scan_count = (token.scan_count or 0) + 1
    db.commit()
    
    # Format expires_at for response
    expires_at_str = None
    if token.expires_at:
        expires_at = token.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        expires_at_str = expires_at.isoformat()
    
    return VerifyResponse(
        status="allow",
        reason="Access granted",
        user_name=user.name if user else None,
        user_email=user.email if user else None,
        expires_at=expires_at_str
    )

@router.get("/access_logs")
async def get_access_logs(
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get recent access logs (for admin/debugging purposes)"""
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

