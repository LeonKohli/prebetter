"""
Client address behind a proxy, read from the HTTP header block Snort captured
(`snort.b64_data`: header lines separated by CRLF, starting at `Host:`).

The header is supplied by the client or by any proxy on the way, so the result is
advisory. Header names are matched only at the start of a line, case-insensitively.
"""

import base64
import binascii
import ipaddress

from app.schemas.alerts import ForwardedInfo


def _header_values(lines: list[str], name: str) -> list[str]:
    prefix = f"{name.lower()}:"
    return [
        line[len(prefix) :].strip()
        for line in lines
        if line[: len(prefix)].lower() == prefix
    ]


def _parse_ip(token: str) -> str | None:
    """IPv4, IPv4:port, IPv6, or [IPv6] with optional :port; None for anything else."""
    token = token.strip().strip('"')
    if token.startswith("["):
        token = token[1:].partition("]")[0]
    elif token.count(":") == 1:
        token = token.partition(":")[0]
    try:
        return str(ipaddress.ip_address(token))
    except ValueError:
        return None


def forwarded_info(payload: str | None) -> ForwardedInfo | None:
    if payload is None:
        return None
    try:
        raw = base64.b64decode(payload, validate=True)
    except binascii.Error:  # the binary field type indexes invalid base64 as given
        return None
    text = raw.decode("utf-8", errors="replace")
    lines = [line.removesuffix("\r") for line in text.split("\n")]

    tokens = ",".join(_header_values(lines, "X-Forwarded-For")).split(",")
    chain = [ip for ip in map(_parse_ip, tokens) if ip]
    if not chain:
        return None

    # Right to left: the entry nearest to us was added by our own proxy, so a client
    # cannot hide behind addresses it prepends.
    true_source = next(
        (ip for ip in reversed(chain) if ipaddress.ip_address(ip).is_global), chain[-1]
    )
    via = _header_values(lines, "Via")
    return ForwardedInfo(
        true_source=true_source, forwarded_for=chain, via_proxy=via[0] if via else None
    )
