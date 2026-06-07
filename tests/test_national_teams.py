"""Tests for national team alias normalisation and detection."""

import pytest

from src.config.competitions import WORLD_CUP_2026
from src.services.reddit_service import find_team_in_title
from src.utils.score_utils import normalize_team_name


@pytest.mark.parametrize(
    "input_name,expected",
    [
        ("USA", "united states"),
        ("United States", "united states"),
        ("U.S.A.", "united states"),
        ("USMNT", "united states"),
        ("South Korea", "south korea"),
        ("Korea Republic", "south korea"),
        ("S. Korea", "south korea"),
        ("Netherlands", "netherlands"),
        ("Holland", "netherlands"),
        ("Oranje", "netherlands"),
        ("Ivory Coast", "ivory coast"),
        ("Cote d'Ivoire", "ivory coast"),
        ("Czechia", "czechia"),
        ("Czech Republic", "czechia"),
        ("Republic of Ireland", "republic of ireland"),
        ("Ireland", "republic of ireland"),
        ("United Arab Emirates", "united arab emirates"),
        ("UAE", "united arab emirates"),
        ("DR Congo", "dr congo"),
        ("Democratic Republic of the Congo", "dr congo"),
        ("Iran", "iran"),
        ("IR Iran", "iran"),
        ("Turkey", "turkey"),
        ("Türkiye", "turkey"),
        ("Cape Verde", "cape verde"),
        ("Cabo Verde", "cape verde"),
    ],
)
def test_national_team_alias_normalization(input_name: str, expected: str):
    assert normalize_team_name(input_name) == expected


def test_find_usa_via_alias():
    result = find_team_in_title(
        "USMNT [1] - 0 Mexico - Pulisic 30'", include_metadata=True
    )
    assert result is not None
    assert isinstance(result, dict)
    assert result["name"] == "USA"
    assert result["competition"].id == WORLD_CUP_2026.id


def test_find_south_korea_via_alias():
    result = find_team_in_title(
        "South Korea [2] - 1 Japan - Son 78'", include_metadata=True
    )
    assert result is not None
    assert isinstance(result, dict)
    assert result["name"] == "South Korea"


def test_find_team_with_native_name():
    result = find_team_in_title(
        "Cote d'Ivoire [1] - 0 Cameroon - Haller 60'", include_metadata=True
    )
    assert result is not None
    assert isinstance(result, dict)
    assert result["name"] == "Ivory Coast"


def test_epl_match_not_misattributed_to_world_cup():
    """Arsenal isn't a national team — EPL must win the match."""
    result = find_team_in_title(
        "Arsenal [1] - 0 Tottenham - Saka 45'", include_metadata=True
    )
    assert result is not None
    assert isinstance(result, dict)
    assert result["competition"].id == "epl"


@pytest.mark.parametrize(
    "title,expected_name",
    [
        ("Bosnia [1] - 0 Germany - Dzeko 23'", "Bosnia-Herzegovina"),
        ("Bosnia-Herzegovina 0 - [1] Spain - Yamal 67'", "Spain"),
        ("Curacao [1] - 0 USA - Bacuna 45'", "Curaçao"),
        ("Curaçao [1] - 0 Panama - Bacuna 45'", "Curaçao"),
        ("Haiti 1 - [2] Canada - David 80'", "Canada"),
        ("Mexico [1] - 0 Haiti - Vega 12'", "Mexico"),
    ],
)
def test_late_qualifier_detection(title: str, expected_name: str):
    """Bosnia, Curaçao, Haiti were surprise qualifiers — confirm they're tracked."""
    result = find_team_in_title(title, include_metadata=True)
    assert result is not None
    assert isinstance(result, dict)
    assert result["name"] == expected_name


@pytest.mark.parametrize(
    "espn_form,reddit_form",
    [
        # ESPN's display name (left) and a Reddit variant (right) must
        # collapse to the same normalised form for cross-source dedup.
        ("Congo DR", "DR Congo"),
        ("Türkiye", "Turkey"),
        ("United States", "USA"),
        ("Bosnia-Herzegovina", "Bosnia"),
        ("Curaçao", "Curacao"),
        ("Netherlands", "Nederland"),
        ("Netherlands", "Holland"),
        ("Belgium", "België"),
        ("Switzerland", "Schweiz"),
        ("Austria", "Österreich"),
        ("Iran", "Persia"),
        ("Czechia", "Česko"),
        ("Japan", "Nippon"),
        ("Wales", "Cymru"),
    ],
)
def test_espn_reddit_name_normalisation_matches(espn_form: str, reddit_form: str):
    """ESPN's display name and Reddit's variant must normalise identically
    so a goal posted in both sources hits the same dedup key."""
    assert normalize_team_name(espn_form) == normalize_team_name(reddit_form)
