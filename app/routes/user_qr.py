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
from app.services.membership import MembershipService, serialize_membership_for_response
from app.services.presence_sessions import PresenceSessionService, serialize_presence_session

router = APIRouter()

class MembershipSummary(BaseModel):
    has_membership: bool
    package_name: str | None = None
    package_type: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    status: str | None = None
    reason: str | None = None
    message: str | None = None


class MembershipDetail(BaseModel):
    membership_id: int
    package_name: str | None = None
    package_type: str | None = None
    membership_type: str | None = None
    status: str | None = None
    valid_from: str | None = None
    valid_to: str | None = None
    daily_limit: int | None = None
    daily_usage_count: int | None = None
    sessions_total: int | None = None
    sessions_used: int | None = None
    message: str | None = None


class PublicPackage(BaseModel):
    id: int
    name: str
    slug: str
    description: str | None = None
    price_czk: int
    duration_days: int
    daily_entry_limit: int | None = None
    session_limit: int | None = None
    package_type: str


class PersonalQRResponse(BaseModel):
    token: str
    qr_code_url: str
    user_name: str
    user_email: str
    credits: int
    membership: MembershipSummary | None = None
    memberships: list[MembershipDetail] = []
    packages: list[PublicPackage] = []
    presence_sessions: list[dict] | None = None


def _build_membership_context(db: Session, user_id: int):
    membership_service = MembershipService(db)
    now_ts = datetime.now(timezone.utc)
    active_membership = membership_service.get_active_membership(user_id, now_ts)
    membership_payload = serialize_membership_for_response(active_membership)
    membership_summary = None
    if membership_payload:
        membership_summary = MembershipSummary(
            has_membership=membership_payload.get("has_membership", False),
            package_name=membership_payload.get("package_name"),
            package_type=membership_payload.get("package_type"),
            valid_from=membership_payload.get("valid_from"),
            valid_to=membership_payload.get("valid_to"),
            status=membership_payload.get("status"),
            reason=membership_payload.get("reason"),
            message=membership_payload.get("message"),
        )

    membership_list: list[MembershipDetail] = []
    for membership in membership_service.list_user_memberships(user_id):
        payload = serialize_membership_for_response(membership)
        membership_list.append(
            MembershipDetail(
                membership_id=membership.id,
                package_name=payload.get("package_name") or membership.package_name_cache,
                package_type=payload.get("package_type") or membership.package.package_type if membership.package else None,
                membership_type=membership.membership_type,
                status=payload.get("status") or membership.status,
                valid_from=payload.get("valid_from"),
                valid_to=payload.get("valid_to"),
                daily_limit=payload.get("daily_limit"),
                daily_usage_count=payload.get("daily_usage_count"),
                sessions_total=payload.get("sessions_total"),
                sessions_used=payload.get("sessions_used"),
                message=payload.get("message"),
            )
        )

    packages = []
    for pkg in membership_service.list_packages(include_inactive=False):
        packages.append(
            PublicPackage(
                id=pkg.id,
                name=pkg.name,
                slug=pkg.slug,
                description=pkg.description,
                price_czk=pkg.price_czk,
                duration_days=pkg.duration_days,
                daily_entry_limit=pkg.daily_entry_limit,
                session_limit=pkg.session_limit,
                package_type=pkg.package_type,
            )
        )
    return membership_summary, membership_list, packages
def _list_presence_sessions(db: Session, user_id: int, limit: int = 20):
    service = PresenceSessionService(db)
    sessions = service.list_sessions(user_id=user_id, limit=limit)
    user = db.query(User).filter(User.id == user_id).first()
    return [serialize_presence_session(session, user) for session in sessions]

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
    
    membership_summary, membership_list, packages = _build_membership_context(db, current_user.id)
    presence_sessions = _list_presence_sessions(db, current_user.id, limit=50)

    return PersonalQRResponse(
        token=active_token.token,
        qr_code_url=qr_code_url,
        user_name=current_user.name,
        user_email=current_user.email,
        credits=current_user.credits or 0,
        membership=membership_summary,
        packages=packages,
        memberships=membership_list,
        presence_sessions=presence_sessions,
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
    
    membership_summary, membership_list, packages = _build_membership_context(db, current_user.id)
    presence_sessions = _list_presence_sessions(db, current_user.id, limit=50)
    
    return PersonalQRResponse(
        token=token_str,
        qr_code_url=qr_code_url,
        user_name=current_user.name,
        user_email=current_user.email,
        credits=current_user.credits or 0,
        membership=membership_summary,
        packages=packages,
        memberships=membership_list,
        presence_sessions=presence_sessions,
    )
