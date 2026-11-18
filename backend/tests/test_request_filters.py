"""Filters on the headers of an alert's HTTP request, against the seeded requests (see tests/seed.py).

Events 1, 2 and 3 have a request document; every other alert has none. Event 1 is curl for
www.example.org from 8.8.4.4, event 2 scanner/1.0 for the same host from 203.0.113.9, and
event 3 a browser for api.example.org without a client address.
"""

import pytest

from app.opensearch import queries
from tests.seed import COMPANIONS, event_id as eid

ALERTS = "/api/v1/alerts"
GROUPS = "/api/v1/alerts/groups"
TIMELINE = "/api/v1/statistics/timeline"
VALUES = "/api/v1/reference/request-values"
DAY = {"start_date": "2026-11-09T00:00:00Z", "end_date": "2026-11-10T23:59:59Z"}

# Events with both addresses, newest first: what the list returns without a filter.
ALL = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]
BROWSER = COMPANIONS[3]["user_agent"]  # has commas


def listed(api, **params) -> list[str]:
    response = api.get(ALERTS, params={**DAY, **params})
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def numbers(*of: int) -> list[str]:
    return [eid(n) for n in of]


@pytest.mark.parametrize(
    ("params", "expected"),
    [
        pytest.param({"user_agent": ["scanner/1.0"]}, [2], id="user agent"),
        pytest.param({"user_agent": [BROWSER]}, [3], id="user agent with commas"),
        pytest.param(
            {"user_agent": ["curl/8.7.1", "scanner/1.0"]},
            [1, 2],
            id="user agents are alternatives",
        ),
        pytest.param({"host": ["www.example.org"]}, [1, 2], id="host"),
        pytest.param({"host": ["WWW.Example.ORG"]}, [1, 2], id="host in any case"),
        pytest.param({"client_ip": ["203.0.113.9"]}, [2], id="client address"),
        pytest.param({"client_ip": ["203.0.113.0/24"]}, [2], id="client network"),
        pytest.param({"client_ip": ["8.8"]}, [1], id="client prefix"),
        pytest.param(
            {"host": ["www.example.org"], "user_agent": ["scanner/1.0"]},
            [2],
            id="kinds all have to hold",
        ),
        pytest.param(
            {"host": ["api.example.org"], "user_agent": ["scanner/1.0"]},
            [],
            id="no request has both",
        ),
        pytest.param(
            {"user_agent": ["nothing like it"]},
            [],
            id="no match is an empty list, not everything",
        ),
    ],
)
def test_include_selects_the_alerts_of_matching_requests(api, params, expected):
    assert listed(api, **params) == numbers(*expected)


@pytest.mark.parametrize(
    ("params", "hidden"),
    [
        pytest.param({"exclude_user_agent": ["scanner/1.0"]}, [2], id="user agent"),
        pytest.param({"exclude_host": ["www.example.org"]}, [1, 2], id="host"),
        pytest.param({"exclude_client_ip": ["203.0.113.9"]}, [2], id="client address"),
        pytest.param(
            {
                "exclude_user_agent": ["scanner/1.0"],
                "exclude_host": ["api.example.org"],
            },
            [2, 3],
            id="any of the kinds hides",
        ),
    ],
)
def test_exclude_hides_matching_requests_and_keeps_alerts_without_one(
    api, params, hidden
):
    # Alerts 4 to 12 have no request at all and stay.
    assert listed(api, **params) == numbers(*[n for n in ALL if n not in hidden])


def test_include_and_exclude_combine(api):
    assert listed(
        api, host=["www.example.org"], exclude_user_agent=["scanner/1.0"]
    ) == numbers(1)


def test_filters_work_with_the_other_filters(api):
    assert listed(
        api, host=["www.example.org"], severity="high", source_ip="192.0.2.10"
    ) == numbers(1, 2)
    assert listed(api, host=["www.example.org"], classification="Beta exploit") == []


def test_the_range_limits_the_requests_too(api):
    # Event 2 is at 10:30, before this range.
    window = {"start_date": "2026-11-10T11:00:00Z", "end_date": "2026-11-10T12:00:00Z"}

    response = api.get(ALERTS, params={**window, "user_agent": ["scanner/1.0"]})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_groups_follow_the_filter(api):
    response = api.get(GROUPS, params={**DAY, "user_agent": ["scanner/1.0"]})

    assert response.status_code == 200, response.text
    groups = response.json()["groups"]
    assert [(g["source_ipv4"], g["target_ipv4"], g["total_count"]) for g in groups] == [
        ("192.0.2.10", "198.51.100.7", 1)
    ]


def test_timeline_follows_the_filter(api):
    response = api.get(TIMELINE, params={**DAY, "exclude_host": ["www.example.org"]})

    assert response.status_code == 200, response.text
    assert sum(p["total"] for p in response.json()["data"]) == len(ALL) - 2


def test_too_many_matching_requests_are_refused(api, monkeypatch):
    monkeypatch.setattr(queries, "MAX_REQUEST_KEYS", 1)

    response = api.get(ALERTS, params={**DAY, "host": ["www.example.org"]})

    assert response.status_code == 422
    assert "narrow" in response.json()["detail"]


@pytest.mark.parametrize(
    "params",
    [
        {"client_ip": ["not an address"]},
        {"exclude_client_ip": ["10.0.0.0/33"]},
        {"user_agent": [""]},
        {"host": ["x" * 1025]},
        {"user_agent": [f"agent-{n}" for n in range(21)]},
    ],
    ids=["address", "network", "empty", "long", "many"],
)
def test_malformed_request_filters_are_rejected(api, params):
    assert api.get(ALERTS, params=params).status_code == 422


def values(api, **params) -> list[tuple[str, int]]:
    response = api.get(VALUES, params={**DAY, **params})
    assert response.status_code == 200, response.text
    return [(v["value"], v["count"]) for v in response.json()]


def test_values_list_the_most_common_first(api):
    assert values(api, field="host") == [("www.example.org", 2), ("api.example.org", 1)]
    assert sorted(values(api, field="client_ip")) == [
        ("203.0.113.9", 1),
        ("8.8.4.4", 1),
    ]
    assert {value for value, _ in values(api, field="user_agent")} == {
        "curl/8.7.1",
        "scanner/1.0",
        BROWSER,
    }


@pytest.mark.parametrize(
    ("field", "q", "expected"),
    [
        ("user_agent", "SCAN", ["scanner/1.0"]),
        ("user_agent", "like Gecko", [BROWSER]),
        ("host", "api.", ["api.example.org"]),
        ("client_ip", "203", ["203.0.113.9"]),
        ("user_agent", "*", []),
    ],
)
def test_values_narrow_by_text_in_any_case(api, field, q, expected):
    assert [value for value, _ in values(api, field=field, q=q)] == expected


def test_values_follow_the_range(api):
    window = {"start_date": "2026-11-10T11:00:00Z", "end_date": "2026-11-10T12:00:00Z"}

    assert values(api, field="host", **window) == [("www.example.org", 1)]


def test_values_reject_an_unknown_field(api):
    assert api.get(VALUES, params={"field": "cookie"}).status_code == 422
