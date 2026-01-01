"""ESPN API service for fetching Premier League match data."""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import aiohttp

from src.utils.logger import setup_logger

espn_logger = setup_logger('espn_service', 'espn.log')

ESPN_SCOREBOARD_URL = "http://site.api.espn.com/apis/site/v2/sports/soccer/eng.1/scoreboard"


async def fetch_todays_matches() -> List[Dict[str, Any]]:
    """Fetch all Premier League matches for today from ESPN API.

    Returns:
        List of match dictionaries with standardized format
    """
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ESPN_SCOREBOARD_URL, timeout=aiohttp.ClientTimeout(total=30)) as response:
                if response.status != 200:
                    espn_logger.error(f"ESPN API error: {response.status}")
                    return []
                data = await response.json()
                matches = _parse_events(data.get('events', []))
                espn_logger.debug(f"Fetched {len(matches)} matches from ESPN")
                return matches
    except aiohttp.ClientError as e:
        espn_logger.error(f"ESPN API request failed: {e}")
        return []
    except Exception as e:
        espn_logger.error(f"Unexpected error fetching ESPN data: {e}")
        return []


def _parse_events(events: List[Dict]) -> List[Dict[str, Any]]:
    """Parse ESPN events into standardized match format.

    Args:
        events: Raw events array from ESPN API

    Returns:
        List of standardized match dictionaries
    """
    matches = []
    for event in events:
        try:
            match = _parse_single_event(event)
            if match:
                matches.append(match)
        except Exception as e:
            espn_logger.error(f"Error parsing event {event.get('id', 'unknown')}: {e}")
    return matches


def _parse_single_event(event: Dict) -> Optional[Dict[str, Any]]:
    """Parse a single ESPN event into standardized format.

    Args:
        event: Single event from ESPN API

    Returns:
        Standardized match dictionary or None if parsing fails
    """
    status_info = event.get('status', {}).get('type', {})

    match = {
        'id': event.get('id'),
        'name': event.get('name'),
        'short_name': event.get('shortName'),
        'date': event.get('date'),  # UTC ISO format
        'status': status_info.get('name'),
        'status_description': status_info.get('description'),
        'home_team': None,
        'away_team': None,
    }

    # Parse competitors
    competitions = event.get('competitions', [])
    if not competitions:
        return match

    competitors = competitions[0].get('competitors', [])
    for comp in competitors:
        team_data = comp.get('team', {})
        team_info = {
            'name': team_data.get('displayName'),
            'short_name': team_data.get('shortDisplayName'),
            'abbreviation': team_data.get('abbreviation'),
            'score': comp.get('score'),
            'logo': team_data.get('logo'),
        }

        if comp.get('homeAway') == 'home':
            match['home_team'] = team_info
        else:
            match['away_team'] = team_info

    return match


def get_match_display_name(match: Dict[str, Any]) -> str:
    """Get a display-friendly match name.

    Args:
        match: Standardized match dictionary

    Returns:
        Formatted match name string
    """
    home = match.get('home_team', {})
    away = match.get('away_team', {})
    home_name = home.get('name', 'Unknown') if home else 'Unknown'
    away_name = away.get('name', 'Unknown') if away else 'Unknown'
    return f"{home_name} vs {away_name}"


def get_match_score_display(match: Dict[str, Any]) -> str:
    """Get a display-friendly score string.

    Args:
        match: Standardized match dictionary

    Returns:
        Formatted score string (e.g., "Arsenal 2 - 1 Chelsea")
    """
    home = match.get('home_team', {})
    away = match.get('away_team', {})
    home_name = home.get('name', 'Unknown') if home else 'Unknown'
    away_name = away.get('name', 'Unknown') if away else 'Unknown'
    home_score = home.get('score', '0') if home else '0'
    away_score = away.get('score', '0') if away else '0'
    return f"{home_name} {home_score} - {away_score} {away_name}"
