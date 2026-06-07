"""Utilities for match notification features."""

from datetime import datetime, timezone
from typing import Dict, Optional, Any

import pytz

from src.config.competitions import Competition, EPL
from src.config.teams import get_teams_for_competition
from src.utils.score_utils import normalize_team_name

UK_TZ = pytz.timezone("Europe/London")

# Premier League brand color (purple) — kept for any legacy reference.
PL_COLOR = 0x37003C


def map_espn_team_to_config(
    espn_team_name: str, competition: Competition = EPL
) -> Optional[Dict[str, Any]]:
    """Map an ESPN team name to the competition's team config for colours/logos."""
    if not espn_team_name:
        return None

    espn_normalized = normalize_team_name(espn_team_name)
    teams_dict = get_teams_for_competition(competition.id)

    for team_key, team_data in teams_dict.items():
        if normalize_team_name(team_key) == espn_normalized:
            return {"name": team_key, "data": team_data, "is_scoring": None}

        aliases = team_data.get("aliases", [])
        if isinstance(aliases, list):
            for alias in aliases:
                if normalize_team_name(alias) == espn_normalized:
                    return {"name": team_key, "data": team_data, "is_scoring": None}

    return None


def format_match_time_uk(utc_datetime_str: str) -> str:
    """Convert UTC datetime string to formatted UK time.

    Args:
        utc_datetime_str: ISO format UTC datetime string (e.g., "2026-01-01T15:00Z")

    Returns:
        Formatted time string in UK timezone (e.g., "15:00")
    """
    try:
        # Handle both Z suffix and +00:00 format
        if utc_datetime_str.endswith("Z"):
            utc_datetime_str = utc_datetime_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(utc_datetime_str)
        uk_time = dt.astimezone(UK_TZ)
        return uk_time.strftime("%H:%M")
    except Exception:
        return "TBD"


def format_match_date_uk(utc_datetime_str: str) -> str:
    """Convert UTC datetime string to formatted UK date.

    Args:
        utc_datetime_str: ISO format UTC datetime string

    Returns:
        Formatted date string (e.g., "1 Jan 2026")
    """
    try:
        if utc_datetime_str.endswith("Z"):
            utc_datetime_str = utc_datetime_str[:-1] + "+00:00"
        dt = datetime.fromisoformat(utc_datetime_str)
        uk_time = dt.astimezone(UK_TZ)
        return uk_time.strftime("%-d %b %Y")
    except Exception:
        return "Unknown Date"


def get_current_uk_time() -> datetime:
    """Get current time in UK timezone.

    Returns:
        datetime object in UK timezone
    """
    return datetime.now(timezone.utc).astimezone(UK_TZ)


def get_today_uk_date_str() -> str:
    """Get today's date string in UK timezone.

    Returns:
        Date string in YYYY-MM-DD format
    """
    return get_current_uk_time().strftime("%Y-%m-%d")
