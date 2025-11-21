from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import AccessToken, User
from app.auth import get_current_user
import qrcode
import io
from datetime import datetime, timedelta, timezone
from app.services.token_service import generate_unique_token

router = APIRouter()

class PersonalQRResponse(BaseModel):
    token: str
    qr_code_url: str
    user_name: str
    user_email: str
    credits: int

@router.get("/my_qr", response_model=PersonalQRResponse)
async def get_my_qr(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get or generate personal QR code for the authenticated user.
    Credit system: 1 credit = 1 workout, no expiration.
    """
    # Find the most recent active token for this user
    active_token = db.query(AccessToken).filter(
        AccessToken.user_id == current_user.id,
        AccessToken.is_active == True
    ).order_by(AccessToken.created_at.desc()).first()
    
    # If no active token exists, create a new one
    if not active_token:
        token_str = generate_unique_token(db)
        
        access_token = AccessToken(
            token=token_str,
            user_id=current_user.id,
            payment_id=None,
            expires_at=None,  # No expiration in credit system
            is_active=True,
            scan_count=0
        )
        db.add(access_token)
        try:
            db.commit()
            db.refresh(access_token)
            active_token = access_token
        except Exception as e:
            db.rollback()
            # If payment_id is NOT NULL, try to fix the database
            if "NOT NULL constraint failed: access_tokens.payment_id" in str(e):
                from app.database import ensure_access_token_nullable_columns
                ensure_access_token_nullable_columns()
                # Try again
                db.add(access_token)
                db.commit()
                db.refresh(access_token)
                active_token = access_token
            else:
                raise
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(active_token.token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    
    # Convert to data URL for frontend display
    import base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{img_base64}"
    
    return PersonalQRResponse(
        token=active_token.token,
        qr_code_url=qr_code_url,
        user_name=current_user.name,
        user_email=current_user.email,
        credits=current_user.credits or 0
    )

@router.post("/regenerate_qr", response_model=PersonalQRResponse)
async def regenerate_qr(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate a new QR code token for the authenticated user.
    Deactivates old tokens and creates a fresh one.
    Credit system: no expiration.
    """
    # Deactivate all existing tokens for this user
    db.query(AccessToken).filter(
        AccessToken.user_id == current_user.id,
        AccessToken.is_active == True
    ).update({"is_active": False})
    
    # Create new token
    token_str = generate_unique_token(db)
    
    access_token = AccessToken(
        token=token_str,
        user_id=current_user.id,
        payment_id=None,
        expires_at=None,  # No expiration in credit system
        is_active=True,
        scan_count=0
    )
    db.add(access_token)
    db.commit()
    db.refresh(access_token)
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(token_str)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    
    # Convert to data URL
    import base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{img_base64}"
    
    return PersonalQRResponse(
        token=token_str,
        qr_code_url=qr_code_url,
        user_name=current_user.name,
        user_email=current_user.email,
        credits=current_user.credits or 0
    )
