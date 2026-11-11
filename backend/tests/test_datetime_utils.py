from datetime import datetime, timedelta, timezone

from app.core.datetime_utils import ensure_timezone, get_current_time


def test_ensure_timezone_assumes_utc_for_naive_datetime():
    assert ensure_timezone(datetime(2023, 10, 26, 12, 0, 0)) == datetime(
        2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc
    )


def test_ensure_timezone_keeps_existing_offset():
    dt = datetime(2023, 10, 26, 14, 0, 0, tzinfo=timezone(timedelta(hours=2)))
    assert ensure_timezone(dt) is dt


def test_get_current_time_is_utc():
    assert get_current_time().tzinfo == timezone.utc
