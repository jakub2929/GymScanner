from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import AccessToken
import qrcode
import io
import base64

router = APIRouter()

def build_qr_image(token_str: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(token_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

@router.get("/tokens")
async def list_tokens(db: Session = Depends(get_db)):
    tokens = db.query(AccessToken).options(joinedload(AccessToken.user)).order_by(AccessToken.created_at.desc()).all()
    response = []
    for token in tokens:
        user = token.user
        response.append({
            "id": token.id,
            "token": token.token,
            "user_name": user.name if user else None,
            "user_email": user.email if user else None,
            "expires_at": token.expires_at.isoformat() if token.expires_at else None,
            "created_at": token.created_at.isoformat() if token.created_at else None,
            "used_at": token.used_at.isoformat() if token.used_at else None,
            "is_active": token.is_active,
            "scan_count": token.scan_count or 0,
            "qr_code_url": build_qr_image(token.token)
        })
    return response

@router.post("/tokens/{token_id}/activate")
async def activate_token(token_id: int, db: Session = Depends(get_db)):
    token = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.is_active = True
    db.commit()
    return {"status": "ok"}

@router.post("/tokens/{token_id}/deactivate")
async def deactivate_token(token_id: int, db: Session = Depends(get_db)):
    token = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.is_active = False
    db.commit()
    return {"status": "ok"}
