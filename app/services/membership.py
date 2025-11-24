from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.database import SessionLocal
from app.models import Membership, MembershipPackage
from app.services.timezone import day_bounds_utc, get_gym_timezone


@dataclass
class MembershipAccessVerdict:
    allowed: bool
    reason: Optional[str]
    membership: Optional[Membership]
    package: Optional[MembershipPackage]
    daily_limit_hit: bool = False


class MembershipService:
    """Helper for working with membership packages and assignments."""

    def __init__(self, db: Session):
        self.db = db

    # --- Package helpers ---
    def list_packages(self, *, include_inactive: bool = False) -> list[MembershipPackage]:
        query = self.db.query(MembershipPackage)
        if not include_inactive:
            query = query.filter(MembershipPackage.is_active.is_(True))
        return query.order_by(MembershipPackage.created_at.desc(), MembershipPackage.id.asc()).all()

    def get_package(self, package_id: int) -> Optional[MembershipPackage]:
        return self.db.query(MembershipPackage).filter(MembershipPackage.id == package_id).first()

    def get_package_by_slug(self, slug: str) -> Optional[MembershipPackage]:
        return (
            self.db.query(MembershipPackage)
            .filter(or_(MembershipPackage.slug == slug, MembershipPackage.name == slug))
            .first()
        )

    def create_package(
        self,
        *,
        name: str,
        slug: str,
        price_czk: int,
        duration_days: int,
        package_type: str = "membership",
        daily_entry_limit: Optional[int] = None,
        session_limit: Optional[int] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None,
        created_by_admin_id: Optional[int] = None,
    ) -> MembershipPackage:
        package = MembershipPackage(
            name=name,
            slug=slug,
            price_czk=price_czk,
            duration_days=duration_days,
            package_type=package_type,
            daily_entry_limit=daily_entry_limit,
            session_limit=session_limit,
            description=description,
            metadata_json=metadata,
            created_by_admin_id=created_by_admin_id,
        )
        self.db.add(package)
        self.db.flush()
        return package

    # --- Membership helpers ---
    def get_active_membership(self, user_id: int, at_ts: Optional[datetime] = None) -> Optional[Membership]:
        """Return active membership for user at given timestamp."""
        ts_aware = at_ts or datetime.now(timezone.utc)
        if ts_aware.tzinfo is None:
            ts_aware = ts_aware.replace(tzinfo=timezone.utc)
        return (
            self.db.query(Membership)
            .filter(
                Membership.user_id == user_id,
                Membership.valid_from <= ts_aware,
                Membership.valid_to >= ts_aware,
                Membership.status.in_(["active", "grace"]),
            )
            .order_by(Membership.valid_from.desc())
            .first()
        )

    def assign_package_to_user(
        self,
        *,
        user_id: int,
        package: MembershipPackage,
        start_at: Optional[datetime] = None,
        created_by_admin_id: Optional[int] = None,
        notes: Optional[str] = None,
        auto_renew: bool = False,
    ) -> Membership:
        """Instantiate a membership for user from package definition."""
        start = start_at or datetime.now(timezone.utc)
        if start.tzinfo is None:
            start = start.replace(tzinfo=timezone.utc)
        valid_to = start + timedelta(days=package.duration_days)
        membership = Membership(
            user_id=user_id,
            package_id=package.id,
            package_name_cache=package.name,
            membership_type=package.package_type,
            price_czk=package.price_czk,
            valid_from=start,
            valid_to=valid_to,
            daily_limit_enabled=bool(package.daily_entry_limit),
            daily_limit=package.daily_entry_limit,
            sessions_total=package.session_limit,
            sessions_used=0 if package.session_limit else None,
            status="active",
            notes=notes,
            metadata_json=package.metadata_json,
            auto_renew=auto_renew,
            created_by_admin_id=created_by_admin_id,
        )
        self.db.add(membership)
        self.db.flush()
        return membership

    def can_consume_entry(
        self, membership: Membership, *, at_ts: Optional[datetime] = None
    ) -> MembershipAccessVerdict:
        ts = at_ts or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        package = membership.package

        if membership.status not in ("active", "grace"):
            return MembershipAccessVerdict(
                allowed=False,
                reason="membership_inactive",
                membership=membership,
                package=package,
            )
        if membership.valid_to < ts:
            return MembershipAccessVerdict(
                allowed=False,
                reason="membership_expired",
                membership=membership,
                package=package,
            )
        if membership.sessions_total is not None and membership.sessions_used is not None:
            if membership.sessions_used >= membership.sessions_total:
                return MembershipAccessVerdict(
                    allowed=False,
                    reason="sessions_limit_reached",
                    membership=membership,
                    package=package,
                )

        daily_limit_hit = False
        if membership.daily_limit_enabled and membership.daily_limit:
            daily_limit_hit = self._is_daily_limit_hit(membership, ts)
            if daily_limit_hit:
                return MembershipAccessVerdict(
                    allowed=False,
                    reason="daily_limit",
                    membership=membership,
                    package=package,
                    daily_limit_hit=True,
                )

        return MembershipAccessVerdict(
            allowed=True,
            reason=None,
            membership=membership,
            package=package,
            daily_limit_hit=daily_limit_hit,
        )

    def record_entry_usage(self, membership: Membership, *, at_ts: Optional[datetime] = None) -> None:
        """Update membership usage counters after a successful entry."""
        ts = at_ts or datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)

        if membership.daily_limit_enabled and membership.daily_limit:
            tz = get_gym_timezone()
            start_utc, end_utc = day_bounds_utc(ts, tz)
            last_usage = membership.last_usage_at
            in_same_day = bool(
                last_usage
                and start_utc <= last_usage.replace(tzinfo=timezone.utc if last_usage.tzinfo is None else last_usage.tzinfo) < end_utc
            )
            if not in_same_day:
                membership.daily_usage_count = 1
            else:
                membership.daily_usage_count = (membership.daily_usage_count or 0) + 1
            membership.last_usage_at = ts

        if membership.sessions_total is not None:
            membership.sessions_used = (membership.sessions_used or 0) + 1

    def _is_daily_limit_hit(self, membership: Membership, ts: datetime) -> bool:
        """Check if membership daily limit was already used."""
        tz = get_gym_timezone()
        start_utc, end_utc = day_bounds_utc(ts, tz)
        last_usage = membership.last_usage_at
        if not last_usage:
            return False
        normalized_last = last_usage
        if normalized_last.tzinfo is None:
            normalized_last = normalized_last.replace(tzinfo=timezone.utc)
        return start_utc <= normalized_last < end_utc and (membership.daily_usage_count or 0) >= (
            membership.daily_limit or 0
        )


