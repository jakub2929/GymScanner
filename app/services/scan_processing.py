import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AccessLog, AccessToken, Membership, User
from app.routes.verify import VerifyResponse
from app.services.membership import get_active_membership
from app.services.presence import set_presence
from app.services.timezone import day_bounds_utc, get_gym_timezone
from app.services.utils import mask_token

logger = logging.getLogger(__name__)


def _get_trainer_flag(user: User) -> bool:
    return bool(getattr(user, "is_trainer", False))


def _direction_from_state(is_entry: bool) -> str:
    return "entry" if is_entry else "exit"


def _device_direction_to_entry_exit(device_direction: str) -> tuple[bool, bool]:
    if device_direction == "in":
        return True, False
    if device_direction == "out":
        return False, True
    return False, False


def _log_and_response(
    db: Session,
    *,
    user: Optional[User],
    token: Optional[AccessToken],
    token_str: str,
    device_id: str,
    device_direction: str,
    scanned_at: datetime,
    processed_at: datetime,
    entry: bool,
    exit: bool,
    direction_from_state: str,
    direction_mismatch: bool,
    client_ip: Optional[str],
    user_agent: Optional[str],
    allowed: bool,
    reason: str,
) -> VerifyResponse:
    status = "allow" if allowed else "deny"
    log = AccessLog(
        user_id=user.id if user else None,
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
        entry=entry,
        exit=exit,
        allowed=allowed,
        direction_from_device=device_direction,
        direction_from_state=direction_from_state,
        direction_mismatch=direction_mismatch,
        raw_token_masked=mask_token(token_str),
        metadata=None,
    )
    db.add(log)
    if not allowed:
        db.commit()

    credits_left = user.credits if user and user.credits is not None else 0
    return VerifyResponse(
        allowed=allowed,
        reason=reason,
        credits_left=credits_left,
        cooldown_seconds_left=None,
        user_name=user.name if user else None,
        user_email=user.email if user else None,
    )


def _daily_limit_hit(db: Session, user: User, scanned_at: datetime, membership: Membership) -> bool:
    if not membership.daily_limit_enabled:
        return False
    tz = get_gym_timezone()
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
    processed_at = datetime.now(timezone.utc)
    if scanned_at.tzinfo is None:
        scanned_at = scanned_at.replace(tzinfo=timezone.utc)

    token = db.query(AccessToken).filter(AccessToken.token == token_str).first()
    if not token or not token.is_active:
        return _log_and_response(
            db,
            user=None,
            token=token,
            token_str=token_str,
            device_id=device_id,
            device_direction=device_direction,
            scanned_at=scanned_at,
            processed_at=processed_at,
            entry=device_direction == "in",
            exit=device_direction == "out",
            direction_from_state=_direction_from_state(device_direction == "in"),
            direction_mismatch=False,
            client_ip=client_ip,
            user_agent=user_agent,
            allowed=False,
            reason="invalid_token",
        )

    user = db.query(User).filter(User.id == token.user_id).first()
    if not user:
        return _log_and_response(
            db,
            user=None,
            token=token,
            token_str=token_str,
            device_id=device_id,
            device_direction=device_direction,
            scanned_at=scanned_at,
            processed_at=processed_at,
            entry=device_direction == "in",
            exit=device_direction == "out",
            direction_from_state=_direction_from_state(device_direction == "in"),
            direction_mismatch=False,
            client_ip=client_ip,
            user_agent=user_agent,
            allowed=False,
            reason="invalid_token",
        )

    # Trainer bypass
    if _get_trainer_flag(user):
        # Decide entry/exit based on presence
        is_entry = not bool(user.is_in_gym)
        direction_from_state = _direction_from_state(is_entry)
        direction_mismatch = (device_direction == "in" and not is_entry) or (device_direction == "out" and is_entry)
        entry_flag = is_entry
        exit_flag = not is_entry

        try:
            set_presence(db, user, is_entry, scanned_at)
            resp = _log_and_response(
                db,
                user=user,
                token=token,
                token_str=token_str,
                device_id=device_id,
                device_direction=device_direction,
                scanned_at=scanned_at,
                processed_at=processed_at,
                entry=entry_flag,
                exit=exit_flag,
                direction_from_state=direction_from_state,
                direction_mismatch=direction_mismatch,
                client_ip=client_ip,
                user_agent=user_agent,
                allowed=True,
                reason="trainer_allowed",
            )
            db.commit()
            return resp
        except Exception as exc:
            logger.error("Trainer processing failed: %s", exc, exc_info=True)
            db.rollback()
            return _log_and_response(
                db,
                user=user,
                token=token,
                token_str=token_str,
                device_id=device_id,
                device_direction=device_direction,
                scanned_at=scanned_at,
                processed_at=processed_at,
                entry=entry_flag,
                exit=exit_flag,
                direction_from_state=direction_from_state,
                direction_mismatch=direction_mismatch,
                client_ip=client_ip,
                user_agent=user_agent,
                allowed=False,
                reason="invalid_token",
            )

    # State-based direction
    is_entry = not bool(user.is_in_gym)
    is_exit = not is_entry
    direction_from_state = _direction_from_state(is_entry)
    direction_mismatch = (device_direction == "in" and not is_entry) or (device_direction == "out" and is_entry)

    # Entry checks: membership & daily limit
    if is_entry:
        membership = get_active_membership(db, user.id, scanned_at)
        if not membership:
            return _log_and_response(
                db,
                user=user,
                token=token,
                token_str=token_str,
                device_id=device_id,
                device_direction=device_direction,
                scanned_at=scanned_at,
                processed_at=processed_at,
                entry=is_entry,
                exit=is_exit,
                direction_from_state=direction_from_state,
                direction_mismatch=direction_mismatch,
                client_ip=client_ip,
                user_agent=user_agent,
                allowed=False,
                reason="membership_expired",
            )
        if _daily_limit_hit(db, user, scanned_at, membership):
            return _log_and_response(
                db,
                user=user,
                token=token,
                token_str=token_str,
                device_id=device_id,
                device_direction=device_direction,
                scanned_at=scanned_at,
                processed_at=processed_at,
                entry=is_entry,
                exit=is_exit,
                direction_from_state=direction_from_state,
                direction_mismatch=direction_mismatch,
                client_ip=client_ip,
                user_agent=user_agent,
                allowed=False,
                reason="daily_entry_limit_reached",
            )

    # Allowed path: update presence and log
    try:
        set_presence(db, user, is_entry, scanned_at)
        resp = _log_and_response(
            db,
            user=user,
            token=token,
            token_str=token_str,
            device_id=device_id,
            device_direction=device_direction,
            scanned_at=scanned_at,
            processed_at=processed_at,
            entry=is_entry,
            exit=is_exit,
            direction_from_state=direction_from_state,
            direction_mismatch=direction_mismatch,
            client_ip=client_ip,
            user_agent=user_agent,
            allowed=True,
            reason="ok",
        )
        db.commit()
        return resp
    except Exception as exc:
        logger.error("Error processing scan: %s", exc, exc_info=True)
        db.rollback()
        return _log_and_response(
            db,
            user=user,
            token=token,
            token_str=token_str,
            device_id=device_id,
            device_direction=device_direction,
            scanned_at=scanned_at,
            processed_at=processed_at,
            entry=is_entry,
            exit=is_exit,
            direction_from_state=direction_from_state,
            direction_mismatch=direction_mismatch,
            client_ip=client_ip,
            user_agent=user_agent,
            allowed=False,
            reason="invalid_token",
        )
