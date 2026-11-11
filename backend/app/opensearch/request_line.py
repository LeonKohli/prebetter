"""
HTTP request line of an alert. Snort's JSON alert cannot carry it, so the ingest pipeline
stores one companion document per HTTP alert in the request indices
(`OPENSEARCH_REQUEST_INDEX`) and keys it by a hash of the alert's identity.
"""

import base64
import binascii
import hashlib
from typing import Any

# Fields that identify an alert, in the order of the key. The ingest pipeline builds the
# same key: the SHA-256 (lowercase hex) of these values joined by "\n". Alert and companion
# carry identical values for all of them.
_KEY_FIELDS = (
    ("observer", "name"),
    ("observer", "ingress", "interface", "name"),
    ("snort", "thread"),
    ("snort", "timestamp"),
    ("snort", "rule"),
    ("snort", "src_ap"),
    ("snort", "dst_ap"),
)


def request_id(alert: dict[str, Any]) -> str | None:
    """`_id` of the alert's companion document; None when the alert lacks a key field."""
    values: list[str] = []
    for path in _KEY_FIELDS:
        value: Any = alert
        for key in path:
            value = value.get(key) if isinstance(value, dict) else None
        if not isinstance(value, str):
            return None
        values.append(value)
    return hashlib.sha256("\n".join(values).encode()).hexdigest()


def decode_request_line(stored: str | None) -> str | None:
    """Text of the stored base64 value; None when absent or not valid base64."""
    if stored is None:
        return None
    try:
        raw = base64.b64decode(stored, validate=True)
    except binascii.Error:  # the binary field type indexes invalid base64 as given
        return None
    return raw.decode("utf-8", errors="replace")
