from datetime import datetime
import base64
import io
import qrcode
import re

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import or_
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, root_validator

from app.auth import get_current_user, get_optional_user
from app.database import get_db
from app.models import AccessToken, Membership, MembershipPackage, AccessLog, User, PresenceSession, APIKey
from app.services.api_keys import create_api_key, serialize_api_key, verify_api_key
from app.services.membership import MembershipService
from app.services.presence_sessions import PresenceSessionService, serialize_presence_session
from app.services.presence import rebuild_presence_from_logs, set_presence

router = APIRouter()

def require_admin(
    request: Request,
    db: Session = Depends(get_db),
    optional_user: User | None = Depends(get_optional_user),
) -> User:
    """
    Allow admin access via JWT or active API key (X-API-KEY).
    Returns the resolved user (creator of the key if available) or a proxy admin user.
    """
    api_key_raw = request.headers.get("X-API-KEY") or request.headers.get("x-api-key")
    if api_key_raw:
        api_key_obj = verify_api_key(db, api_key_raw.strip())
        if api_key_obj:
            if api_key_obj.created_by_user_id:
                creator = db.query(User).filter(User.id == api_key_obj.created_by_user_id).first()
                if creator:
                    return creator
            proxy = User()
            proxy.id = api_key_obj.created_by_user_id
            proxy.is_admin = True
            proxy.email = "api-key"
            proxy.name = api_key_obj.name
            return proxy

    if optional_user:
        is_admin = bool(optional_user.is_admin) if optional_user.is_admin is not None else False
        if not is_admin:
            raise HTTPException(status_code=403, detail="Admin access required")
        return optional_user

    raise HTTPException(status_code=401, detail="Unauthorized")

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


class MembershipPackagePayload(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)
    slug: str = Field(..., min_length=3, max_length=120, pattern=r"^[a-z0-9\-_]+$")
    price_czk: int = Field(..., ge=0)
    duration_days: int = Field(..., ge=1)
    package_type: str = Field(default="membership", min_length=3, max_length=50)
    daily_entry_limit: int | None = Field(default=None, ge=1)
    session_limit: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None


class MembershipPackageUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=3, max_length=120)
    slug: str | None = Field(default=None, min_length=3, max_length=120, pattern=r"^[a-z0-9\-_]+$")
    price_czk: int | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, ge=1)
    package_type: str | None = Field(default=None, min_length=3, max_length=50)
    daily_entry_limit: int | None = Field(default=None, ge=1)
    session_limit: int | None = Field(default=None, ge=1)
    description: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None
    is_active: bool | None = None


class TogglePackageRequest(BaseModel):
    is_active: bool

class EndPresenceSessionRequest(BaseModel):
    status: str = Field(default="closed", max_length=40)
    note: str | None = Field(default=None, max_length=500)


class AssignMembershipRequest(BaseModel):
    package_id: int | None = None
    package_slug: str | None = None
    custom_name: str | None = Field(default=None, min_length=3, max_length=120)
    membership_type: str | None = Field(default="membership", min_length=3, max_length=50)
    price_czk: int | None = Field(default=None, ge=0)
    duration_days: int | None = Field(default=None, ge=1)
    start_at: datetime | None = None
    daily_limit: int | None = Field(default=None, ge=1)
    session_limit: int | None = Field(default=None, ge=1)
    notes: str | None = Field(default=None, max_length=500)
    metadata: dict | None = None
    auto_renew: bool = False

    @root_validator(skip_on_failure=True)
    def validate_payload(cls, values):
        package_id = values.get("package_id")
        package_slug = values.get("package_slug")
        if not package_id and not package_slug:
            # manual assignment requires core details
            if not values.get("custom_name"):
                raise ValueError("custom_name is required when package_id is not provided")
            if not values.get("duration_days"):
                raise ValueError("duration_days is required when package_id is not provided")
        return values


class UpdateMembershipStatusRequest(BaseModel):
    status: str = Field(..., pattern=r"^(active|paused|cancelled|expired|grace)$")
    note: str | None = Field(default=None, max_length=500)


class ConsumeSessionsRequest(BaseModel):
    count: int = Field(1, ge=1, le=10)
    note: str | None = Field(default=None, max_length=500)

class APIKeyCreateRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=120)


class APIKeyResponse(BaseModel):
    id: int
    name: str
    prefix: str
    is_active: bool
    created_at: str | None = None
    last_used_at: str | None = None
    created_by_user_id: int | None = None
    token: str | None = None  # only populated on create


def _slugify(value: str) -> str:
    slug = value.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return slug or "package"


