"""GET /alerts/groups against the seeded events (see tests/seed.py)."""

import pytest

from app.opensearch import queries
from app.repositories import alerts as alerts_repository

URL = "/api/v1/alerts/groups"

# Pairs with one alert each, in address order.
SINGLES = [
    ("192.0.2.10", "198.51.100.8"),
    ("192.0.2.20", "198.51.100.8"),
    ("203.0.113.5", "198.51.100.7"),
    ("203.0.113.5", "198.51.100.9"),
    ("2001:db8::1", "2001:db8::2"),
]
P_BUSY = ("192.0.2.10", "198.51.100.7")  # 4 alerts
P_TWO = ("192.0.2.20", "198.51.100.7")  # 2 alerts


def pairs(response) -> list[tuple[str, str]]:
    assert response.status_code == 200, response.text
    return [(g["source_ipv4"], g["target_ipv4"]) for g in response.json()["groups"]]


def test_groups_default_to_largest_first_with_address_order_for_ties(api):
    response = api.get(URL)

    assert pairs(response) == [P_BUSY, P_TWO, *SINGLES]
    body = response.json()
    assert body["pagination"] == {"total": 7, "page": 1, "size": 100, "pages": 1}
    assert body["total_alerts"] == 11


def test_group_alerts_are_counted_per_rule_name_newest_first(api):
    groups = api.get(URL).json()["groups"]

    # Rule ids 1:1001 and 1:1003 share the name "Alpha scan".
    assert groups[0] == {
        "source_ipv4": "192.0.2.10",
        "target_ipv4": "198.51.100.7",
        "total_count": 4,
        "alerts": [
            {
                "classification": "Alpha scan",
                "count": 3,
                "detected_at": "2026-11-10T11:00:00Z",
            },
            {
                "classification": "Beta exploit",
                "count": 1,
                "detected_at": "2026-11-10T10:00:00Z",
            },
        ],
    }
    # Here the newer rule sorts last by name, so the order is by time, not by name.
    assert [a["classification"] for a in groups[1]["alerts"]] == [
        "Beta exploit",
        "Alpha scan",
    ]


@pytest.mark.parametrize(
    ("sort_by", "sort_order", "expected"),
    [
        ("total_count", "asc", [*SINGLES, P_TWO, P_BUSY]),
        ("source_ip", "asc", [P_BUSY, SINGLES[0], P_TWO, *SINGLES[1:]]),
        (
            "target_ip",
            "desc",
            [SINGLES[4], SINGLES[3], SINGLES[0], SINGLES[1], P_BUSY, P_TWO, SINGLES[2]],
        ),
        (
            "detect_time",
            "desc",
            [P_BUSY, P_TWO, SINGLES[1], SINGLES[2], SINGLES[4], SINGLES[3], SINGLES[0]],
        ),
    ],
)
def test_groups_sort(api, sort_by, sort_order, expected):
    response = api.get(URL, params={"sort_by": sort_by, "sort_order": sort_order})

    assert pairs(response) == expected


def test_groups_page_across_pairs_with_exact_totals(api):
    first = api.get(URL, params={"size": 3}).json()
    last = api.get(URL, params={"size": 3, "page": 3}).json()
    beyond = api.get(URL, params={"size": 3, "page": 4}).json()

    assert first["pagination"] == {"total": 7, "page": 1, "size": 3, "pages": 3}
    assert first["total_alerts"] == 4 + 2 + 1
    assert [(g["source_ipv4"], g["target_ipv4"]) for g in last["groups"]] == [
        SINGLES[4]
    ]
    assert beyond["groups"] == [] and beyond["total_alerts"] == 0
    assert beyond["pagination"]["total"] == 7


def test_groups_honour_the_filters(api):
    response = api.get(URL, params={"severity": "high"})

    assert pairs(response) == [P_BUSY]
    assert response.json()["total_alerts"] == 4


def test_groups_reject_sort_fields_without_meaning_for_pairs(api):
    assert api.get(URL, params={"sort_by": "severity"}).status_code == 422


def test_groups_are_complete_when_the_enumeration_needs_many_pages(api, monkeypatch):
    monkeypatch.setattr(queries, "COMPOSITE_PAGE_SIZE", 2)

    response = api.get(URL)

    assert pairs(response) == [P_BUSY, P_TWO, *SINGLES]
    assert response.json()["groups"][0]["total_count"] == 4


def test_too_many_pairs_are_rejected(api, monkeypatch):
    monkeypatch.setattr(alerts_repository, "MAX_PAIRS", 6)

    response = api.get(URL)

    assert response.status_code == 422
    assert "narrow the filter" in response.json()["detail"]
