from datetime import datetime, timezone, timedelta
import os
from zoneinfo import ZoneInfo


DEFAULT_TZ = "Europe/Prague"


def get_gym_timezone() -> ZoneInfo:
    """Return gym timezone from env or default."""
    tz_name = os.getenv("GYM_TIMEZONE", DEFAULT_TZ)
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo(DEFAULT_TZ)


def day_bounds_utc(ts: datetime, tz: ZoneInfo):
    """
    Given an aware UTC timestamp, return (start_utc, end_utc) for the local day in the given timezone.
    """
    local = ts.astimezone(tz)
    day_start_local = local.replace(hour=0, minute=0, second=0, microsecond=0)
    start_utc = day_start_local.astimezone(timezone.utc)
    end_utc = (day_start_local + timedelta(days=1)).astimezone(timezone.utc)
    return start_utc, end_utc
