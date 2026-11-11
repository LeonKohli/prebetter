import base64

import pytest

from app.opensearch.request_line import decode_request_line, request_id

ALERT = {
    "observer": {"name": "011", "ingress": {"interface": {"name": "eno5"}}},
    "snort": {
        "thread": "3",
        "timestamp": "09/21-15:13:20.003000",
        "rule": "1:19438:14",
        "src_ap": "192.0.2.10:40001",
        "dst_ap": "198.51.100.7:80",
    },
}


def test_request_id_matches_the_ingest_pipeline():
    assert (
        request_id(ALERT)
        == "638f9d635829210b48e40617c66d3cc0c5a6be7feffa52126dcb8e3c8bf91689"
    )


def test_request_id_is_none_when_a_key_field_is_missing():
    assert request_id({**ALERT, "snort": {**ALERT["snort"], "thread": None}}) is None
    assert request_id({"snort": ALERT["snort"]}) is None


@pytest.mark.parametrize(
    "stored, expected",
    [
        (base64.b64encode(b"GET /a%00b HTTP/1.1").decode(), "GET /a%00b HTTP/1.1"),
        (base64.b64encode(b"GET /\xff HTTP/1.1").decode(), "GET /� HTTP/1.1"),
        ("not base64!", None),
        (None, None),
    ],
)
def test_decode_request_line(stored, expected):
    assert decode_request_line(stored) == expected
