"""Utilities for handling score patterns and duplicates."""

import re
import time
import unicodedata
from datetime import datetime, timezone, timedelta
from difflib import SequenceMatcher
from typing import Dict, Optional
from src.utils.logger import app_logger

def get_similarity_ratio(a: str, b: str) -> float:
    """Return a ratio of similarity between two strings.
    
    Args:
        a (str): First string
        b (str): Second string
        
    Returns:
        float: Similarity ratio between 0 and 1
    """
    return SequenceMatcher(None, a, b).ratio()

def normalize_score_pattern(title: str) -> Optional[str]:
    """Extract and normalize just the score pattern.
    
    Args:
        title (str): Post title
        
    Returns:
        str: Normalized score pattern if found, None otherwise
    """
    # Extract score pattern and minute
    score_pattern = re.search(r'(\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+)', title)
    minute_pattern = re.search(r'(\d+)\'', title)
    
    if not score_pattern or not minute_pattern:
        return None
        
    return f"{score_pattern.group(1)}_{minute_pattern.group(1)}'"

def normalize_player_name(name: str) -> str:
    """Normalize player name to handle different formats.
    
    Handles cases like:
    - "Gabriel Jesus" -> "jesus"
    - "G. Jesus" -> "jesus"
    - "Eddie Nketiah" -> "nketiah"
    - "E. Nketiah" -> "nketiah"
    - "van Dijk" -> "van dijk"
    - "L. Díaz" -> "diaz"
    - "Luis Diaz" -> "diaz"
    
    Args:
        name (str): Player name to normalize
        
    Returns:
        str: Normalized name
    """
    # Convert to lowercase
    name = name.lower()
    
    # Remove accents and special characters
    name = ''.join(c for c in unicodedata.normalize('NFKD', name)
                  if not unicodedata.combining(c))
    
    # Remove any remaining non-alphanumeric characters except spaces
    name = re.sub(r'[^a-z0-9\s]', '', name)
    
    # Handle abbreviated first names (e.g., "G. Jesus" -> "jesus")
    if '. ' in name:
        name = name.split('. ')[1]
    elif len(name.split()) > 1:
        # For full names, take the last part
        name = name.split()[-1]
    
    # Special cases for multi-word last names
    multi_word_prefixes = ['van', 'de', 'den', 'der', 'dos', 'el', 'al']
    words = name.split()
    
    if len(words) > 1:
        # Check if we have a multi-word last name
        for i, word in enumerate(words[:-1]):
            if word in multi_word_prefixes:
                return ' '.join(words[i:])
    
    return name.strip()

def normalize_team_name(team_name: str) -> str:
    """Normalize team names to handle common variations.
    
    Args:
        team_name (str): Team name to normalize
        
    Returns:
        str: Normalized team name
    """
    # Convert to lowercase for case-insensitive comparison
    name = team_name.lower().strip()
    
    # Remove "the" prefix
    if name.startswith('the '):
        name = name[4:]
    
    # Handle special cases and nicknames first
    # Make sure team names in keys are normalized lowercase too
    replacements = {
        'arsenal': ['gunners'],
        'manchester united': ['man united', 'man utd', 'united', 'mufc'],
        'manchester city': ['man city', 'city', 'mcfc'],
        'tottenham': ['spurs', 'thfc', 'tottenham hotspur', 'hotspur'],
        'wolverhampton wanderers': ['wolves', 'wwfc', 'wanderers'],
        'brighton & hove albion': ['brighton', 'brighton and hove', 'bha'],
        'crystal palace': ['palace', 'cpfc'],
        'aston villa': ['villa', 'avfc'],
        'newcastle united': ['newcastle', 'nufc', 'newcastle utd'],
        'west ham united': ['west ham', 'hammers', 'whufc'],
        'liverpool': ['reds', 'lfc'],
        'chelsea': ['blues', 'cfc'],
        'leicester city': ['leicester', 'lcfc', 'foxes']
    }
    
    # Try to match team name with known variations first
    for standard, variations in replacements.items():
        # Check if the name matches the standard form
        if name == standard:
            return standard
            
        # Check if the name matches any of the variations exactly or as a word
        for var in variations:
            # Use word boundaries for alias matching to avoid partial words
            # e.g. prevent 'man' matching 'manchester' if 'man' isn't a specific alias
            if re.fullmatch(var, name) or re.search(rf'\b{re.escape(var)}\b', name):
                return standard

    # Remove common suffixes AFTER checking specific aliases/names to avoid over-stripping
    # Example: "Manchester United" should be normalized above, not stripped to "Manchester" here
    name = re.sub(r'\s+(fc|football club|united|utd|hotspur|wanderers|&|and|albion|city)(\s+|$)', ' ', name, flags=re.IGNORECASE).strip()
            
    return name.strip()

