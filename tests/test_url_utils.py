"""Tests for URL domain parsing utilities."""

import pytest

from src.utils.url_utils import get_base_domain, get_domain_info


@pytest.mark.parametrize(
    "url,expected_domain,expected_base",
    [
        ("https://streamable.com/abc123", "streamable.com", "streamable"),
        ("https://www.streamable.com/abc123", "streamable.com", "streamable"),
        ("https://streamff.com/v/xyz", "streamff.com", "streamff"),
        ("https://STREAMABLE.com/ABC", "streamable.com", "streamable"),
        ("https://example.com/video", "example.com", None),
    ],
)
def test_get_domain_info_matches_known_hosts(url, expected_domain, expected_base):
    result = get_domain_info(url)
    assert result == {"full_domain": expected_domain, "matched_base": expected_base}


@pytest.mark.parametrize("bad_url", [None, "", 123, [], {}])
def test_get_domain_info_rejects_non_string_or_empty(bad_url):
    assert get_domain_info(bad_url) is None


def test_get_domain_info_returns_none_when_no_domain_found():
    assert get_domain_info("not a url at all") is None


def test_get_base_domain_strips_www():
    assert get_base_domain("https://www.streamable.com/abc") == "streamable.com"


def test_get_base_domain_returns_full_domain_when_no_match():
    assert get_base_domain("https://example.com/video") == "example.com"


def test_get_base_domain_falls_back_to_original_url_on_parse_error():
    assert get_base_domain(None) is None
