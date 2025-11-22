from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import Membership


def get_active_membership(db: Session, user_id: int, at_ts: datetime) -> Optional[Membership]:
    """Return active membership for user at given timestamp."""
    ts_aware = at_ts
    if ts_aware.tzinfo is None:
        ts_aware = ts_aware.replace(tzinfo=timezone.utc)
    return (
        db.query(Membership)
        .filter(
            Membership.user_id == user_id,
            Membership.valid_from <= ts_aware,
            Membership.valid_to >= ts_aware,
        )
        .order_by(Membership.valid_from.desc())
        .first()
    )
