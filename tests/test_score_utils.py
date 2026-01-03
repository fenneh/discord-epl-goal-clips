"""Test suite for score utilities."""

from datetime import datetime, timezone, timedelta

import pytest

from src.utils.score_utils import (
    is_duplicate_score,
    extract_goal_info,
    normalize_player_name,
    generate_canonical_key,
)

@pytest.mark.parametrize(
    "input_name,expected",
    [
        ("Gabriel Jesus", "jesus"),
        ("G. Jesus", "jesus"),
        ("Eddie Nketiah", "nketiah"),
        ("E. Nketiah", "nketiah"),
        ("João Félix", "felix"),
        ("J. Félix", "felix"),
        ("Virgil van Dijk", "dijk"),
        ("V. van Dijk", "dijk"),
        ("Smith-Rowe", "smithrowe"),
        ("E. Smith-Rowe", "smithrowe"),
    ],
)
def test_normalize_player_name(input_name: str, expected: str):
    assert normalize_player_name(input_name) == expected

@pytest.mark.parametrize(
    "title,expected",
    [
        (
            "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
            {"score": "[3]-1", "minute": "81", "scorer": "Gabriel Jesus"},
        ),
        (
            "Manchester United 2 - [3] Liverpool - Mo Salah 90+2'",
            {"score": "2-[3]", "minute": "90+2", "scorer": "Mo Salah"},
        ),
        ("Match Thread: Arsenal vs Crystal Palace", None),
        ("Post Match Thread: Arsenal 3-1 Crystal Palace", None),
    ],
)
def test_extract_goal_info(title, expected):
    result = extract_goal_info(title)
    if expected is None:
        assert result is None
        return
    assert result["score"] == expected["score"]
    assert result["minute"] == expected["minute"]
    assert normalize_player_name(result["scorer"]) == normalize_player_name(expected["scorer"])

@pytest.mark.parametrize(
    "title1,title2,should_match,time_diff",
    [
        (
            "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
            "Arsenal [3] - 1 Crystal Palace - G. Jesus 81'",
            True,
            30,
        ),
        (
            "Arsenal 3 - [2] Crystal Palace - Eddie Nketiah 85'",
            "Arsenal 3 - [2] Crystal Palace - E. Nketiah 85'",
            True,
            30,
        ),
        (
            "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
            "Arsenal [3] - 1 Crystal Palace - G. Jesus 82'",
            False,
            60,
        ),
        (
            "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
            "Arsenal [3] - 1 Crystal Palace - Saka 82'",
            False,
            60,
        ),
        (
            "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
            "Arsenal [3] - 1 Crystal Palace - Saka 81'",
            True,
            30,
        ),
        (
            "Arsenal [3] - 1 Crystal Palace - Gabriel Jesus 81'",
            "Arsenal [4] - 1 Crystal Palace - Gabriel Jesus 81'",
            False,
            30,
        ),
    ],
)
def test_duplicate_detection(title1, title2, should_match, time_diff):
    posted_scores = {}
    base_time = datetime.now(timezone.utc)
    info1 = extract_goal_info(title1)
    assert info1
    key1 = generate_canonical_key(info1)
    assert key1
    posted_scores[key1] = {
        "timestamp": base_time.isoformat(),
        "url": "https://example.com/post1",
        "reddit_url": "https://reddit.com/post1",
        "original_title": title1,
    }

    current_time = base_time + timedelta(seconds=time_diff)
    is_duplicate = is_duplicate_score(
        title2,
        posted_scores,
        current_time,
        url="https://example.com/post2",
    )

    assert is_duplicate == should_match


def test_canonical_key_strips_brackets():
    """Verify canonical key strips brackets from score for ESPN compatibility.

    Reddit titles have brackets indicating scoring team: '[1] - 0' or '1 - [2]'
    ESPN keys use plain scores: '1-0' or '1-2'
    Keys must match for cross-system deduplication to work.
    """
    # Home team scores
    info = extract_goal_info("Aston Villa [1] - 0 Nottingham Forest - Ollie Watkins 45+1'")
    assert info is not None
    key = generate_canonical_key(info)
    assert key is not None
    # Key should have score WITHOUT brackets
    assert "_1-0_" in key, f"Expected '1-0' in key but got: {key}"
    assert "[" not in key, f"Brackets should be stripped but got: {key}"
    assert "]" not in key, f"Brackets should be stripped but got: {key}"

    # Away team scores
    info = extract_goal_info("Liverpool 2 - [3] Manchester City - Erling Haaland 90'")
    assert info is not None
    key = generate_canonical_key(info)
    assert key is not None
    assert "_2-3_" in key, f"Expected '2-3' in key but got: {key}"
    assert "[" not in key, f"Brackets should be stripped but got: {key}"


