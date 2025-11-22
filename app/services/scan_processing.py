import logging
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.models import AccessLog, AccessToken, Membership, User
from app.routes.verify import VerifyResponse
from app.services.membership import get_active_membership
from app.services.timezone import day_bounds_utc, get_gym_timezone
from app.services.presence import set_presence

logger = logging.getLogger(__name__)


def mask_token(token: str) -> str:
    if not token:
        return ""
    return f"{token[:4]}..." if len(token) > 4 else token


class ScanResult:
    def __init__(self, response: VerifyResponse, allowed: bool):
        self.response = response
        self.allowed = allowed


def _trainer_allowed(user: User) -> bool:
    return bool(user.is_trainer)


def _get_membership_or_none(db: Session, user: User, scanned_at: datetime) -> Optional[Membership]:
    return get_active_membership(db, user.id, scanned_at)


def _daily_limit_hit(db: Session, user: User, scanned_at: datetime, membership: Membership, tz: ZoneInfo) -> bool:
    if not membership.daily_limit_enabled:
        return False
    start_utc, end_utc = day_bounds_utc(scanned_at, tz)
    existing_entry = (
        db.query(AccessLog)
        .filter(
            AccessLog.user_id == user.id,
            AccessLog.entry == True,
            AccessLog.allowed == True,
            AccessLog.scanned_at.isnot(None),
            AccessLog.scanned_at >= start_utc,
            AccessLog.scanned_at < end_utc,
        )
        .first()
    )
    return existing_entry is not None


def process_scan(
    db: Session,
    *,
    token_str: str,
    scanned_at: datetime,
    device_id: str,
    device_direction: str,
    client_ip: Optional[str],
    user_agent: Optional[str],
) -> VerifyResponse:
    """
    Process a scan and return a VerifyResponse-like payload.
    Always returns 200-compatible response; domain denies use allowed=False with reason.
    """
    processed_at = datetime.now(timezone.utc)
    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=timezone.utc)
    tz = get_gym_timezone()

    token = db.query(AccessToken).filter(AccessToken.token == token_str).first()
    if not token or not token.is_active:
        log = AccessLog(
            user_id=None,
            token_id=token.id if token else None,
            token_string=token_str,
            status="deny",
            reason="invalid_token" if token else "token_not_found",
            ip_address=client_ip,
            user_agent=user_agent,
            direction=device_direction,
            scanner_id=device_id,
            scanned_at=scanned_at,
            processed_at=processed_at,
            entry=device_direction == "in",
            exit=device_direction == "out",
            allowed=False,
            direction_from_device=device_direction,
            direction_from_state="entry" if device_direction == "in" else "exit",
            direction_mismatch=False,
            raw_token_masked=mask_token(token_str),
            metadata=None,
        )
        db.add(log)
        db.commit()
        return VerifyResponse(
            allowed=False,
            reason="invalid_token",
            credits_left=0,
            cooldown_seconds_left=None,
        )

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        log = AccessLog(
            user_id=None,
            token_id=token.id,
            token_string=token_str,
            status="deny",
            reason="user_not_found",
            ip_address=client_ip,
            user_agent=user_agent,
            direction=device_direction,
            scanner_id=device_id,
            scanned_at=scanned_at,
            processed_at=processed_at,
            entry=device_direction == "in",
            exit=device_direction == "out",
            allowed=False,
            direction_from_device=device_direction,
            direction_from_state="entry" if device_direction == "in" else "exit",
            direction_mismatch=False,
            raw_token_masked=mask_token(token_str),
            metadata=None,
        )
        db.add(log)
        db.commit()
        return VerifyResponse(
            allowed=False,
            reason="user_not_found",
            credits_left=0,
            cooldown_seconds_left=None,
        )

    is_trainer = _trainer_allowed(user)

    # Determine state-based direction
    is_entry = not bool(user.is_in_gym)
    is_exit = not is_entry
    expected_dir = "in" if is_entry else "out"
    direction_mismatch = device_direction != expected_dir
    direction_from_state = "entry" if is_entry else "exit"
    if direction_mismatch:
        logger.warning(
            "Direction mismatch for user %s (device=%s, state=%s)",
            user.id,
            device_direction,
            expected_dir,
        )

    # Membership / daily limit checks apply only to entry and non-trainers
    membership = None
    if is_entry and not is_trainer:
        membership = _get_membership_or_none(db, user, scanned_at)
        if not membership:
            return _log_and_response(
                db,
                user,
                token,
                token_str,
                device_id,
                device_direction,
                scanned_at,
                processed_at,
                is_entry,
                is_exit,
                direction_from_state,
                direction_mismatch,
                client_ip,
                user_agent,
                allowed=False,
                reason="membership_expired",
            )

        if _daily_limit_hit(db, user, scanned_at, membership, tz):
            return _log_and_response(
                db,
                user,
                token,
                token_str,
                device_id,
                device_direction,
                scanned_at,
                processed_at,
                is_entry,
                is_exit,
                direction_from_state,
                direction_mismatch,
                client_ip,
                user_agent,
                allowed=False,
                reason="daily_entry_limit_reached",
            )

    # Entry or exit allowed
    allowed = True

    # Update presence atomically
    try:
        set_presence(db, user, is_entry, scanned_at)
        response = _log_and_response(
            db,
            user,
            token,
            token_str,
            device_id,
            device_direction,
            scanned_at,
            processed_at,
            is_entry,
            is_exit,
            direction_from_state,
            direction_mismatch,
            client_ip,
            user_agent,
            allowed=allowed,
            reason="ok",
        )
        db.commit()
        return response
    except Exception as exc:
        logger.error("Error updating presence or logging scan: %s", exc, exc_info=True)
        db.rollback()
        return VerifyResponse(
            allowed=False,
            reason="invalid_token",
            credits_left=user.credits or 0,
            cooldown_seconds_left=None,
        )


def _log_and_response(
    db: Session,
    user: User,
    token: AccessToken,
    token_str: str,
    device_id: str,
    device_direction: str,
    scanned_at: datetime,
    processed_at: datetime,
    is_entry: bool,
    is_exit: bool,
    direction_from_state: str,
    direction_mismatch: bool,
    client_ip: Optional[str],
    user_agent: Optional[str],
    *,
    allowed: bool,
    reason: str,
) -> VerifyResponse:
    status = "allow" if allowed else "deny"
    log = AccessLog(
        user_id=user.id,
        token_id=token.id if token else None,
        token_string=token_str,
        status=status,
        reason=reason,
        ip_address=client_ip,
        user_agent=user_agent,
        direction=device_direction,
        scanner_id=device_id,
        scanned_at=scanned_at,
        processed_at=processed_at,
        entry=is_entry,
        exit=is_exit,
        allowed=allowed,
        direction_from_device=device_direction,
        direction_from_state=direction_from_state,
        direction_mismatch=direction_mismatch,
        raw_token_masked=mask_token(token_str),
        metadata=None,
    )
    db.add(log)

    # presence flag persistence is handled by caller to allow transaction control
    if not allowed:
        db.commit()

    return VerifyResponse(
        allowed=allowed,
        reason=reason,
        credits_left=user.credits or 0,
        cooldown_seconds_left=None,
        user_name=user.name,
        user_email=user.email,
    )