def extract_goal_info(title: str) -> Optional[Dict[str, str]]:
    """Extract goal information from title.
    
    Args:
        title (str): Post title
        
    Returns:
        dict: Dictionary containing score, minute, and scorer if found
    """
    try:
        # Extract score pattern and minute
        score_match = re.search(r'(\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+)', title)
        # Handle injury time minutes (e.g., 90+2)
        minute_match = re.search(r'(\d+(?:\+\d+)?)\s*\'', title)
        
        if not score_match or not minute_match:
            return None
            
        # Extract scorer's name - usually before the minute
        name_match = re.search(r'-\s*([^-]+?)\s*\d+(?:\+\d+)?\s*\'', title)
        
        # Extract team names - more flexible pattern that handles variations better
        score_pattern = score_match.group(1)
        title_parts = title.split(score_pattern)
        if len(title_parts) != 2:
            return None
            
        # First part is team1, second part has team2 followed by scorer
        team1 = title_parts[0].strip()
        team2_match = re.match(r'\s*([^-]+?)\s*-', title_parts[1])
        if not team2_match:
            return None
            
        team2 = team2_match.group(1).strip()
        
        # Normalize team names
        team1_norm = normalize_team_name(team1)
        team2_norm = normalize_team_name(team2)
        
        return {
            'score': score_match.group(1).replace(' ', ''),
            'minute': minute_match.group(1),
            'scorer': name_match.group(1).strip() if name_match else None,
            'team1': team1_norm,
            'team2': team2_norm
        }
        
    except Exception as e:
        app_logger.error(f"Error extracting goal info: {str(e)}")
        return None

def normalize_title(title: str) -> str:
    """Normalize title to canonical format.
    
    This removes variations in player names (e.g., "G. Jesus" vs "Gabriel Jesus")
    and other formatting differences.
    
    Args:
        title (str): Title to normalize
        
    Returns:
        str: Normalized title
    """
    # Extract goal info
    goal_info = extract_goal_info(title)
    if not goal_info:
        return title
        
    # Reconstruct title in canonical format
    return f"{goal_info['team1']} vs {goal_info['team2']} {goal_info['score']} {goal_info['minute']}' Scorer: {goal_info.get('scorer', 'Unknown')}"

def extract_minutes(minute_str: str) -> int:
    """Extract the base minute from a minute string, handling injury time.
    
    Args:
        minute_str (str): Minute string (e.g., "90+2", "45", "45+1")
        
    Returns:
        int: Total minutes
    """
    if '+' in minute_str:
        base, injury = minute_str.split('+')
        return int(base) + int(injury)
    return int(minute_str)

