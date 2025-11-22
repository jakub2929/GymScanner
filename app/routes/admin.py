from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from pydantic import BaseModel
from app.database import get_db
from app.models import User, AccessToken
from app.services.presence import rebuild_presence_from_logs
from app.auth import get_current_user
import qrcode
import io
import base64

router = APIRouter()

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Require admin privileges"""
    # Handle SQLite boolean (0/1) vs Python bool
    is_admin = bool(current_user.is_admin) if current_user.is_admin is not None else False
    if not is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user

def build_qr_image(token_str: str) -> str:
    qr = qrcode.QRCode(version=1, box_size=6, border=2)
    qr.add_data(token_str)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    buffer.seek(0)
    return f"data:image/png;base64,{base64.b64encode(buffer.getvalue()).decode()}"

class UpdateCreditsRequest(BaseModel):
    credits: int
    note: str = ""

@router.get("/users/search")
async def search_users(
    q: str = Query(..., description="Search query (name or email)"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Search users by name or email"""
    search_term = f"%{q.lower()}%"
    users = db.query(User).filter(
        or_(
            User.name.ilike(search_term),
            User.email.ilike(search_term)
        )
    ).limit(50).all()
    
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "credits": user.credits or 0,
            "is_admin": user.is_admin or False,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]

@router.get("/users")
async def list_users(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all users"""
    users = db.query(User).order_by(User.created_at.desc()).limit(100).all()
    
    return [
        {
            "id": user.id,
            "name": user.name,
            "email": user.email,
            "credits": user.credits or 0,
            "is_admin": user.is_admin or False,
            "created_at": user.created_at.isoformat() if user.created_at else None
        }
        for user in users
    ]

@router.post("/users/{user_id}/credits")
async def update_user_credits(
    user_id: int,
    request: UpdateCreditsRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Add or remove credits from a user"""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    old_credits = user.credits or 0
    user.credits = max(0, old_credits + request.credits)  # Prevent negative credits
    db.commit()
    db.refresh(user)
    
    return {
        "user_id": user.id,
        "user_name": user.name,
        "user_email": user.email,
        "old_credits": old_credits,
        "credits_change": request.credits,
        "new_credits": user.credits,
        "note": request.note
    }

@router.get("/tokens")
async def list_tokens(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """List all access tokens"""
    tokens = db.query(AccessToken).join(User).order_by(AccessToken.created_at.desc()).limit(100).all()
    response = []
    for token in tokens:
        user = token.user
        response.append({
            "id": token.id,
            "token": token.token,
            "user_id": user.id if user else None,
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
async def activate_token(
    token_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Activate a token"""
    token = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.is_active = True
    db.commit()
    return {"status": "ok", "message": "Token activated"}

@router.post("/tokens/{token_id}/deactivate")
async def deactivate_token(
    token_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db)
):
    """Deactivate a token"""
    token = db.query(AccessToken).filter(AccessToken.id == token_id).first()
    if not token:
        raise HTTPException(status_code=404, detail="Token not found")
    token.is_active = False
    db.commit()
    return {"status": "ok", "message": "Token deactivated"}


@router.post("/users/{user_id}/rebuild-presence")
async def rebuild_presence(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Rebuild presence flag from latest AccessLog (admin fix-up)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    is_in = rebuild_presence_from_logs(db, user)
    db.commit()
    return {
        "user_id": user.id,
        "is_in_gym": is_in,
        "last_entry_at": user.last_entry_at.isoformat() if user.last_entry_at else None,
        "last_exit_at": user.last_exit_at.isoformat() if user.last_exit_at else None,
    }
