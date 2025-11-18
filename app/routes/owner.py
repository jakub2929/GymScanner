import os
from pathlib import Path
from uuid import uuid4
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.auth import verify_password, create_access_token, get_current_owner
from app.database import get_db
from app.models import User, BrandingSettings
from app.services.owner import ensure_branding_defaults, OWNER_ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.branding import BrandingResponse, BrandingUpdateRequest

router = APIRouter(prefix="/owner", tags=["owner"])

MAX_LOGO_BYTES = int(os.getenv("BRANDING_LOGO_MAX_BYTES", 1_048_576))
UPLOAD_DIR = Path(os.getenv("BRANDING_UPLOAD_DIR", "static/branding"))
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
ALLOWED_CONTENT_TYPES = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/jpg": ".jpg",
    "image/svg+xml": ".svg",
}

def _get_branding(db: Session) -> BrandingSettings:
    branding = db.query(BrandingSettings).order_by(BrandingSettings.id).first()
    if branding:
        return branding
    ensure_branding_defaults()
    branding = db.query(BrandingSettings).order_by(BrandingSettings.id).first()
    if branding:
        return branding
    raise HTTPException(status_code=500, detail="Branding configuration missing")

def _serialize_branding(branding: BrandingSettings) -> BrandingResponse:
    return BrandingResponse(
        brand_name=branding.brand_name,
        console_name=branding.console_name,
        tagline=branding.tagline,
        support_email=branding.support_email,
        primary_color=branding.primary_color,
        footer_text=branding.footer_text,
        logo_url=branding.logo_url,
    )

def _delete_logo_file(logo_url: Optional[str]):
    if not logo_url:
        return
    if not logo_url.startswith("/static/branding/"):
        return
    filename = Path(logo_url).name
    file_path = UPLOAD_DIR / filename
    try:
        if file_path.exists():
            file_path.unlink()
    except Exception:
        # Silent failure - not critical
        pass

class OwnerLoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    owner_email: str
    owner_name: str
    role: str = "owner"

@router.post("/login", response_model=OwnerLoginResponse)
async def owner_login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    owner = db.query(User).filter(
        User.email == form_data.username,
        User.is_owner.is_(True)
    ).first()

    if not owner or not verify_password(form_data.password, owner.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid owner credentials")

    expires_minutes = OWNER_ACCESS_TOKEN_EXPIRE_MINUTES
    access_token = create_access_token({"sub": str(owner.id), "role": "owner"}, expires_minutes)

    return OwnerLoginResponse(
        access_token=access_token,
        owner_email=owner.email,
        owner_name=owner.name,
    )

@router.get("/me")
async def owner_me(current_owner: User = Depends(get_current_owner)):
    return {
        "id": current_owner.id,
        "email": current_owner.email,
        "name": current_owner.name,
        "role": "owner",
    }

@router.get("/branding", response_model=BrandingResponse)
async def get_branding(current_owner: User = Depends(get_current_owner), db: Session = Depends(get_db)):
    branding = _get_branding(db)
    return _serialize_branding(branding)

@router.put("/branding", response_model=BrandingResponse)
async def update_branding(
    request: BrandingUpdateRequest,
    current_owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    branding = _get_branding(db)
    old_logo = branding.logo_url

    branding.brand_name = request.brand_name
    branding.console_name = request.console_name
    branding.tagline = request.tagline
    branding.support_email = request.support_email
    branding.primary_color = request.primary_color
    branding.footer_text = request.footer_text
    branding.logo_url = request.logo_url or None
    branding.updated_by_owner_id = current_owner.id

    db.commit()
    db.refresh(branding)

    if old_logo and old_logo != branding.logo_url:
        _delete_logo_file(old_logo)

    return _serialize_branding(branding)

@router.post("/logo-upload", response_model=BrandingResponse)
async def upload_logo(
    file: UploadFile = File(...),
    current_owner: User = Depends(get_current_owner),
    db: Session = Depends(get_db),
):
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="Nepodporovaný formát. Povolené: PNG, JPG, SVG.")

    contents = await file.read()
    size = len(contents)
    if size > MAX_LOGO_BYTES:
        raise HTTPException(status_code=400, detail="Soubor je příliš velký (max 1 MB).")

    extension = ALLOWED_CONTENT_TYPES[file.content_type]
    filename = f"logo_{uuid4().hex}{extension}"
    upload_path = UPLOAD_DIR / filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    with open(upload_path, "wb") as buffer:
        buffer.write(contents)

    logo_url = f"/static/branding/{filename}"

    branding = _get_branding(db)
    old_logo = branding.logo_url
    branding.logo_url = logo_url
    branding.updated_by_owner_id = current_owner.id

    try:
        db.commit()
        db.refresh(branding)
    except Exception:
        db.rollback()
        if upload_path.exists():
            upload_path.unlink()
        raise

    if old_logo and old_logo != logo_url:
        _delete_logo_file(old_logo)

    return _serialize_branding(branding)
