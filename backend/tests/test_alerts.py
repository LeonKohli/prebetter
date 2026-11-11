"""GET /alerts and GET /alerts/{id} against the seeded events (see tests/seed.py)."""

import pytest

from tests.seed import PAYLOAD, REQUEST_LINE, event_id as eid

URL = "/api/v1/alerts"

# Events with both addresses, newest first (what the default query returns).
DEFAULT_ORDER = [1, 2, 3, 4, 5, 6, 8, 9, 10, 11, 12]


def ids(response) -> list[str]:
    assert response.status_code == 200, response.text
    return [item["id"] for item in response.json()["items"]]


def id_set(*numbers: int) -> set[str]:
    return {eid(n) for n in numbers}


def test_list_defaults_to_newest_first_with_both_addresses(api):
    response = api.get(URL)

    assert ids(response) == [eid(n) for n in DEFAULT_ORDER]
    body = response.json()
    assert body["pagination"] == {"total": 11, "page": 1, "size": 100, "pages": 1}
    assert body["items"][0] == {
        "id": eid(1),
        "detected_at": {"timestamp": "2026-11-10T11:00:00Z"},
        "severity": "high",
        "classification_text": "Alpha scan",
        "source_ipv4": "192.0.2.10",
        "target_ipv4": "198.51.100.7",
        "analyzer": {"name": "s01", "interface": None},
    }


def test_list_without_require_ips_includes_alert_without_addresses(api):
    response = api.get(URL, params={"require_ips": False})

    assert response.json()["pagination"]["total"] == 12
    item = next(i for i in response.json()["items"] if i["id"] == eid(7))
    assert item["source_ipv4"] is None and item["target_ipv4"] is None
    assert item["severity"] == "low"


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("high", {1, 2, 3, 9}),  # priorities 0 and 1
        ("medium", {4, 8, 12}),
        ("low", {6, 10}),
        ("info", {5, 11}),  # priority 4
        ("high,info", {1, 2, 3, 9, 5, 11}),
    ],
)
def test_severity_filter_uses_labels(api, severity, expected):
    response = api.get(URL, params={"severity": severity})

    assert set(ids(response)) == id_set(*expected)
    assert {i["severity"] for i in response.json()["items"]} == set(severity.split(","))


def test_unknown_severity_is_rejected(api):
    assert api.get(URL, params={"severity": "critical"}).status_code == 422


@pytest.mark.parametrize(
    ("param", "value", "expected"),
    [
        ("source_ip", "203.0.113.5", {6, 11}),
        ("source_ip", "192.0.2.0/25", {1, 2, 3, 4, 5, 9, 10, 12}),
        ("source_ip", "192.0.2", {1, 2, 3, 4, 5, 9, 10, 12}),  # prefix means /24
        ("source_ip", "2001:db8::/32", {8}),
        ("target_ip", "198.51.100.8", {5, 12}),
        ("target_ip", "198.51", {1, 2, 3, 4, 5, 6, 9, 10, 11, 12}),  # prefix means /16
    ],
)
def test_ip_filters_match_addresses_networks_and_prefixes(api, param, value, expected):
    assert set(ids(api.get(URL, params={param: value}))) == id_set(*expected)


@pytest.mark.parametrize("value", ["999.1.1.1", "10.0.0.0/33", "abc", "1.2.3.4.5"])
def test_invalid_ip_filter_is_rejected(api, value):
    assert api.get(URL, params={"source_ip": value}).status_code == 422


def test_classification_filter_matches_every_rule_id_with_that_name(api):
    response = api.get(URL, params={"classification": "Alpha scan"})

    assert set(ids(response)) == id_set(1, 2, 6, 9, 10, 12)


def test_classification_and_server_filters_take_lists(api):
    by_rule = api.get(URL, params={"classification": "Delta info,Beta exploit"})
    by_sensor = api.get(URL, params={"server": "s02"})

    assert set(ids(by_rule)) == id_set(3, 4, 5, 8, 11)
    assert set(ids(by_sensor)) == id_set(4, 5, 9, 10)


@pytest.mark.parametrize("end", ["2026-11-10T09:00:00Z", "2026-11-10T09:00:00"])
def test_date_range_is_inclusive_and_naive_means_utc(api, end):
    params = {"start_date": "2026-11-10T05:00:00", "end_date": end}

    assert set(ids(api.get(URL, params=params))) == id_set(4, 5, 6, 8)


def test_severity_sort_desc_lists_most_severe_first_with_stable_ties(api):
    response = api.get(URL, params={"sort_by": "severity", "sort_order": "desc"})

    # Priority 0, then 1, 2, 3, 4; events of equal priority ordered by event id.
    expected = [eid(3)] + sorted(id_set(1, 2, 9)) + sorted(id_set(4, 8, 12))
    expected += sorted(id_set(6, 10)) + sorted(id_set(5, 11))
    assert ids(response) == expected


