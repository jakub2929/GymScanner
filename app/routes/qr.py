from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models import Payment, AccessToken
import qrcode
import io
import uuid
from datetime import datetime, timedelta, timezone

router = APIRouter()

class QRRequest(BaseModel):
    payment_id: str
    expires_in_days: int = 1  # Default 1 day, can be customized

class QRResponse(BaseModel):
    token: str
    qr_code_url: str
    expires_at: str

@router.post("/generate_qr", response_model=QRResponse)
async def generate_qr(
    qr_request: QRRequest,
    db: Session = Depends(get_db)
):
    """
    Generate a QR code token for gym access.
    Requires a valid completed payment.
    Token can be used multiple times within the validity period (days).
    """
    # Verify payment exists and is completed
    payment = db.query(Payment).filter(Payment.payment_id == qr_request.payment_id).first()
    if not payment:
        raise HTTPException(status_code=404, detail="Payment not found")
    
    if payment.status != "completed":
        raise HTTPException(
            status_code=400,
            detail=f"Payment not completed. Current status: {payment.status}"
        )
    
    # Get expiration in days from request (default 1 day)
    expires_in_days = getattr(qr_request, 'expires_in_days', 1) or 1
    expires_at = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
    
    # Always generate a new token for each QR code generation
    # This ensures fresh token with correct expiration
    token_str = str(uuid.uuid4())
    
    access_token = AccessToken(
        token=token_str,
        user_id=payment.user_id,
        payment_id=payment.id,
        expires_at=expires_at,
        is_active=True,
        scan_count=0
    )
    db.add(access_token)
    db.commit()
    
    # Generate QR code
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(token_str)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    
    # Convert to data URL for frontend display
    import base64
    img_base64 = base64.b64encode(img_buffer.getvalue()).decode()
    qr_code_url = f"data:image/png;base64,{img_base64}"
    
    return QRResponse(
        token=token_str,
        qr_code_url=qr_code_url,
        expires_at=expires_at.isoformat()
    )

@router.get("/qr_image/{token}")
async def get_qr_image(token: str):
    """Get QR code as PNG image"""
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img_buffer = io.BytesIO()
    img.save(img_buffer, format="PNG")
    img_buffer.seek(0)
    
    return Response(content=img_buffer.getvalue(), media_type="image/png")

