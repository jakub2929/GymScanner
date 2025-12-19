from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import BrandingSettings
from app.schemas.branding import BrandingResponse
from app.services.owner import ensure_branding_defaults, DEFAULT_BRANDING

router = APIRouter()

def _serialize(branding: BrandingSettings | None) -> BrandingResponse:
    if branding:
        return BrandingResponse(
            brand_name=branding.brand_name,
            console_name=branding.console_name,
            tagline=branding.tagline,
            support_email=branding.support_email,
            primary_color=branding.primary_color,
            footer_text=branding.footer_text,
            logo_url=branding.logo_url,
            reservations_enabled=bool(branding.reservations_enabled),
        )
    return BrandingResponse(
        brand_name=DEFAULT_BRANDING["brand_name"],
        console_name=DEFAULT_BRANDING["console_name"],
        tagline=DEFAULT_BRANDING["tagline"],
        support_email=DEFAULT_BRANDING["support_email"],
        primary_color=DEFAULT_BRANDING["primary_color"],
        footer_text=DEFAULT_BRANDING["footer_text"],
        logo_url=DEFAULT_BRANDING["logo_url"],
        reservations_enabled=DEFAULT_BRANDING["reservations_enabled"],
    )

@router.get("/branding", response_model=BrandingResponse)
async def public_branding(db: Session = Depends(get_db)):
    branding = db.query(BrandingSettings).order_by(BrandingSettings.id).first()
    if not branding:
        ensure_branding_defaults()
        branding = db.query(BrandingSettings).order_by(BrandingSettings.id).first()
    return _serialize(branding)