def test_severity_sort_asc_lists_least_severe_first(api):
    response = api.get(URL, params={"sort_by": "severity", "sort_order": "asc"})

    labels = [i["severity"] for i in response.json()["items"]]
    assert labels == ["info"] * 2 + ["low"] * 2 + ["medium"] * 3 + ["high"] * 4


def test_source_ip_sort_is_numeric_not_lexical(api):
    response = api.get(URL, params={"sort_by": "source_ip", "sort_order": "asc"})

    sources = [i["source_ipv4"] for i in response.json()["items"]]
    assert sources == (
        ["192.0.2.10"] * 5 + ["192.0.2.20"] * 3 + ["203.0.113.5"] * 2 + ["2001:db8::1"]
    )


def test_classification_sort_orders_by_rule_name(api):
    response = api.get(URL, params={"sort_by": "classification", "sort_order": "asc"})

    names = [i["classification_text"] for i in response.json()["items"]]
    assert names == ["Alpha scan"] * 6 + ["Beta exploit"] * 3 + ["Delta info"] * 2


def test_unknown_sort_field_is_rejected(api):
    assert api.get(URL, params={"sort_by": "alert_id"}).status_code == 422


def test_paging_slices_the_sorted_result(api):
    response = api.get(URL, params={"page": 2, "size": 4})

    assert ids(response) == [eid(n) for n in DEFAULT_ORDER[4:8]]
    assert response.json()["pagination"] == {
        "total": 11,
        "page": 2,
        "size": 4,
        "pages": 3,
    }


@pytest.mark.parametrize(("page", "size"), [(101, 100), (5001, 2)])
def test_page_beyond_the_result_window_is_rejected(api, page, size):
    response = api.get(URL, params={"page": page, "size": size})

    assert response.status_code == 422
    assert "10000" in response.json()["detail"]


def test_last_page_inside_the_window_is_empty_not_an_error(api):
    response = api.get(URL, params={"page": 100, "size": 100})

    assert response.status_code == 200
    assert response.json()["items"] == []


def test_detail_returns_typed_fields_and_the_complete_document(api):
    response = api.get(f"{URL}/{eid(1)}")

    assert response.status_code == 200
    body = response.json()
    document = body.pop("document")
    assert body == {
        "id": eid(1),
        "detected_at": {"timestamp": "2026-11-10T11:00:00Z"},
        "severity": "high",
        "classification_text": "Alpha scan",
        "rule": {"id": "1:1001", "version": "4", "category": "Attempted Recon"},
        "action": "would_block",
        "source": {"address": "192.0.2.10", "port": 40001, "mac": "02:00:00:00:00:01"},
        "target": {"address": "198.51.100.7", "port": 25, "mac": None},
        "network": {
            "transport": "tcp",
            "protocol": "smtp",
            "vlan_id": "100",
            "bytes": 2048,
            "packets": 12,
        },
        "flow": {
            "direction": "C2S",
            "started_at": "2026-11-10T10:59:53Z",
            "client_bytes": 1536,
            "client_packets": 8,
            "server_bytes": 512,
            "server_packets": 4,
        },
        "analyzer": {"name": "s01", "interface": "eth0"},
        # Without the fields the typed part already shows (addresses, interface, rule, direction).
        "packet": {
            "thread": "3",
            "timestamp": "11/10-11:00:00.000000",
            "pkt_gen": "raw",
            "pkt_len": 60,
            "ip_ttl": 64,
            "tcp_flags": "AP",
        },
        "payload": PAYLOAD,
        "forwarded": {
            "true_source": "8.8.4.4",
            "forwarded_for": ["8.8.4.4", "10.0.0.1"],
            "via_proxy": "1.1 proxy.example",
        },
        "http_request": REQUEST_LINE,
    }
    assert document["event"]["id"] == eid(1)
    assert '"msg": "Alpha scan"' in document["event"]["original"]


def test_detail_without_addresses_or_payload_reports_them_as_missing(api):
    body = api.get(f"{URL}/{eid(7)}").json()

    assert body["source"] is None and body["target"] is None
    assert body["payload"] is None and body["forwarded"] is None
    assert body["http_request"] is None  # no snort fields, hence no companion lookup


def test_detail_of_unknown_alert_is_404(api):
    assert api.get(f"{URL}/{'0' * 64}").status_code == 404


@pytest.mark.parametrize("alert_id", ["abc", "G" * 64, eid(1).upper()])
def test_detail_with_malformed_id_is_rejected(api, alert_id):
    assert api.get(f"{URL}/{alert_id}").status_code == 422


def test_routes_require_authentication(client):
    assert client.get(URL).status_code in (401, 403)
