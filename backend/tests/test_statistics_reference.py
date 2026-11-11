"""Timeline and reference lists against the seeded events (see tests/seed.py)."""

from datetime import datetime

import pytest

from app.core.config import get_settings
from app.opensearch import queries

TIMELINE = "/api/v1/statistics/timeline"
DAY = {"start_date": "2026-11-09T00:00:00Z", "end_date": "2026-11-10T23:59:59Z"}


def points(response) -> list[tuple[str, int]]:
    assert response.status_code == 200, response.text
    return [(p["timestamp"], p["total"]) for p in response.json()["data"]]


def nonzero(response) -> list[tuple[str, int]]:
    return [(ts, total) for ts, total in points(response) if total]


def test_hourly_buckets_cover_the_window_and_start_on_the_hour(api):
    params = {"start_date": "2026-11-10T00:00:00Z", "end_date": "2026-11-10T12:00:00Z"}

    response = api.get(TIMELINE, params=params)

    # Empty hours are present with 0, also before the first and after the last alert.
    series = points(response)
    assert [ts for ts, _ in series] == [f"2026-11-10T{h:02d}:00:00Z" for h in range(13)]
    # Nothing at 06:00: its only alert has no addresses and is filtered out.
    assert nonzero(response) == [
        ("2026-11-10T05:00:00Z", 1),
        ("2026-11-10T07:00:00Z", 1),
        ("2026-11-10T08:00:00Z", 1),
        ("2026-11-10T09:00:00Z", 1),
        ("2026-11-10T10:00:00Z", 2),
        ("2026-11-10T11:00:00Z", 1),
    ]
    assert response.json()["time_frame"] == "hour"
    assert response.json()["start_date"] == "2026-11-10T00:00:00Z"


def test_timeline_honours_the_alert_filters(api):
    params = {
        "start_date": "2026-11-10T00:00:00Z",
        "server": "s02",
        "require_ips": False,
    }

    response = api.get(TIMELINE, params=params | {"end_date": "2026-11-10T12:00:00Z"})

    assert nonzero(response) == [
        ("2026-11-10T06:00:00Z", 1),
        ("2026-11-10T08:00:00Z", 1),
        ("2026-11-10T09:00:00Z", 1),
    ]


def test_minute_buckets(api):
    params = {
        "time_frame": "minute",
        "start_date": "2026-11-10T10:29:00Z",
        "end_date": "2026-11-10T10:31:00Z",
    }

    assert points(api.get(TIMELINE, params=params)) == [
        ("2026-11-10T10:29:00Z", 0),
        ("2026-11-10T10:30:00Z", 1),
        ("2026-11-10T10:31:00Z", 0),
    ]


def test_daily_buckets_start_at_midnight_utc(api):
    response = api.get(TIMELINE, params=DAY | {"time_frame": "day"})

    assert points(response) == [
        ("2026-11-09T00:00:00Z", 4),
        ("2026-11-10T00:00:00Z", 7),
    ]


def test_weekly_buckets_start_on_monday(api):
    response = api.get(TIMELINE, params=DAY | {"time_frame": "week"})

    # 2026-11-10 is a Tuesday: both days fall into the week of Monday the 9th.
    assert points(response) == [("2026-11-09T00:00:00Z", 11)]


def test_missing_dates_default_to_a_window_ending_now(api):
    body = api.get(TIMELINE, params={"time_frame": "day"}).json()

    start, end = (datetime.fromisoformat(body[k]) for k in ("start_date", "end_date"))
    assert (end - start).days == 30


def test_a_window_with_too_many_buckets_is_rejected(api):
    params = {
        "time_frame": "minute",
        "start_date": "2026-11-01T00:00:00Z",
        "end_date": "2026-11-10T00:00:00Z",
    }

    assert api.get(TIMELINE, params=params).status_code == 422


def test_unknown_time_frame_is_rejected(api):
    assert api.get(TIMELINE, params={"time_frame": "month"}).status_code == 422


def test_severities_are_the_four_labels(api):
    response = api.get("/api/v1/reference/severities")

    assert response.json() == ["high", "medium", "low", "info"]


@pytest.mark.parametrize("page_size", [1000, 1])
def test_reference_lists_are_complete_and_sorted(api, monkeypatch, page_size):
    monkeypatch.setattr(queries, "COMPOSITE_PAGE_SIZE", page_size)

    servers = api.get("/api/v1/reference/servers")
    classifications = api.get("/api/v1/reference/classifications")

    assert servers.json() == ["s01", "s02"]
    # Two rule ids share "Alpha scan"; it is listed once.
    assert classifications.json() == ["Alpha scan", "Beta exploit", "Delta info"]


def test_a_pattern_without_indices_answers_with_empty_results(api, monkeypatch):
    # A fresh installation: OpenSearch omits the aggregations section entirely.
    monkeypatch.setattr(get_settings(), "OPENSEARCH_INDEX", "prebetter-test-none-*")

    assert api.get(TIMELINE, params=DAY).json()["data"] == []
    assert api.get("/api/v1/alerts/groups").json()["groups"] == []
    assert api.get("/api/v1/alerts").json()["items"] == []
    assert api.get("/api/v1/reference/classifications").json() == []