def get_active_membership(db: Session, user_id: int, at_ts: datetime) -> Optional[Membership]:
    """Backward-compatible helper used by existing code paths."""
    service = MembershipService(db)
    return service.get_active_membership(user_id, at_ts)


def ensure_default_membership_packages():
    """Seed an initial 30-day membership package for development environments."""
    defaults = [
        {
            "slug": "monthly_standard",
            "name": "30denní permanentka",
            "price_czk": 1500,
            "duration_days": 30,
            "daily_entry_limit": 1,
            "package_type": "membership",
            "description": "Standardní měsíční permanentka s limitem jednoho vstupu denně.",
        },
        {
            "slug": "personal_training_single",
            "name": "Osobní trénink",
            "price_czk": 800,
            "duration_days": 30,
            "daily_entry_limit": None,
            "session_limit": 1,
            "package_type": "personal_training",
            "description": "Jednorázový osobní trénink s trenérem.",
        },
    ]

    session = SessionLocal()
    try:
        for pkg in defaults:
            existing = (
                session.query(MembershipPackage)
                .filter(
                    or_(
                        MembershipPackage.slug == pkg["slug"],
                        MembershipPackage.name == pkg["name"],
                    )
                )
                .first()
            )
            if existing:
                # Update pricing/duration if changed
                existing.price_czk = pkg["price_czk"]
                existing.duration_days = pkg["duration_days"]
                existing.daily_entry_limit = pkg.get("daily_entry_limit")
                existing.session_limit = pkg.get("session_limit")
                existing.package_type = pkg["package_type"]
                existing.description = pkg.get("description")
                existing.is_active = True
            else:
                session.add(
                    MembershipPackage(
                        slug=pkg["slug"],
                        name=pkg["name"],
                        price_czk=pkg["price_czk"],
                        duration_days=pkg["duration_days"],
                        daily_entry_limit=pkg.get("daily_entry_limit"),
                        session_limit=pkg.get("session_limit"),
                        package_type=pkg["package_type"],
                        description=pkg.get("description"),
                    )
                )
        session.commit()
    finally:
        session.close()