def serialize_package(package: MembershipPackage) -> dict:
    return {
        "id": package.id,
        "name": package.name,
        "slug": package.slug,
        "description": package.description,
        "price_czk": package.price_czk,
        "duration_days": package.duration_days,
        "daily_entry_limit": package.daily_entry_limit,
        "session_limit": package.session_limit,
        "package_type": package.package_type,
        "is_active": package.is_active,
        "metadata": package.metadata_json,
        "created_at": package.created_at.isoformat() if package.created_at else None,
        "updated_at": package.updated_at.isoformat() if package.updated_at else None,
    }


def serialize_membership(membership: Membership) -> dict:
    return {
        "id": membership.id,
        "user_id": membership.user_id,
        "package_id": membership.package_id,
        "package_name": membership.package_name_cache,
        "membership_type": membership.membership_type,
        "status": membership.status,
        "price_czk": membership.price_czk,
        "valid_from": membership.valid_from.isoformat() if membership.valid_from else None,
        "valid_to": membership.valid_to.isoformat() if membership.valid_to else None,
        "daily_limit_enabled": membership.daily_limit_enabled,
        "daily_limit": membership.daily_limit,
        "daily_usage_count": membership.daily_usage_count,
        "sessions_total": membership.sessions_total,
        "sessions_used": membership.sessions_used,
        "auto_renew": membership.auto_renew,
        "notes": membership.notes,
        "metadata": membership.metadata_json,
        "last_usage_at": membership.last_usage_at.isoformat() if membership.last_usage_at else None,
        "created_at": membership.created_at.isoformat() if membership.created_at else None,
    }

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
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_entry_at": user.last_entry_at.isoformat() if user.last_entry_at else None,
            "last_exit_at": user.last_exit_at.isoformat() if user.last_exit_at else None,
            "is_in_gym": bool(user.is_in_gym),
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
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "last_entry_at": user.last_entry_at.isoformat() if user.last_entry_at else None,
            "last_exit_at": user.last_exit_at.isoformat() if user.last_exit_at else None,
            "is_in_gym": bool(user.is_in_gym),
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


