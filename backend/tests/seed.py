"""
Synthetic alert events shaped to exercise the adapter: several address pairs, one rule
name shared by two rule ids, all four severity labels (priorities 0 to 4), one event
without addresses, one IPv6 pair and two sensors, spread over two daily indices.

The test suite seeds a node with this data. For manual work against a local node:

    uv run python -m tests.seed
"""

import base64
import hashlib
import json
from datetime import datetime, timedelta, UTC
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from opensearchpy import OpenSearch

from app.opensearch.request_line import request_id

TEMPLATE = json.loads((Path(__file__).parent / "index_template.json").read_text())
REQUEST_TEMPLATE = json.loads(
    (Path(__file__).parent / "requests_template.json").read_text()
)
TEST_BASE = datetime(2026, 11, 10, 12, 0, tzinfo=UTC)

# Header block as Snort logs it, followed by four non-printable bytes. The chain ends in a
# private proxy hop, so the true source is the public address before it.
PAYLOAD = base64.b64encode(
    b"Host: www.example.org\r\nUser-Agent: curl/8.7.1\r\n"
    b"X-Forwarded-For: 8.8.4.4, 10.0.0.1\r\nVia: 1.1 proxy.example\r\n"
    b"Accept: */*\r\n\x00\x01\xfe\xff"
).decode()

# Request line of event 1, as the ingest pipeline stores it (base64 of the bytes).
REQUEST_LINE = "GET /seed?q=1 OR 1=1 HTTP/1.1"

# rule key -> (rule.id, rule.name, rule.category)
RULES = {
    "A": ("1:1001", "Alpha scan", "Attempted Recon"),
    "B": ("1:1002", "Beta exploit", "Attempted Admin"),
    "C": ("1:1003", "Alpha scan", "Attempted Recon"),  # same name as A, other id
    "D": ("1:1004", "Delta info", "Misc Activity"),
}

# n -> (minutes before base, source, destination, rule, priority, sensor)
EVENTS = {
    1: (60, "192.0.2.10", "198.51.100.7", "A", 1, "s01"),
    2: (90, "192.0.2.10", "198.51.100.7", "C", 1, "s01"),
    3: (120, "192.0.2.10", "198.51.100.7", "B", 0, "s01"),
    4: (180, "192.0.2.20", "198.51.100.7", "B", 2, "s02"),
    5: (240, "192.0.2.20", "198.51.100.8", "D", 4, "s02"),
    6: (300, "203.0.113.5", "198.51.100.7", "A", 3, "s01"),
    7: (360, None, None, "D", 3, "s02"),
    8: (420, "2001:db8::1", "2001:db8::2", "B", 2, "s01"),
    9: (750, "192.0.2.10", "198.51.100.7", "A", 1, "s02"),
    10: (840, "192.0.2.20", "198.51.100.7", "A", 3, "s02"),
    11: (1440, "203.0.113.5", "198.51.100.9", "D", 4, "s01"),
    12: (1500, "192.0.2.10", "198.51.100.8", "A", 2, "s01"),
}


def event_id(n: int, base: datetime = TEST_BASE) -> str:
    return hashlib.sha256(f"event-{n}-{base.isoformat()}".encode()).hexdigest()


