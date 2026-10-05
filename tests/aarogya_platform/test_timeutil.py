from datetime import datetime, timezone

import pytest

from aarogya.platform.timeutil import to_ist, to_ist_display, utc_now_iso


def test_utc_now_iso_ends_with_utc_offset():
    stamp = utc_now_iso()
    assert stamp.endswith("+00:00")
    assert datetime.fromisoformat(stamp).utcoffset().total_seconds() == 0


def test_display_converts_to_ist():
    shown = to_ist_display("2026-01-01T00:00:00+00:00")
    assert shown == "2026-01-01 05:30 IST"


def test_display_crosses_midnight():
    shown = to_ist_display("2026-10-05T20:00:00+00:00")
    assert shown == "2026-10-06 01:30 IST"


def test_ist_keeps_same_instant():
    utc = datetime(2026, 3, 1, 12, tzinfo=timezone.utc)
    assert to_ist(utc.isoformat()) == utc


@pytest.mark.parametrize("empty", [None, ""])
def test_display_passes_empty_through(empty):
    assert to_ist_display(empty) == empty


def test_naive_timestamp_rejected():
    with pytest.raises(ValueError):
        to_ist("2026-01-01T00:00:00")
