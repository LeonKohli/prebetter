import pytest
from pydantic import ValidationError

from app.schemas.filters import (
    parse_ip_filter,
    IPRange,
    AlertFilterParams,
)


class TestParseIPFilter:
    def test_single_ipv4_address(self):
        result = parse_ip_filter("192.168.1.100")
        assert result.is_cidr is False
        assert result.original == "192.168.1.100"
        assert result.network_int == result.broadcast_int
        assert result.network_int == 0xC0A80164

    def test_cidr_class_c_network(self):
        result = parse_ip_filter("192.168.1.0/24")
        assert result.is_cidr is True
        assert result.original == "192.168.1.0/24"
        assert result.network_int == 0xC0A80100
        assert result.broadcast_int == 0xC0A801FF

    def test_cidr_class_b_network(self):
        result = parse_ip_filter("172.16.0.0/12")
        assert result.is_cidr is True
        assert result.network_int == 0xAC100000
        assert result.broadcast_int == 0xAC1FFFFF

    def test_cidr_class_a_network(self):
        result = parse_ip_filter("10.0.0.0/8")
        assert result.is_cidr is True
        assert result.network_int == 0x0A000000
        assert result.broadcast_int == 0x0AFFFFFF

    def test_cidr_single_host(self):
        result = parse_ip_filter("192.168.1.100/32")
        assert result.is_cidr is True
        assert result.network_int == result.broadcast_int
        assert result.network_int == 0xC0A80164

    def test_cidr_non_aligned_network(self):
        result = parse_ip_filter("192.168.1.50/24")
        assert result.is_cidr is True
        assert result.network_int == 0xC0A80100
        assert result.broadcast_int == 0xC0A801FF

    def test_invalid_ipv4_address(self):
        with pytest.raises(ValueError, match="Invalid IPv4 address"):
            parse_ip_filter("999.999.999.999")

    def test_invalid_cidr_notation(self):
        with pytest.raises(ValueError, match="Invalid CIDR notation"):
            parse_ip_filter("192.168.1.0/33")

    def test_invalid_cidr_format(self):
        with pytest.raises(ValueError, match="Invalid CIDR notation"):
            parse_ip_filter("192.168.1.0/abc")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_ip_filter("")

    def test_whitespace_handling(self):
        result = parse_ip_filter("  192.168.1.100  ")
        assert result.original == "192.168.1.100"
        assert result.is_cidr is False


class TestIPRange:
    def test_ip_range_is_frozen(self):
        ip_range = IPRange(
            network_int=100,
            broadcast_int=200,
            is_cidr=True,
            original="test",
            expanded="test",
        )
        with pytest.raises(AttributeError):
            ip_range.network_int = 999

    def test_ip_in_range_check(self):
        ip_range = parse_ip_filter("192.168.1.0/24")
        test_ip = 0xC0A80132
        assert ip_range.network_int <= test_ip <= ip_range.broadcast_int


class TestPartialIPExpansion:
    def test_single_octet_expands_to_class_a(self):
        result = parse_ip_filter("10")
        assert result.is_cidr is True
        assert result.original == "10"
        assert result.expanded == "10.0.0.0 - 10.255.255.255"
        assert result.network_int == 0x0A000000
        assert result.broadcast_int == 0x0AFFFFFF

    def test_two_octets_expands_to_class_b(self):
        result = parse_ip_filter("192.168")
        assert result.is_cidr is True
        assert result.original == "192.168"
        assert result.expanded == "192.168.0.0 - 192.168.255.255"
        assert result.network_int == 0xC0A80000
        assert result.broadcast_int == 0xC0A8FFFF

    def test_three_octets_expands_to_class_c(self):
        result = parse_ip_filter("10.128.9")
        assert result.is_cidr is True
        assert result.original == "10.128.9"
        assert result.expanded == "10.128.9.0 - 10.128.9.255"
        assert result.network_int == 0x0A800900
        assert result.broadcast_int == 0x0A8009FF

    def test_full_ip_not_expanded(self):
        result = parse_ip_filter("192.168.1.100")
        assert result.is_cidr is False
        assert result.original == "192.168.1.100"
        assert result.expanded == "192.168.1.100"

    def test_partial_ip_with_leading_zeros(self):
        result = parse_ip_filter("10.0.0")
        assert result.is_cidr is True
        assert result.expanded == "10.0.0.0 - 10.0.0.255"

    def test_partial_ip_boundary_values(self):
        result = parse_ip_filter("255.255")
        assert result.is_cidr is True
        assert result.expanded == "255.255.0.0 - 255.255.255.255"

    def test_cidr_has_expanded_field(self):
        result = parse_ip_filter("192.168.1.0/24")
        assert result.expanded == "192.168.1.0 - 192.168.1.255"

    def test_partial_ip_invalid_octet_fails(self):
        with pytest.raises(ValueError):
            parse_ip_filter("10.256.9")

    def test_partial_ip_non_numeric_fails(self):
        with pytest.raises(ValueError):
            parse_ip_filter("10.abc.9")


class TestAlertFilterParamsIPValidation:
    def test_valid_single_source_ip(self):
        params = AlertFilterParams(source_ip="192.168.1.100")
        assert params.source_ip == "192.168.1.100"
        ip_range = params.source_ip_range()
        assert ip_range is not None
        assert ip_range.is_cidr is False

    def test_valid_cidr_source_ip(self):
        params = AlertFilterParams(source_ip="10.0.0.0/8")
        assert params.source_ip == "10.0.0.0/8"
        ip_range = params.source_ip_range()
        assert ip_range is not None
        assert ip_range.is_cidr is True

    def test_valid_single_target_ip(self):
        params = AlertFilterParams(target_ip="10.0.0.1")
        assert params.target_ip == "10.0.0.1"
        ip_range = params.target_ip_range()
        assert ip_range is not None
        assert ip_range.is_cidr is False

    def test_valid_cidr_target_ip(self):
        params = AlertFilterParams(target_ip="172.16.0.0/12")
        assert params.target_ip == "172.16.0.0/12"
        ip_range = params.target_ip_range()
        assert ip_range is not None
        assert ip_range.is_cidr is True

    def test_invalid_source_ip_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AlertFilterParams(source_ip="invalid-ip")

    def test_invalid_target_ip_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AlertFilterParams(target_ip="256.256.256.256")

    def test_invalid_cidr_raises_validation_error(self):
        with pytest.raises(ValidationError):
            AlertFilterParams(source_ip="192.168.1.0/33")

    def test_none_ip_returns_none_range(self):
        params = AlertFilterParams()
        assert params.source_ip_range() is None
        assert params.target_ip_range() is None

    def test_combined_source_and_target(self):
        params = AlertFilterParams(
            source_ip="192.168.0.0/16",
            target_ip="10.0.0.1",
        )
        source_range = params.source_ip_range()
        target_range = params.target_ip_range()

        assert source_range is not None
        assert source_range.is_cidr is True
        assert target_range is not None
        assert target_range.is_cidr is False
