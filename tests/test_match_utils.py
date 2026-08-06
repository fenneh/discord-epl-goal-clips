"""Tests for match notification utilities."""

from datetime import datetime, timezone

import pytest

from src.utils.match_utils import (
    format_match_date_uk,
    format_match_time_uk,
    get_current_uk_time,
    get_today_uk_date_str,
    map_espn_team_to_config,
)


@pytest.mark.parametrize(
    "utc_str,expected",
    [
        ("2026-01-01T15:00Z", "15:00"),  # GMT, no offset
        ("2026-07-01T15:00Z", "16:00"),  # BST, +1 offset
        ("2026-01-01T15:00+00:00", "15:00"),  # explicit offset instead of Z
    ],
)
def test_format_match_time_uk_converts_to_uk_time(utc_str, expected):
    assert format_match_time_uk(utc_str) == expected


@pytest.mark.parametrize("bad_input", ["not a date", "", None, "2026-13-99Z"])
def test_format_match_time_uk_returns_tbd_on_bad_input(bad_input):
    assert format_match_time_uk(bad_input) == "TBD"


@pytest.mark.parametrize(
    "utc_str,expected",
    [
        ("2026-01-01T15:00Z", "1 Jan 2026"),
        ("2026-07-04T15:00Z", "4 Jul 2026"),
    ],
)
def test_format_match_date_uk_formats_date(utc_str, expected):
    assert format_match_date_uk(utc_str) == expected


@pytest.mark.parametrize("bad_input", ["not a date", "", None])
def test_format_match_date_uk_returns_unknown_on_bad_input(bad_input):
    assert format_match_date_uk(bad_input) == "Unknown Date"


def test_get_current_uk_time_is_close_to_now():
    now = datetime.now(timezone.utc)
    uk_time = get_current_uk_time()
    assert abs((uk_time.astimezone(timezone.utc) - now).total_seconds()) < 5


def test_get_today_uk_date_str_matches_current_uk_time():
    assert get_today_uk_date_str() == get_current_uk_time().strftime("%Y-%m-%d")


def test_map_espn_team_to_config_matches_canonical_name():
    result = map_espn_team_to_config("Arsenal")
    assert result["name"] == "Arsenal"
    assert result["data"]["color"] == 0xFF0000


def test_map_espn_team_to_config_matches_alias():
    result = map_espn_team_to_config("The Gunners")
    assert result["name"] == "Arsenal"


def test_map_espn_team_to_config_is_case_insensitive():
    result = map_espn_team_to_config("arsenal")
    assert result["name"] == "Arsenal"


def test_map_espn_team_to_config_returns_none_for_unknown_team():
    assert map_espn_team_to_config("Real Madrid") is None


@pytest.mark.parametrize("bad_input", [None, ""])
def test_map_espn_team_to_config_returns_none_for_empty_input(bad_input):
    assert map_espn_team_to_config(bad_input) is None
