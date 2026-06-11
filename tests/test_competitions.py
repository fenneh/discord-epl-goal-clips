"""Tests for the competition registry, multi-competition team lookup and
competition-prefixed canonical keys."""


from src.config.competitions import (
    EPL,
    WORLD_CUP_2026,
    get_competition,
    list_competitions,
)
from src.config.teams import get_teams_for_competition
from src.services.reddit_service import find_team_in_title
from src.utils.score_utils import (
    extract_goal_info,
    generate_canonical_key,
    is_duplicate_score,
    migrate_legacy_scores,
)


def test_registry_has_epl_and_world_cup():
    ids = {c.id for c in list_competitions()}
    assert {"epl", "world_cup_2026"} <= ids


def test_get_competition_lookup():
    assert get_competition("epl") is EPL
    assert get_competition("world_cup_2026") is WORLD_CUP_2026


def test_epl_competition_fields():
    assert EPL.espn_league == "epl"
    assert EPL.schedule_title == "Premier League"


def test_world_cup_competition_fields():
    assert WORLD_CUP_2026.espn_league == "world_cup"
    assert WORLD_CUP_2026.schedule_title == "World Cup"


def test_teams_dict_lookup_by_competition_id():
    epl_teams = get_teams_for_competition(EPL.id)
    wc_teams = get_teams_for_competition(WORLD_CUP_2026.id)
    assert "Arsenal" in epl_teams
    assert "USA" in wc_teams
    assert "Arsenal" not in wc_teams
    assert "USA" not in epl_teams


def test_find_team_in_title_returns_epl_competition():
    result = find_team_in_title(
        "Arsenal [2] - 0 Chelsea - Saka 45'", include_metadata=True
    )
    assert result is not None
    assert isinstance(result, dict)
    assert result["competition"].id == "epl"


def test_find_team_in_title_returns_world_cup_competition():
    result = find_team_in_title(
        "Argentina [1] - 0 Brazil - Messi 23'", include_metadata=True
    )
    assert result is not None
    assert isinstance(result, dict)
    assert result["competition"].id == "world_cup_2026"


def test_find_team_in_title_no_match():
    assert find_team_in_title("Some random title with no team", include_metadata=True) is None


def test_canonical_key_carries_competition_prefix():
    info = extract_goal_info("Argentina [1] - 0 Brazil - Messi 23'")
    assert info is not None
    key = generate_canonical_key(info, "world_cup_2026")
    assert key is not None
    assert key.startswith("world_cup_2026:")


def test_canonical_keys_do_not_collide_across_competitions():
    info = extract_goal_info("Arsenal [1] - 0 Chelsea - Saka 45'")
    assert info is not None
    epl_key = generate_canonical_key(info, "epl")
    wc_key = generate_canonical_key(info, "world_cup_2026")
    assert epl_key != wc_key


def test_is_duplicate_score_scoped_to_competition():
    from datetime import datetime, timezone

    title = "Arsenal [1] - 0 Chelsea - Saka 45'"
    posted = {}
    info = extract_goal_info(title)
    assert info is not None
    epl_key = generate_canonical_key(info, "epl")
    assert epl_key is not None
    posted[epl_key] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "url": "x",
        "reddit_url": "x",
        "original_title": title,
    }
    # Same fixture under a different competition is not a duplicate
    now = datetime.now(timezone.utc)
    assert is_duplicate_score(title, posted, now, competition_id="epl") is True
    assert (
        is_duplicate_score(title, posted, now, competition_id="world_cup_2026")
        is False
    )


def test_migrate_legacy_scores_adds_epl_prefix():
    legacy = {"arsenal_vs_chelsea_1-0_45": {"timestamp": "x"}}
    assert migrate_legacy_scores(legacy) is True
    assert "epl:arsenal_vs_chelsea_1-0_45" in legacy
    assert "arsenal_vs_chelsea_1-0_45" not in legacy


def test_migrate_legacy_scores_is_idempotent():
    already = {"epl:arsenal_vs_chelsea_1-0_45": {"timestamp": "x"}}
    assert migrate_legacy_scores(already) is False
    assert "epl:arsenal_vs_chelsea_1-0_45" in already
