from datetime import datetime, timedelta, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models import Base, User, AccessToken, Membership, DoorLog
from app.services.scan_processing import process_scan, DEFAULT_DOOR_DURATION


def setup_db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)


def create_member(session, *, token_str: str, daily_limit_enabled: bool = False):
    user = User(
        email="user@example.com",
        name="Test User",
        password_hash="hash",
        is_trainer=False,
        is_in_gym=False,
    )
    session.add(user)
    session.flush()
    token = AccessToken(token=token_str, user_id=user.id, is_active=True)
    session.add(token)
    now = datetime.now(timezone.utc)
    membership = Membership(
        user_id=user.id,
        valid_from=now - timedelta(days=1),
        valid_to=now + timedelta(days=10),
        daily_limit_enabled=daily_limit_enabled,
    )
    session.add(membership)
    session.commit()
    return user, token


def test_allowed_scan_opens_door_and_logs():
    Session = setup_db()
    session = Session()
    user, token = create_member(session, token_str="tok1234567890")

    scanned_at = datetime.now(timezone.utc)
    resp = process_scan(
        session,
        token_str=token.token,
        scanned_at=scanned_at,
        device_id="in-1",
        device_direction="in",
        client_ip="127.0.0.1",
        user_agent="test-agent",
    )

    assert resp.allowed is True
    assert resp.open_door is True
    assert resp.door_open_duration == DEFAULT_DOOR_DURATION
    assert session.query(DoorLog).count() == 1
    session.refresh(user)
    assert user.is_in_gym is True


def test_membership_expired_does_not_open_door():
    Session = setup_db()
    session = Session()
    user = User(
        email="user2@example.com",
        name="No Membership",
        password_hash="hash",
        is_trainer=False,
        is_in_gym=False,
    )
    session.add(user)
    session.flush()
    token = AccessToken(token="tok0987654321", user_id=user.id, is_active=True)
    session.add(token)
    session.commit()

    resp = process_scan(
        session,
        token_str=token.token,
        scanned_at=datetime.now(timezone.utc),
        device_id="in-1",
        device_direction="in",
        client_ip=None,
        user_agent=None,
    )

    assert resp.allowed is False
    assert resp.reason == "membership_expired" or resp.reason == "invalid_token"
    assert getattr(resp, "open_door", False) in (False, None)
    assert session.query(DoorLog).count() == 0
