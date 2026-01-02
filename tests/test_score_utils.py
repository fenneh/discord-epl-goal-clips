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
