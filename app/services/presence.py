import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import User

logger = logging.getLogger(__name__)


def set_presence(db: Session, user: User, is_in_gym: bool, when: datetime):
    """Update presence flag and timestamps for a user."""
    ts = when if when.tzinfo else when.replace(tzinfo=timezone.utc)
    user.is_in_gym = is_in_gym
    if is_in_gym:
        user.last_entry_at = ts
    else:
        user.last_exit_at = ts
    db.add(user)


def rebuild_presence_from_logs(db: Session, user: User):
    """Rebuild presence flag from the most recent access log (entry/exit)."""
    from app.models import AccessLog  # local import to avoid circular

    logger.info("Rebuild presence requested for user %s (id=%s)", user.email, user.id)
    last_log = (
        db.query(AccessLog)
        .filter(AccessLog.user_id == user.id)
        .order_by(AccessLog.scanned_at.desc().nullslast(), AccessLog.created_at.desc())
        .first()
    )
    if not last_log:
        user.is_in_gym = False
        user.last_entry_at = None
        user.last_exit_at = None
        db.add(user)
        return user.is_in_gym

    if last_log.entry:
        user.is_in_gym = True
        user.last_entry_at = last_log.scanned_at or last_log.created_at
    elif last_log.exit:
        user.is_in_gym = False
        user.last_exit_at = last_log.scanned_at or last_log.created_at
    else:
        user.is_in_gym = False
    db.add(user)
    return user.is_in_gym
