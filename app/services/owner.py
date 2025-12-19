import logging
import os
from contextlib import contextmanager
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import User, BrandingSettings
from app.auth import get_password_hash

logger = logging.getLogger(__name__)

DEFAULT_BRANDING = {
    "brand_name": os.getenv("BRANDING_DEFAULT_BRAND_NAME", "Gym Access"),
    "console_name": os.getenv("BRANDING_DEFAULT_CONSOLE_NAME", "Control Console"),
    "tagline": os.getenv("BRANDING_DEFAULT_TAGLINE", "Smart access management"),
    "support_email": os.getenv("BRANDING_DEFAULT_SUPPORT_EMAIL", "support@example.com"),
    "primary_color": os.getenv("BRANDING_DEFAULT_PRIMARY_COLOR", "#0EA5E9"),
    "footer_text": os.getenv("BRANDING_DEFAULT_FOOTER_TEXT", "© 2025 GymScanner"),
    "logo_url": os.getenv("BRANDING_DEFAULT_LOGO_URL"),
    "reservations_enabled": False,
}

OWNER_ACCESS_TOKEN_EXPIRE_MINUTES = int(
    os.getenv("OWNER_ACCESS_TOKEN_EXPIRE_MINUTES", os.getenv("JWT_ACCESS_TOKEN_EXPIRE_MINUTES", "60"))
)

@contextmanager
def session_scope():
    session: Session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def ensure_owner_account():
    """Create owner account if none exists and ENV variables are provided."""
    owner_email = os.getenv("OWNER_EMAIL")
    owner_password = os.getenv("OWNER_PASSWORD")
    owner_name = os.getenv("OWNER_NAME", "Platform Owner")

    if not owner_email or not owner_password:
        logger.warning("OWNER_EMAIL / OWNER_PASSWORD are not set; owner account will not be auto-created.")
        return

    with session_scope() as db:
        existing_owner = db.query(User).filter(User.is_owner.is_(True)).first()
        if existing_owner:
            logger.info("Owner account already present (email=%s)", existing_owner.email)
            return

        normalized_email = owner_email.strip().lower()
        conflicting_user = db.query(User).filter(User.email == normalized_email).first()
        if conflicting_user:
            # Promote existing user to owner if needed
            conflicting_user.is_owner = True
            conflicting_user.is_admin = True
            conflicting_user.password_hash = get_password_hash(owner_password)
            db.commit()
            logger.info("Existing user %s promoted to owner.", normalized_email)
            return

        new_owner = User(
            email=normalized_email,
            name=owner_name,
            password_hash=get_password_hash(owner_password),
            is_owner=True,
            is_admin=True,
            credits=0,
        )
        db.add(new_owner)
        db.commit()
        logger.info("Owner account created with email %s", normalized_email)

def ensure_branding_defaults():
    """Ensure at least one branding configuration exists with defaults."""
    with session_scope() as db:
        branding = db.query(BrandingSettings).order_by(BrandingSettings.id).first()
        if branding:
            return branding

        branding = BrandingSettings(**DEFAULT_BRANDING)
        db.add(branding)
        db.commit()
        logger.info("Default branding settings created.")
        return branding
