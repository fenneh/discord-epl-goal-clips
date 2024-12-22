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
    
    Args:
        name (str): Player name to normalize
        
    Returns:
        str: Normalized name
    """
    # Convert to lowercase
    name = name.lower()
    
    # Remove accents
    name = ''.join(c for c in unicodedata.normalize('NFKD', name)
                  if not unicodedata.combining(c))
    
    # Handle abbreviated first names (e.g., "G. Jesus" -> "jesus")
    if '. ' in name:
        name = name.split('. ')[1]
    
    # Special cases for multi-word last names
    multi_word_prefixes = ['van', 'de', 'den', 'der', 'dos', 'el', 'al']
    words = name.split()
    
    if len(words) > 1:
        # Check if we have a multi-word last name
        for i, word in enumerate(words[:-1]):
            if word in multi_word_prefixes:
                return ' '.join(words[i:])
        # Default to last word
        return words[-1]
    
    return name

def normalize_team_name(team_name: str) -> str:
    """Normalize team names to handle common variations.
    
    Args:
        team_name (str): Team name to normalize
        
    Returns:
        str: Normalized team name
    """
    # Convert to lowercase for case-insensitive comparison
    name = team_name.lower()
    
    # Remove "the" prefix
    if name.startswith('the '):
        name = name[4:]
    
    # Remove common suffixes
    name = re.sub(r'\s+(fc|football club|united|utd|hotspur|wanderers|&|and|albion|city)(\s+|$)', ' ', name).strip()
    
    # Handle special cases and nicknames
    replacements = {
        'arsenal': ['gunners'],
        'manchester': ['man', 'mufc', 'mcfc'],
        'tottenham': ['spurs', 'thfc'],
        'wolves': ['wolverhampton', 'wwfc', 'wanderers'],
        'brighton': ['brighton and hove', 'brighton & hove', 'brighton hove'],
        'crystal': ['palace', 'cpfc', 'crystal palace'],
        'villa': ['aston', 'aston villa', 'avfc'],
        'newcastle': ['nufc', 'newcastle upon tyne', 'newcastle united', 'newcastle utd'],
        'west ham': ['hammers', 'whufc'],
        'liverpool': ['reds', 'lfc'],
        'chelsea': ['blues', 'cfc'],
        'leicester': ['lcfc', 'foxes', 'leicester city']
    }
    
    # Try to match team name with known variations
    for standard, variations in replacements.items():
        # Check if the name matches the standard form
        if name == standard:
            return standard
            
        # Check if the name matches any of the variations exactly or as a word
        for var in variations:
            if (var == name or 
                re.search(rf'\b{re.escape(var)}\b', name) or 
                re.search(rf'\b{re.escape(name)}\b', var)):
                return standard
            
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
        team1 = normalize_team_name(team1)
        team2 = normalize_team_name(team2)
        
        return {
            'score': score_match.group(1),
            'minute': minute_match.group(1),
            'scorer': name_match.group(1).strip() if name_match else None,
            'team1': team1,
            'team2': team2
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
    return f"{goal_info['score']} - {goal_info['scorer']} {goal_info['minute']}'"

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

def is_duplicate_score(title: str, posted_scores: Dict[str, Dict[str, str]], timestamp: datetime, url: Optional[str] = None) -> bool:
    """Check if this goal has already been posted.
    
    A goal is considered a duplicate if:
    1. It has the same teams (in either order)
    2. It has the same score state
    3. It occurred at approximately the same minute (±2 minutes to account for posting delays and injury time)
    
    Special cases:
    - A goal at 89' and 90' is considered the same goal (end of regular time)
    - A goal at 45' and 45+1' is considered the same goal (end of first half)
    
    Args:
        title (str): Post title
        posted_scores (dict): Dictionary mapping titles to timestamps and URLs
        timestamp (datetime): Current timestamp (used for logging)
        url (str, optional): URL of the post (used for logging)
        
    Returns:
        bool: True if duplicate, False otherwise
    """
    try:
        # Extract goal info from current title
        current_info = extract_goal_info(title)
        if not current_info:
            return False
            
        for posted_title, data in posted_scores.items():
            # Extract goal info from posted title
            posted_info = extract_goal_info(posted_title)
            if not posted_info:
                continue
                
            # Check if teams match (in either order)
            teams_match = (
                (current_info['team1'] == posted_info['team1'] and current_info['team2'] == posted_info['team2']) or
                (current_info['team1'] == posted_info['team2'] and current_info['team2'] == posted_info['team1'])
            )
            
            if not teams_match:
                continue
                
            # Check if score state matches
            if current_info['score'] != posted_info['score']:
                continue
                
            # Calculate effective minutes (base + injury)
            current_minute = extract_minutes(current_info['minute'])
            posted_minute = extract_minutes(posted_info['minute'])
            
            # Special case: 89' and 90' are considered the same minute (end of regular time)
            if (current_minute == 89 and posted_minute == 90) or (current_minute == 90 and posted_minute == 89):
                is_same_minute = True
            # Special case: 45' and 45+1' are considered the same minute (end of first half)
            elif (current_minute == 45 and posted_minute in (45, 46)) or (posted_minute == 45 and current_minute in (45, 46)):
                is_same_minute = True
            # Regular case: Allow ±2 minute variation
            else:
                is_same_minute = abs(current_minute - posted_minute) <= 2
                
            if is_same_minute:
                app_logger.info("-" * 40)
                app_logger.info("[DUPLICATE] Same goal detected")
                app_logger.info(f"Original:   {posted_title}")
                app_logger.info(f"URL:        {data.get('url')}")
                app_logger.info(f"Reddit URL: {data.get('reddit_url', 'Unknown')}")
                app_logger.info(f"Duplicate:  {title}")
                app_logger.info(f"Teams:      {current_info['team1']} vs {current_info['team2']}")
                app_logger.info(f"Score:      {current_info['score']}")
                app_logger.info(f"Minutes:    {posted_info['minute']}' ≈ {current_info['minute']}'")
                app_logger.info("-" * 40)
                return True
                
        return False
        
    except Exception as e:
        app_logger.error(f"Error checking duplicate score: {str(e)}")
        return False

def cleanup_old_scores(posted_scores: Dict[str, Dict[str, str]]) -> None:
    """Remove scores older than 5 minutes from the posted_scores dictionary.
    
    Args:
        posted_scores (dict): Dictionary mapping titles to timestamps and URLs
    """
    try:
        app_logger.debug(f"Starting cleanup of old scores: {posted_scores}")
        current_time = datetime.now(timezone.utc)
        # Create a list of items to remove
        to_remove = []
        
        # First pass: identify items to remove
        for title, data in list(posted_scores.items()):
            app_logger.debug(f"Checking title: {title}, data: {data}")
            
            # Handle legacy data where value is a datetime object
            if isinstance(data, datetime):
                app_logger.warning(f"Converting legacy data for {title}")
                posted_scores[title] = {
                    'timestamp': data.isoformat(),
                    'url': '',  # No URL for legacy data
                    'team': '',
                    'score': ''
                }
                continue
                
            if not isinstance(data, dict):
                app_logger.warning(f"Invalid data type for {title}: {type(data)}")
                to_remove.append(title)
                continue
                
            if 'timestamp' not in data:
                app_logger.warning(f"No timestamp in data for {title}")
                to_remove.append(title)
                continue
                
            try:
                posted_time = datetime.fromisoformat(data['timestamp'])
                time_diff = (current_time - posted_time).total_seconds()
                app_logger.debug(f"Time difference for {title}: {time_diff} seconds")
                if time_diff > 300:  # 5 minutes
                    app_logger.info(f"Removing old score: {title} (age: {time_diff}s)")
                    to_remove.append(title)
            except (ValueError, TypeError) as e:
                app_logger.error(f"Error parsing timestamp for {title}: {str(e)}")
                to_remove.append(title)
                
        # Second pass: remove identified items
        for title in to_remove:
            app_logger.debug(f"Removing title: {title}")
            posted_scores.pop(title, None)
            
    except Exception as e:
        app_logger.error(f"Error in cleanup_old_scores: {str(e)}")
