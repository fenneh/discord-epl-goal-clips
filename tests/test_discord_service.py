"""Tests for Discord webhook service."""

import pytest
from datetime import datetime, timezone
from src.services.discord_service import clean_text, post_to_discord
from src.config.teams import premier_league_teams

@pytest.mark.parametrize("text,expected", [
    # Unicode control characters
    ("Arsenal\u200e vs Chelsea", "Arsenal vs Chelsea"),
    ("Man United\u200f 1-0", "Man United 1-0"),
    ("\u202aLiverpool\u202c", "Liverpool"),
    
    # Multiple control characters
    ("Arsenal\u200e\u200f vs Chelsea", "Arsenal vs Chelsea"),
    
    # No control characters
    ("Arsenal vs Chelsea", "Arsenal vs Chelsea"),
    ("", ""),
])
def test_clean_text(text: str, expected: str):
    """Test that text cleaning works correctly."""
    assert clean_text(text) == expected

@pytest.mark.asyncio
async def test_post_to_discord_pl_team():
    """Test Discord post creation for Premier League team."""
    content = "Arsenal [2] - 1 Chelsea"
    team_data = {
        "team": "Arsenal",
        "color": premier_league_teams["Arsenal"]["color"],
    }
    
    # Mock the actual post call but verify the embed structure
    embed = await post_to_discord(content, team_data)
    assert embed["title"] == "**Arsenal [2] - 1 Chelsea**"
    assert embed["color"] == premier_league_teams["Arsenal"]["color"]
    assert "thumbnail" in embed
    assert embed["thumbnail"]["url"] == premier_league_teams["Arsenal"]["logo"]

@pytest.mark.asyncio
async def test_post_to_discord_non_pl_team():
    """Test Discord post creation for non-Premier League team."""
    content = "Real Madrid [2] - 1 Barcelona"
    team_data = {
        "team": "Real Madrid",
        "color": 0x808080,  # Default gray
    }
    
    embed = await post_to_discord(content, team_data)
    assert embed["title"] == "**Real Madrid [2] - 1 Barcelona**"
    assert embed["color"] == 0x808080
    assert "thumbnail" not in embed

@pytest.mark.asyncio
async def test_post_to_discord_with_url():
    """Test Discord post creation with URL in content."""
    content = "Arsenal [2] - 1 Chelsea\nhttps://example.com/video"
    team_data = {"team": "Arsenal"}
    
    embed = await post_to_discord(content, team_data)
    assert "https://example.com/video" in embed["description"]

@pytest.mark.parametrize("team_name", premier_league_teams.keys())
@pytest.mark.asyncio
async def test_all_pl_teams_have_valid_logos(team_name: str):
    """Test that all Premier League teams have valid logo URLs."""
    team_data = {
        "team": team_name,
        "color": premier_league_teams[team_name]["color"],
    }
    
    embed = await post_to_discord(f"{team_name} [1] - 0 Test Team", team_data)
    assert "thumbnail" in embed
    assert embed["thumbnail"]["url"] == premier_league_teams[team_name]["logo"]
    assert embed["thumbnail"]["url"].startswith("https://resources.premierleague.com/")

def test_timestamp_format():
    """Test that timestamps are in correct ISO format."""
    content = "Test Content"
    embed = post_to_discord(content)
    timestamp = embed["timestamp"]
    
    # Should be able to parse as ISO format
    try:
        datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
    except ValueError:
        pytest.fail(f"Invalid timestamp format: {timestamp}")

@pytest.mark.asyncio
async def test_long_content_handling():
    """Test handling of very long content."""
    long_content = "A" * 2000  # Discord has a 2000 char limit
    embed = await post_to_discord(long_content)
    assert len(embed["title"]) <= 256  # Discord embed title limit
