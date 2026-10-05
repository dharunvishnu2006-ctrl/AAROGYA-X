"""One way of storing time: UTC ISO-8601. Display in Indian time."""

from datetime import datetime, timedelta, timezone, tzinfo
from typing import Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

IST_LABEL = "IST"
DISPLAY_FORMAT = "%Y-%m-%d %H:%M"


def _load_ist() -> tzinfo:
    try:
        return ZoneInfo("Asia/Kolkata")
    except ZoneInfoNotFoundError:
        # Fall back; India has no DST
        return timezone(timedelta(hours=5, minutes=30), IST_LABEL)


IST = _load_ist()


def utc_now_iso() -> str:
    """Returns the current time as UTC ISO-8601 ending +00:00."""
    return datetime.now(timezone.utc).isoformat()


def to_ist(iso_utc: str) -> datetime:
    """Parses a stored UTC timestamp; rejects one without offset."""
    moment = datetime.fromisoformat(iso_utc)
    if moment.tzinfo is None:
        raise ValueError("Stored timestamp has no UTC offset.")
    return moment.astimezone(IST)


def to_ist_display(iso_utc: Optional[str]) -> Optional[str]:
    """Formats a stored UTC timestamp for the dashboard in IST."""
    if not iso_utc:
        return iso_utc
    return f"{to_ist(iso_utc).strftime(DISPLAY_FORMAT)} {IST_LABEL}"
