import base64

import pytest

from app.opensearch.forwarded import forwarded_info

H = "Host: a.example\r\nUser-Agent: curl/8\r\n"
XFF = "X-Forwarded-For: "

# name -> (header block, true source, chain, via)
CASES = {
    "single global": (H + XFF + "8.8.4.4\r\n", "8.8.4.4", ["8.8.4.4"], None),
    "private hop last": (
        H + XFF + "8.8.4.4, 10.0.0.1\r\n",
        "8.8.4.4",
        ["8.8.4.4", "10.0.0.1"],
        None,
    ),
    "prepended spoof is ignored": (
        H + XFF + "6.6.6.6, 8.8.4.4, 10.1.1.1\r\n",
        "8.8.4.4",
        ["6.6.6.6", "8.8.4.4", "10.1.1.1"],
        None,
    ),
    "only private takes the last": (
        H + XFF + "10.0.0.5, 192.168.1.2\r\n",
        "192.168.1.2",
        ["10.0.0.5", "192.168.1.2"],
        None,
    ),
    "documentation range is not global": (
        H + XFF + "203.0.113.9\r\n",
        "203.0.113.9",
        ["203.0.113.9"],
        None,
    ),
    "ipv6": (
        H + XFF + "2606:4700:4700::1111, fd00::1\r\n",
        "2606:4700:4700::1111",
        ["2606:4700:4700::1111", "fd00::1"],
        None,
    ),
    "ipv6 uncompressed is normalized": (
        H + XFF + "2606:4700:4700:0:0:0:0:1111\r\n",
        "2606:4700:4700::1111",
        ["2606:4700:4700::1111"],
        None,
    ),
    "ipv4 with port": (
        H + XFF + "8.8.4.4:5555, 10.0.0.1\r\n",
        "8.8.4.4",
        ["8.8.4.4", "10.0.0.1"],
        None,
    ),
    "bracketed ipv6 with port": (
        H + XFF + '"[2606:4700:4700::1111]:443", [fd00::1]\r\n',
        "2606:4700:4700::1111",
        ["2606:4700:4700::1111", "fd00::1"],
        None,
    ),
    "invalid tokens are skipped": (
        H + XFF + "unknown, 8.8.4.4, 999.1.1.1, 10.0.0.1\r\n",
        "8.8.4.4",
        ["8.8.4.4", "10.0.0.1"],
        None,
    ),
    "via": (
        H + XFF + "8.8.4.4\r\nVia: 1.1 proxy1\r\n",
        "8.8.4.4",
        ["8.8.4.4"],
        "1.1 proxy1",
    ),
    "several header lines form one chain": (
        H + XFF + "6.6.6.6\r\n" + XFF + "8.8.4.4\r\n",
        "8.8.4.4",
        ["6.6.6.6", "8.8.4.4"],
        None,
    ),
    "header name is case-insensitive": (
        H + "x-forwarded-for: 8.8.4.4\r\nVIA: 1.1 proxy1\r\n",
        "8.8.4.4",
        ["8.8.4.4"],
        "1.1 proxy1",
    ),
    "text inside another header's value is not a header": (
        "Host: a.example\r\nReferer: http://x.example/?q=X-Forwarded-For: 6.6.6.6\r\n"
        + XFF
        + "8.8.4.4\r\nX-Note: Via: 1.1 fake\r\n",
        "8.8.4.4",
        ["8.8.4.4"],
        None,
    ),
    "binary tail does not matter": (
        H + XFF + "8.8.4.4\r\n\x00\x01\xfe\xff",
        "8.8.4.4",
        ["8.8.4.4"],
        None,
    ),
}


def b64(text: str) -> str:
    return base64.b64encode(text.encode("latin-1")).decode()


@pytest.mark.parametrize("block, true_source, chain, via", CASES.values(), ids=CASES)
def test_forwarded_info(block, true_source, chain, via):
    info = forwarded_info(b64(block))

    assert info is not None
    assert (info.true_source, info.forwarded_for, info.via_proxy) == (
        true_source,
        chain,
        via,
    )


@pytest.mark.parametrize(
    "payload",
    [None, b64(H), b64(H + XFF + "unknown\r\n"), "not base64 !!"],
    ids=["no payload", "no header", "no valid address", "invalid base64"],
)
def test_forwarded_info_is_none_without_a_client_address(payload):
    assert forwarded_info(payload) is None
