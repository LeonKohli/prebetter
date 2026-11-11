"""Typical-range baseline: the arithmetic alone, then through the timeline route."""

import copy
from datetime import UTC, datetime, timedelta

import pytest
from opensearchpy import OpenSearch

from app import baseline
from app.core.config import get_settings
from tests.seed import TEMPLATE, TEST_BASE, build_event

TIMELINE = "/api/v1/statistics/timeline"
HOUR = datetime(2026, 11, 10, 10, tzinfo=UTC)
WEEK = timedelta(weeks=1)


def test_band_is_the_median_with_a_robust_spread():
    # Median 2.5, MAD 0.5: the spread falls back to sqrt(2.5) because counts are Poisson-like.
    assert baseline.band([2, 3, 2, 4]) == (0, 7, 2.5)


def test_a_burst_in_one_week_does_not_move_the_band():
    assert baseline.band([10, 11, 9, 5000]) == baseline.band([10, 11, 9, 12])


def test_a_quiet_hour_still_has_a_band():
    assert baseline.band([0, 0, 0, 0]) == (0, 3, 0.0)


def test_too_few_samples_give_no_band():
    assert baseline.band([5, 6]) is None


def test_weeks_before_the_first_event_are_not_counted_as_quiet():
    counts = {HOUR - n * WEEK: 1 for n in range(0, 5)}
    first_seen = HOUR - 2 * WEEK + timedelta(minutes=17)

    # Only two earlier weeks exist: too little history.
    assert baseline.seasonal_baseline(counts, [HOUR], first_seen) == []
    # Without a known start of the data all four weeks count.
    assert len(baseline.seasonal_baseline(counts, [HOUR], None)) == 1


@pytest.fixture
def weekly_history(monkeypatch):
    """A separate index: events at HOUR in the previous weeks, `per_week` events each."""

    def index(per_week: list[int]) -> None:
        settings = get_settings()
        name = "prebetter-test-events-baseline"
        client = OpenSearch(hosts=[settings.OPENSEARCH_URL])
        client.indices.create(index=name, body=TEMPLATE)
        template = build_event(1, TEST_BASE)
        for weeks_back, count in enumerate([1, *per_week]):
            for n in range(count):
                doc = copy.deepcopy(template)
                moment = HOUR - weeks_back * WEEK + timedelta(minutes=n)
                doc["@timestamp"] = moment.strftime("%Y-%m-%dT%H:%M:%SZ")
                doc["event"]["id"] = f"baseline-{weeks_back}-{n}"
                client.index(index=name, id=doc["event"]["id"], body=doc)
        client.indices.refresh(index=name)
        monkeypatch.setattr(settings, "OPENSEARCH_INDEX", name)
        index.client, index.name = client, name

    yield index
    index.client.indices.delete(index=index.name, params={"ignore_unavailable": "true"})


def test_timeline_returns_the_band_for_hours_with_history(api, weekly_history):
    weekly_history([2, 3, 2, 4])
    params = {
        "start_date": "2026-11-10T10:00:00Z",
        "end_date": "2026-11-10T10:59:59Z",
    }

    body = api.get(TIMELINE, params=params).json()

    assert [(p["timestamp"], p["total"]) for p in body["data"]] == [
        ("2026-11-10T10:00:00Z", 1)
    ]
    assert body["baseline"] == [
        {"timestamp": "2026-11-10T10:00:00Z", "low": 0, "high": 7, "typical": 2.5}
    ]


def test_timeline_leaves_the_band_out_without_enough_weeks(api, weekly_history):
    weekly_history([2, 3])

    params = {
        "start_date": "2026-11-10T10:00:00Z",
        "end_date": "2026-11-10T10:59:59Z",
    }

    assert api.get(TIMELINE, params=params).json()["baseline"] == []


def test_only_hourly_buckets_have_a_band(api):
    params = {"start_date": "2026-11-09T00:00:00Z", "end_date": "2026-11-10T23:59:59Z"}

    assert api.get(TIMELINE, params=params | {"time_frame": "day"}).json()["baseline"] == []