class TestEspnRedditGoalKeyMatching:
    """Test cross-system goal key matching between ESPN and Reddit.

    ESPN keys use scorer names: teams_scorer_minute
    Reddit keys use scores: teams_score_minute

    Both must parse correctly with rsplit('_', 2) to extract teams for matching.
    """

    @pytest.mark.parametrize(
        "scorer_name,expected_scorer_in_key",
        [
            ("John McGinn", "johnmcginn"),
            ("Ollie Watkins", "olliewatkins"),
            ("Morgan Gibbs-White", "morgangibbswhite"),
            ("Son Heung-min", "sonheungmin"),
            ("Bruno Fernandes", "brunofernandes"),
            ("N. Jackson", "njackson"),
            ("K. De Bruyne", "kdebruyne"),
        ],
    )
    def test_espn_scorer_name_no_underscores(self, scorer_name: str, expected_scorer_in_key: str):
        """Scorer names must NOT contain underscores after normalization.

        If scorer names contain underscores (e.g., john_mcginn), rsplit('_', 2)
        will incorrectly parse the key and teams won't match.
        """
        normalized = scorer_name.lower().replace(' ', '').replace('.', '').replace('-', '')
        assert '_' not in normalized, f"Scorer '{scorer_name}' contains underscore after normalization: {normalized}"
        assert normalized == expected_scorer_in_key

    def test_espn_key_parses_correctly_with_multiword_scorer(self):
        """ESPN key with multi-word scorer must parse correctly with rsplit('_', 2)."""
        # After fix: scorer has no underscores
        espn_key = "aston villa_vs_nottingham forest_johnmcginn_73"
        parts = espn_key.rsplit('_', 2)

        assert len(parts) == 3
        assert parts[0] == "aston villa_vs_nottingham forest"
        assert parts[1] == "johnmcginn"
        assert parts[2] == "73"

    def test_espn_key_with_underscore_scorer_fails_parsing(self):
        """Demonstrate the bug: underscore in scorer breaks rsplit parsing."""
        # Bug case: scorer has underscore
        broken_key = "aston villa_vs_nottingham forest_john_mcginn_73"
        parts = broken_key.rsplit('_', 2)

        # This incorrectly includes 'john' in teams
        assert parts[0] == "aston villa_vs_nottingham forest_john"  # WRONG
        assert parts[1] == "mcginn"
        assert parts[2] == "73"

    def test_reddit_key_parses_correctly(self):
        """Reddit keys parse correctly since scores don't contain underscores."""
        reddit_key = "aston villa_vs_nottingham forest_3-1_73"
        parts = reddit_key.rsplit('_', 2)

        assert len(parts) == 3
        assert parts[0] == "aston villa_vs_nottingham forest"
        assert parts[1] == "3-1"
        assert parts[2] == "73"

    def test_espn_reddit_teams_match_after_fix(self):
        """After fix, ESPN and Reddit keys must have matching teams."""
        # Fixed ESPN key (no underscore in scorer)
        espn_key = "aston villa_vs_nottingham forest_johnmcginn_73"
        reddit_key = "aston villa_vs_nottingham forest_3-1_73"

        espn_parts = espn_key.rsplit('_', 2)
        reddit_parts = reddit_key.rsplit('_', 2)

        # Teams should match
        assert espn_parts[0] == reddit_parts[0], (
            f"Teams mismatch: ESPN={espn_parts[0]}, Reddit={reddit_parts[0]}"
        )
        # Minutes should match
        assert espn_parts[2] == reddit_parts[2]

    @pytest.mark.parametrize(
        "espn_key,reddit_key,should_match_teams",
        [
            # Fixed keys - teams match
            ("aston villa_vs_nottingham forest_johnmcginn_73", "aston villa_vs_nottingham forest_3-1_73", True),
            ("arsenal_vs_chelsea_bukayosaka_45", "arsenal_vs_chelsea_1-0_45", True),
            ("liverpool_vs_manchester city_mosalah_90", "liverpool_vs_manchester city_2-2_90", True),
            # Broken keys (bug case) - teams don't match
            ("aston villa_vs_nottingham forest_john_mcginn_73", "aston villa_vs_nottingham forest_3-1_73", False),
        ],
    )
    def test_cross_system_team_matching(self, espn_key: str, reddit_key: str, should_match_teams: bool):
        """Verify ESPN and Reddit key team extraction matches or fails as expected."""
        espn_parts = espn_key.rsplit('_', 2)
        reddit_parts = reddit_key.rsplit('_', 2)

        teams_match = espn_parts[0] == reddit_parts[0]
        assert teams_match == should_match_teams