@router.get("/membership-packages")
async def list_membership_packages(
    include_inactive: bool = Query(False, description="Include inactive packages"),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = MembershipService(db)
    packages = service.list_packages(include_inactive=include_inactive)
    return [serialize_package(pkg) for pkg in packages]


@router.post("/membership-packages")
async def create_membership_package(
    payload: MembershipPackagePayload,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = MembershipService(db)
    existing = service.get_package_by_slug(payload.slug)
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists.")
    package = service.create_package(
        name=payload.name,
        slug=payload.slug or _slugify(payload.name),
        price_czk=payload.price_czk,
        duration_days=payload.duration_days,
        package_type=payload.package_type,
        daily_entry_limit=payload.daily_entry_limit,
        session_limit=payload.session_limit,
        description=payload.description,
        metadata=payload.metadata,
        created_by_admin_id=current_user.id,
    )
    db.commit()
    db.refresh(package)
    return serialize_package(package)


@router.put("/membership-packages/{package_id}")
async def update_membership_package(
    package_id: int,
    payload: MembershipPackageUpdateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = MembershipService(db)
    package = service.get_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    if payload.slug and payload.slug != package.slug:
        conflict = service.get_package_by_slug(payload.slug)
        if conflict and conflict.id != package.id:
            raise HTTPException(status_code=400, detail="Slug already in use")
    service.update_package(
        package,
        name=payload.name,
        slug=payload.slug,
        price_czk=payload.price_czk,
        duration_days=payload.duration_days,
        package_type=payload.package_type,
        daily_entry_limit=payload.daily_entry_limit,
        session_limit=payload.session_limit,
        description=payload.description,
        metadata=payload.metadata,
        is_active=payload.is_active,
    )
    db.commit()
    db.refresh(package)
    return serialize_package(package)


@router.post("/membership-packages/{package_id}/toggle")
async def toggle_membership_package(
    package_id: int,
    payload: TogglePackageRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = MembershipService(db)
    package = service.get_package(package_id)
    if not package:
        raise HTTPException(status_code=404, detail="Package not found")
    service.set_package_active(package, payload.is_active)
    db.commit()
    db.refresh(package)
    return serialize_package(package)


@router.get("/users/{user_id}/memberships")
async def list_user_memberships(
    user_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    service = MembershipService(db)
    memberships = service.list_user_memberships(user_id)
    return [serialize_membership(m) for m in memberships]


@router.post("/users/{user_id}/memberships")
async def assign_membership_to_user(
    user_id: int,
    payload: AssignMembershipRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    service = MembershipService(db)
    membership: Membership
    if payload.package_id or payload.package_slug:
        package = None
        if payload.package_id:
            package = service.get_package(payload.package_id)
        elif payload.package_slug:
            package = service.get_package_by_slug(payload.package_slug)
        if not package:
            raise HTTPException(status_code=404, detail="Package not found")
        membership = service.assign_package_to_user(
            user_id=user_id,
            package=package,
            start_at=payload.start_at,
            created_by_admin_id=current_user.id,
            notes=payload.notes,
            auto_renew=payload.auto_renew,
        )
    else:
        membership = service.create_manual_membership(
            user_id=user_id,
            name=payload.custom_name or "Manuální permanentka",
            membership_type=payload.membership_type or "manual",
            price_czk=payload.price_czk,
            duration_days=payload.duration_days or 30,
            start_at=payload.start_at,
            daily_limit=payload.daily_limit,
            session_limit=payload.session_limit,
            notes=payload.notes,
            metadata=payload.metadata,
            created_by_admin_id=current_user.id,
            auto_renew=payload.auto_renew,
        )
    db.commit()
    db.refresh(membership)
    return serialize_membership(membership)


@router.post("/users/{user_id}/memberships/{membership_id}/status")
async def update_membership_status(
    user_id: int,
    membership_id: int,
    payload: UpdateMembershipStatusRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(Membership).filter(Membership.id == membership_id, Membership.user_id == user_id).first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    membership.status = payload.status
    if payload.note:
        membership.notes = (membership.notes or "") + f"\n[{datetime.now().isoformat()}] {payload.note}"
    db.commit()
    db.refresh(membership)
    return serialize_membership(membership)


@router.post("/users/{user_id}/memberships/{membership_id}/sessions/consume")
async def consume_membership_sessions(
    user_id: int,
    membership_id: int,
    payload: ConsumeSessionsRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    membership = (
        db.query(Membership).filter(Membership.id == membership_id, Membership.user_id == user_id).first()
    )
    if not membership:
        raise HTTPException(status_code=404, detail="Membership not found")
    service = MembershipService(db)
    try:
        service.consume_sessions(membership, count=payload.count, note=payload.note)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    db.commit()
    db.refresh(membership)
    return serialize_membership(membership)

@router.get("/api-keys", response_model=list[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """List API keys without exposing secrets."""
    keys = db.query(APIKey).order_by(APIKey.created_at.desc()).all()
    return [APIKeyResponse(**serialize_api_key(key)) for key in keys]


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    payload: APIKeyCreateRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Create a new API key and return the secret once."""
    api_key, raw_key = create_api_key(
        db,
        name=payload.name,
        created_by_user_id=current_user.id if current_user else None,
    )
    data = serialize_api_key(api_key)
    data["token"] = raw_key
    return APIKeyResponse(**data)


@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = False
    db.commit()
    return {"status": "ok", "message": "API key revoked"}


@router.delete("/api-keys/{key_id}")
async def delete_api_key(
    key_id: int,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    key = db.query(APIKey).filter(APIKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(key)
    db.commit()
    return {"status": "ok", "message": "API key deleted"}

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


@router.get("/scan-logs")
async def list_scan_logs(
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    logs = (
        db.query(AccessLog)
        .order_by(AccessLog.created_at.desc())
        .limit(limit)
        .all()
    )
    results = []
    for log in logs:
        results.append(
            {
                "id": log.id,
                "user_id": log.user_id,
                "user_name": log.user.name if log.user else None,
                "reason": log.reason,
                "status": log.status,
                "allowed": log.allowed,
                "created_at": log.created_at.isoformat() if log.created_at else None,
                "metadata": log.metadata_json,
            }
        )
    return results

@router.get("/presence/active")
async def list_active_presence(
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = PresenceSessionService(db)
    sessions = service.list_active_sessions()
    user_map = {u.id: u for u in db.query(User).filter(User.id.in_([s.user_id for s in sessions])).all()}
    return [serialize_presence_session(session, user_map.get(session.user_id)) for session in sessions]


@router.get("/presence/sessions")
async def list_presence_sessions(
    user_id: int | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = PresenceSessionService(db)
    sessions = service.list_sessions(user_id=user_id, limit=limit)
    user_ids = [s.user_id for s in sessions]
    user_map = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}
    return [serialize_presence_session(session, user_map.get(session.user_id)) for session in sessions]


@router.post("/presence/{session_id}/end")
async def end_presence_session(
    session_id: int,
    payload: EndPresenceSessionRequest,
    current_user: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    service = PresenceSessionService(db)
    session = db.query(PresenceSession).filter(PresenceSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    service.force_close(session, status=payload.status, notes=payload.note)
    user = db.query(User).filter(User.id == session.user_id).first()
    # Update user presence flag and last_exit timestamp
    if user:
        set_presence(db, user, False, session.ended_at or datetime.utcnow())
    db.commit()
    db.refresh(session)
    return serialize_presence_session(session, user)

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
