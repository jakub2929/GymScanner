from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.models import AccessLog, PresenceSession, User, AccessToken, Membership


class PresenceSessionService:
    """Helper for managing presence sessions (IN/OUT visits)."""

    def __init__(self, db: Session):
        self.db = db

    def _normalize_ts(self, ts: datetime) -> datetime:
        return ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)

    def start_session(
        self,
        *,
        user: User,
        token: Optional[AccessToken],
        membership: Optional[Membership],
        access_log: Optional[AccessLog] = None,
        scanned_at: datetime,
        metadata: Optional[dict] = None,
    ) -> PresenceSession:
        session = PresenceSession(
            user_id=user.id,
            token_id=token.id if token else None,
            membership_id=membership.id if membership else None,
            started_at=self._normalize_ts(scanned_at),
            last_direction="in",
            status="active",
            metadata_json=metadata,
        )
        self.db.add(session)
        self.db.flush()  # populate session.id
        if access_log is not None:
            access_log.presence_session_id = session.id
            self.db.add(access_log)
        return session

    def end_session(
        self,
        *,
        session: PresenceSession,
        access_log: Optional[AccessLog],
        scanned_at: datetime,
        status: str = "closed",
        notes: Optional[str] = None,
    ) -> PresenceSession:
        scanned_norm = self._normalize_ts(scanned_at)
        session.ended_at = scanned_norm
        session.last_direction = "out"
        session.status = status
        if notes:
            session.notes = (session.notes or "") + f"\n{notes}"
        if session.started_at:
            duration = (scanned_norm - session.started_at).total_seconds()
            session.duration_seconds = max(0, int(duration))
        if access_log is not None:
            access_log.presence_session_id = session.id
            self.db.add(access_log)
        self.db.add(session)
        return session

    def find_active_session(self, user_id: int) -> Optional[PresenceSession]:
        return (
            self.db.query(PresenceSession)
            .filter(PresenceSession.user_id == user_id, PresenceSession.ended_at.is_(None), PresenceSession.status == "active")
            .order_by(PresenceSession.started_at.desc())
            .first()
        )

    def force_close(self, session: PresenceSession, *, status: str = "timeout", notes: Optional[str] = None) -> PresenceSession:
        session.ended_at = datetime.now(timezone.utc)
        session.status = status
        if notes:
            session.notes = (session.notes or "") + f"\n{notes}"
        if session.started_at:
            session.duration_seconds = max(0, int((session.ended_at - session.started_at).total_seconds()))
        self.db.add(session)
        return session

    def list_active_sessions(self) -> list[PresenceSession]:
        return (
            self.db.query(PresenceSession)
            .filter(PresenceSession.ended_at.is_(None), PresenceSession.status == "active")
            .order_by(PresenceSession.started_at.desc())
            .all()
        )

    def list_sessions(self, *, user_id: Optional[int] = None, limit: int = 20) -> list[PresenceSession]:
        query = self.db.query(PresenceSession)
        if user_id is not None:
            query = query.filter(PresenceSession.user_id == user_id)
        return query.order_by(PresenceSession.started_at.desc()).limit(limit).all()


def serialize_presence_session(session: PresenceSession, user: Optional[User] = None) -> dict:
    return {
        "id": session.id,
        "user_id": session.user_id,
        "user_name": user.name if user else None,
        "user_email": user.email if user else None,
        "token_id": session.token_id,
        "membership_id": session.membership_id,
        "started_at": session.started_at.isoformat() if session.started_at else None,
        "ended_at": session.ended_at.isoformat() if session.ended_at else None,
        "duration_seconds": session.duration_seconds,
        "last_direction": session.last_direction,
        "status": session.status,
        "notes": session.notes,
        "metadata": session.metadata_json,
    }
