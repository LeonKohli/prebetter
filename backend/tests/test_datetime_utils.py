from datetime import datetime, timezone, timedelta

from app.core.datetime_utils import (
    ensure_timezone,
    format_datetime,
    parse_datetime,
    get_current_time,
    get_time_range,
)


# Tests for ensure_timezone
def test_ensure_timezone_naive():
    naive_dt = datetime(2023, 10, 26, 12, 0, 0)
    aware_dt = ensure_timezone(naive_dt)
    assert aware_dt is not None
    assert aware_dt.tzinfo == timezone.utc


def test_ensure_timezone_aware_utc():
    aware_dt_utc = datetime(2023, 10, 26, 12, 0, 0, tzinfo=timezone.utc)
    result_dt = ensure_timezone(aware_dt_utc)
    assert result_dt == aware_dt_utc  # Should return the same object


def test_ensure_timezone_aware_non_utc():
    non_utc_tz = timezone(timedelta(hours=2))
    aware_dt_non_utc = datetime(2023, 10, 26, 14, 0, 0, tzinfo=non_utc_tz)
    result_dt = ensure_timezone(aware_dt_non_utc)
    # ensure_timezone doesn't convert, just ensures tz exists
    assert result_dt == aware_dt_non_utc
    assert result_dt is not None and result_dt.tzinfo == non_utc_tz


def test_ensure_timezone_none():
    assert ensure_timezone(None) is None


# Tests for format_datetime
def test_format_datetime_basic():
    dt = datetime(2023, 10, 26, 14, 30, 15, tzinfo=timezone.utc)
    expected = "26 Oct 2023, 14:30:15 UTC"
    assert format_datetime(dt) == expected


def test_format_datetime_no_timezone():
    dt = datetime(2023, 10, 26, 14, 30, 15, tzinfo=timezone.utc)
    expected = "26 Oct 2023, 14:30:15"
    assert format_datetime(dt, include_timezone=False) == expected


def test_format_datetime_naive_input():
    # Should assume UTC if naive
    naive_dt = datetime(2023, 10, 26, 14, 30, 15)
    expected = "26 Oct 2023, 14:30:15 UTC"
    assert format_datetime(naive_dt) == expected


def test_format_datetime_none():
    assert format_datetime(None) == ""


# Tests for parse_datetime
def test_parse_datetime_iso_zulu():
    dt_str = "2023-10-26T10:00:00Z"
    expected_dt = datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
    assert parse_datetime(dt_str) == expected_dt


def test_parse_datetime_iso_offset():
    dt_str = "2023-10-26T12:00:00+02:00"
    # The function parses the offset correctly but doesn't convert the tzinfo object itself to UTC
    # It ensures the datetime object is timezone-aware.
    expected_dt_utc = datetime(
        2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc
    )  # Equivalent UTC time
    parsed = parse_datetime(dt_str)
    assert parsed is not None
    # Check that the timezone info exists and is the original offset
    assert parsed.tzinfo == timezone(timedelta(hours=2))
    # Check that the time represents the correct moment (compare by converting to UTC)
    assert parsed.astimezone(timezone.utc) == expected_dt_utc


def test_parse_datetime_iso_no_offset():
    # Should assume UTC if no offset provided by fromisoformat logic and ensure_timezone
    dt_str = "2023-10-26T10:00:00"
    expected_dt = datetime(2023, 10, 26, 10, 0, 0, tzinfo=timezone.utc)
    parsed = parse_datetime(dt_str)
    assert parsed is not None
    assert parsed.tzinfo == timezone.utc
    assert parsed == expected_dt


def test_parse_datetime_invalid_string():
    assert parse_datetime("invalid date string") is None
    assert parse_datetime("26-10-2023") is None  # Incorrect format


def test_parse_datetime_none():
    assert parse_datetime(None) is None
    assert parse_datetime("") is None


# --- Tests for time-dependent functions (potentially need mocking) ---


# Test for get_current_time
def test_get_current_time():
    now = get_current_time()
    assert isinstance(now, datetime)
    assert now.tzinfo == timezone.utc


# Test for get_time_range (basic checks without mocking)
def test_get_time_range():
    hours = 3
    start_time, end_time = get_time_range(hours)

    assert isinstance(start_time, datetime)
    assert isinstance(end_time, datetime)
    assert start_time.tzinfo == timezone.utc
    assert end_time.tzinfo == timezone.utc
    assert end_time > start_time
    # Allow for slight execution delay
    assert (end_time - start_time) >= timedelta(hours=hours)
    assert (end_time - start_time) < timedelta(
        hours=hours, seconds=5
    )  # Check it's close