def build_event(n: int, base: datetime) -> dict[str, Any]:
    minutes, source, destination, rule, priority, sensor = EVENTS[n]
    timestamp = (base - timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%SZ")
    rule_id, rule_name, category = RULES[rule]
    doc: dict[str, Any] = {
        "@timestamp": timestamp,
        "event": {
            "id": event_id(n, base),
            "kind": "alert",
            "module": "snort",
            "severity": priority,
            "action": "would_block",
            "original": json.dumps({"msg": rule_name, "priority": priority, "n": n}),
        },
        "rule": {
            "id": rule_id,
            "name": rule_name,
            "category": category,
            "version": "4",
        },
        "observer": {
            "name": sensor,
            "type": "ids",
            "ingress": {"interface": {"name": "eth0"}},
        },
    }
    if source and destination:
        doc["source"] = {"ip": source, "port": 40000 + n}
        doc["destination"] = {"ip": destination, "port": 25}
    if n == 1:
        doc["source"]["mac"] = "02:00:00:00:00:01"
        doc["network"] = {
            "transport": "tcp",
            "protocol": "smtp",
            "vlan": {"id": "100"},
            "bytes": 2048,
            "packets": 12,
        }
        flow_start = base - timedelta(minutes=minutes, seconds=7)
        doc["event"]["start"] = flow_start.strftime("%Y-%m-%dT%H:%M:%SZ")
        doc["client"] = {"bytes": 1536, "packets": 8}
        doc["server"] = {"bytes": 512, "packets": 4}
        doc["snort"] = {
            "dir": "C2S",
            "iface": "eth0",
            "thread": "3",
            "timestamp": "11/10-11:00:00.000000",
            "rule": f"{rule_id}:4",
            "src_ap": f"{source}:{40000 + n}",
            "dst_ap": f"{destination}:25",
            "pkt_gen": "raw",
            "pkt_len": 60,
            "ip": {"ttl": 64},
            "tcp": {"flags": "AP"},
            "b64_data": PAYLOAD,
        }
    return doc


def build_request(event: dict[str, Any]) -> dict[str, Any]:
    """Companion document of an HTTP alert, with the identity fields copied from it."""
    snort = event["snort"]
    return {
        "@timestamp": event["@timestamp"],
        "observer": {
            "name": event["observer"]["name"],
            "ingress": event["observer"]["ingress"],
        },
        "snort": {
            **{
                k: snort[k] for k in ("thread", "timestamp", "rule", "src_ap", "dst_ap")
            },
            "http_request": base64.b64encode(REQUEST_LINE.encode()).decode(),
        },
    }


def _index_name(pattern: str, doc: dict[str, Any]) -> str:
    day = doc["@timestamp"][:10].replace("-", ".")
    return pattern.replace("*", day)


def _create(client: OpenSearch, indices: list[str], template: dict[str, Any]) -> None:
    for index in indices:
        if not client.indices.exists(index=index):
            client.indices.create(index=index, body=template)


def seed(
    client: OpenSearch, pattern: str, request_pattern: str, base: datetime = TEST_BASE
) -> list[str]:
    """Create one index per UTC day from the production templates; index the events and
    the request companion of event 1. Returns the names of all indices created."""
    docs = [build_event(n, base) for n in EVENTS]
    indices = sorted({_index_name(pattern, doc) for doc in docs})
    _create(client, indices, TEMPLATE)
    for doc in docs:
        client.index(index=_index_name(pattern, doc), id=doc["event"]["id"], body=doc)

    request = build_request(docs[0])
    request_index = _index_name(request_pattern, request)
    _create(client, [request_index], REQUEST_TEMPLATE)
    # The id is the app's own, so a change of the key breaks the lookup test.
    client.index(index=request_index, id=request_id(docs[0]), body=request)
    client.indices.refresh(index=[*indices, request_index])
    return [*indices, request_index]


def main() -> None:
    from app.core.config import get_settings

    settings = get_settings()
    if urlparse(settings.OPENSEARCH_URL).hostname not in ("localhost", "127.0.0.1"):
        raise SystemExit("Refusing to seed: OPENSEARCH_URL is not a local node")
    # Whole hours keep a repeated run idempotent: the same events get the same ids.
    base = datetime.now(UTC).replace(minute=0, second=0, microsecond=0)
    client = OpenSearch(hosts=[settings.OPENSEARCH_URL])
    indices = seed(
        client, settings.OPENSEARCH_INDEX, settings.OPENSEARCH_REQUEST_INDEX, base
    )
    print(f"Seeded {len(EVENTS)} events and one request line into {', '.join(indices)}")


if __name__ == "__main__":
    main()
