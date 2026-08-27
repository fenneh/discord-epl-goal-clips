"""Tests for post title filtering and ESPN coverage dedup logic."""

import pytest

from src.main import check_espn_covered_goal, contains_excluded_term, contains_goal_keyword


@pytest.mark.parametrize(
    "title",
    [
        "Salah [1] - 0 Arsenal",
        "Arsenal 0 - [1] Salah",
        "Arsenal [1-0] Liverpool",
        "Mexico 1-0 South Africa - Quinones 9'",
        "What a strike from Rashford!",
        "Header goal by Haaland",
        "Red card for the defender",
        "Second yellow card shown",
        "GOOOAL ⚽",
    ],
)
def test_contains_goal_keyword_matches_goal_titles(title):
    assert contains_goal_keyword(title) is True


@pytest.mark.parametrize(
    "title",
    [
        "Arsenal vs Liverpool - Match Thread",
        "Pre-season friendly announced",
        "Transfer news roundup",
    ],
)
def test_contains_goal_keyword_rejects_non_goal_titles(title):
    assert contains_goal_keyword(title) is False


@pytest.mark.parametrize(
    "title",
    [
        "Arsenal vs Liverpool: Pre Match Thread",
        "Arsenal vs Liverpool: Pre-Match Thread",
        "Match Thread: Arsenal vs Liverpool",
        "Post Match Thread: Arsenal 2-1 Liverpool",
        "Post-Match Thread: Arsenal 2-1 Liverpool",
        "Half Time: Arsenal 1-0 Liverpool",
        "Full Time: Arsenal 2-1 Liverpool",
        "This is a test",
    ],
)
def test_contains_excluded_term_matches_excluded_titles(title):
    assert contains_excluded_term(title) is True


@pytest.mark.parametrize(
    "title",
    [
        "Arsenal [1] - 0 Liverpool",
        "Contest winner announced",
        "Testosterone joke thread",
    ],
)
def test_contains_excluded_term_does_not_match_word_fragments(title):
    assert contains_excluded_term(title) is False


def test_check_espn_covered_goal_returns_false_when_no_data(monkeypatch):
    import src.main as main

    monkeypatch.setattr(main, "load_data", lambda *args, **kwargs: {})
    goal_info = {"team1": "Arsenal", "team2": "Liverpool", "minute": "10"}
    assert check_espn_covered_goal(goal_info) is False


def test_check_espn_covered_goal_returns_false_for_empty_goal_info():
    assert check_espn_covered_goal({}) is False
    assert check_espn_covered_goal(None) is False


def test_check_espn_covered_goal_matches_within_two_minutes(monkeypatch):
    import src.main as main

    covered = {"EPL:Arsenal_vs_Liverpool_11": "2026-01-01T15:00Z"}
    monkeypatch.setattr(main, "load_data", lambda *args, **kwargs: covered)
    goal_info = {"team1": "Arsenal", "team2": "Liverpool", "minute": "10"}
    assert check_espn_covered_goal(goal_info, competition_id="EPL") is True


def test_check_espn_covered_goal_ignores_goals_outside_tolerance(monkeypatch):
    import src.main as main

    covered = {"EPL:Arsenal_vs_Liverpool_20": "2026-01-01T15:00Z"}
    monkeypatch.setattr(main, "load_data", lambda *args, **kwargs: covered)
    goal_info = {"team1": "Arsenal", "team2": "Liverpool", "minute": "10"}
    assert check_espn_covered_goal(goal_info, competition_id="EPL") is False


def test_check_espn_covered_goal_handles_stoppage_time_minute(monkeypatch):
    import src.main as main

    covered = {"EPL:Arsenal_vs_Liverpool_45": "2026-01-01T15:00Z"}
    monkeypatch.setattr(main, "load_data", lambda *args, **kwargs: covered)
    goal_info = {"team1": "Arsenal", "team2": "Liverpool", "minute": "45+2"}
    assert check_espn_covered_goal(goal_info, competition_id="EPL") is True


def test_check_espn_covered_goal_returns_false_for_different_teams(monkeypatch):
    import src.main as main

    covered = {"EPL:Arsenal_vs_Liverpool_10": "2026-01-01T15:00Z"}
    monkeypatch.setattr(main, "load_data", lambda *args, **kwargs: covered)
    goal_info = {"team1": "Chelsea", "team2": "Liverpool", "minute": "10"}
    assert check_espn_covered_goal(goal_info, competition_id="EPL") is False