def generate_canonical_key(goal_info: Dict[str, str]) -> Optional[str]:
    """Generates a consistent key for a goal event."""
    if not goal_info or not goal_info.get('team1') or not goal_info.get('team2') or not goal_info.get('score') or not goal_info.get('minute'):
        app_logger.debug(f"Cannot generate canonical key, missing info: {goal_info}")
        return None
    # Sort team names alphabetically to handle "TeamA vs TeamB" and "TeamB vs TeamA" the same
    teams_key = "_vs_".join(sorted([goal_info['team1'], goal_info['team2']]))
    # Use base minute to handle minor variations in injury time reporting
    base_minute = goal_info['minute'].split('+')[0]
    # Normalize score by removing spaces and brackets
    score_key = re.sub(r'[\\[\\]\\s]', '', goal_info['score'])
    key = f"{teams_key}_{score_key}_{base_minute}"
    app_logger.debug(f"Generated canonical key: {key}")
    return key

def is_duplicate_score(title: str, posted_scores: Dict[str, Dict[str, str]], timestamp: datetime, url: Optional[str] = None) -> bool:
    """Check if this goal has already been posted using a canonical key."""
    # Set a time window for considering duplicates (e.g., 30 minutes)
    DUPLICATE_CHECK_WINDOW_MINUTES = 30

    try:
        current_info = extract_goal_info(title)
        if not current_info:
            app_logger.warning(f"Could not extract goal info for duplicate check: {title}")
            return False # Cannot determine if duplicate if info extraction fails

        canonical_key = generate_canonical_key(current_info)
        if not canonical_key:
            app_logger.warning(f"Could not generate canonical key for duplicate check: {title}")
            return False # Cannot determine if duplicate

        if canonical_key in posted_scores:
            # Check timestamp to ensure it's reasonably close
            posted_data = posted_scores[canonical_key]
            posted_time = datetime.fromisoformat(posted_data['timestamp'])
            time_diff = timestamp - posted_time
            
            if time_diff < timedelta(minutes=DUPLICATE_CHECK_WINDOW_MINUTES):
                 app_logger.info(f"[DUPLICATE] Found matching canonical key '{canonical_key}' within {DUPLICATE_CHECK_WINDOW_MINUTES} mins.")
                 app_logger.info(f"  Current Post:  Title='{title}', URL='{url}'")
                 # Use get with default for keys that might not exist in older stored data
                 app_logger.info(f"  Previous Post: Title='{posted_data.get('original_title', 'N/A')}', URL='{posted_data.get('url', 'N/A')}', Reddit='{posted_data.get('reddit_url', 'N/A')}', Time='{posted_time}'")
                 return True
            else:
                 app_logger.info(f"[STALE MATCH] Canonical key '{canonical_key}' found, but outside time window ({time_diff}). Not a duplicate.")
                 # Optional: Update timestamp if it's just a stale entry for the same key?
                 # posted_scores[canonical_key]['timestamp'] = timestamp.isoformat() # Consider if this makes sense

        return False # No recent matching key found

    except Exception as e:
        app_logger.error(f"Error in is_duplicate_score: {str(e)}", exc_info=True)
        return False # Err on the side of not calling it a duplicate

def cleanup_old_scores(posted_scores: Dict[str, Dict[str, str]]) -> bool:
    """Remove scores older than a defined threshold (e.g., 24 hours)."""
    CLEANUP_THRESHOLD_HOURS = 24 # Example threshold
    now = datetime.now(timezone.utc)
    keys_to_delete = []
    initial_count = len(posted_scores)

    for key, data in posted_scores.items():
        try:
            posted_time = datetime.fromisoformat(data['timestamp'])
            if now - posted_time > timedelta(hours=CLEANUP_THRESHOLD_HOURS):
                keys_to_delete.append(key)
        except (ValueError, KeyError) as e:
            app_logger.warning(f"Could not parse timestamp for score key '{key}': {e}. Marking for deletion.")
            keys_to_delete.append(key) # Remove entries with invalid timestamps

    deleted_count = 0
    for key in keys_to_delete:
        if key in posted_scores:
            del posted_scores[key]
            deleted_count += 1

    if deleted_count > 0:
        app_logger.info(f"Cleaned up {deleted_count} old score entries (older than {CLEANUP_THRESHOLD_HOURS} hours).")
        return True # Indicate that changes were made

    return False # No changes made
