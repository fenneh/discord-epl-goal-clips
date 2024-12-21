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
        
        # Extract team names
        teams_match = re.match(r'([^0-9\[\]]+?)\s*(?:\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+)\s*([^-]+?)\s*-', title)
        
        if not teams_match:
            return None
            
        # Normalize team names by removing "United", "FC", etc.
        team1 = re.sub(r'\s*(United|FC|Football Club)\s*', '', teams_match.group(1).strip())
        team2 = re.sub(r'\s*(United|FC|Football Club)\s*', '', teams_match.group(2).strip())
        
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

def is_duplicate_score(title: str, posted_scores: Dict[str, Dict[str, str]], timestamp: datetime, url: Optional[str] = None) -> bool:
    """Check if the same score for the same game is posted within 5 minutes.
    
    The function uses different time windows to determine duplicates:
    1. 0-30s: Exact URL matches
    2. 0-60s: Exact score/minute/scorer matches (regardless of URL)
    3. 60-120s: Similar minute (±1) matches for different formats
    
    Args:
        title (str): Post title
        posted_scores (dict): Dictionary mapping titles to timestamps and URLs
        timestamp (datetime): Current timestamp
        url (str, optional): URL of the post
        
    Returns:
        bool: True if duplicate, False otherwise
    """
    try:
        # Extract goal info from current title
        current_info = extract_goal_info(title)
        if not current_info:
            return False
            
        for posted_title, data in posted_scores.items():
            # Skip if no timestamp (shouldn't happen)
            if 'timestamp' not in data:
                continue
                
            # Parse stored timestamp
            try:
                posted_time = datetime.fromisoformat(data['timestamp'])
            except (ValueError, TypeError):
                continue
                
            # Calculate time difference
            time_diff = abs((timestamp - posted_time).total_seconds())
            
            # Skip if too old
            if time_diff > 120:  # 2 minutes max
                continue
                
            # Check for exact URL match within 30s
            if time_diff <= 30 and url and data.get('url') == url:
                app_logger.info("-" * 40)
                app_logger.info("[DUPLICATE] Exact URL match within 30s")
                app_logger.info(f"Original:   {posted_title}")
                app_logger.info(f"URL:        {data.get('url')}")
                app_logger.info(f"Reddit URL: {data.get('reddit_url', 'Unknown')}")
                app_logger.info(f"Duplicate:  {title}")
                app_logger.info("-" * 40)
                return True
                
            # Extract goal info from posted title
            posted_info = extract_goal_info(posted_title)
            if not posted_info:
                continue
                
            # Check for exact score/minute/scorer match within 60s
            if time_diff <= 60:
                # Normalize scorer names for comparison
                current_scorer = normalize_player_name(current_info['scorer']) if current_info['scorer'] else None
                posted_scorer = normalize_player_name(posted_info['scorer']) if posted_info['scorer'] else None
                
                # Check if teams match (in either order)
                teams_match = (
                    (current_info['team1'] == posted_info['team1'] and current_info['team2'] == posted_info['team2']) or
                    (current_info['team1'] == posted_info['team2'] and current_info['team2'] == posted_info['team1'])
                )
                
                if (current_info['score'] == posted_info['score'] and
                    current_info['minute'] == posted_info['minute'] and
                    current_scorer == posted_scorer and
                    teams_match):
                    app_logger.info("-" * 40)
                    app_logger.info("[DUPLICATE] Exact score match within 60s")
                    app_logger.info(f"Original:   {posted_title}")
                    app_logger.info(f"URL:        {data.get('url')}")
                    app_logger.info(f"Reddit URL: {data.get('reddit_url', 'Unknown')}")
                    app_logger.info(f"Duplicate:  {title}")
                    app_logger.info(f"Scorer:     {posted_scorer} = {current_scorer}")
                    app_logger.info(f"Teams:      {current_info['team1']} vs {current_info['team2']}")
                    app_logger.info("-" * 40)
                    return True
                    
            # Check for similar minute match within 120s
            elif time_diff <= 120:
                # Calculate effective minutes (base + injury)
                current_minute = current_info['minute'].split('+')[0] if '+' in current_info['minute'] else current_info['minute']
                posted_minute = posted_info['minute'].split('+')[0] if '+' in posted_info['minute'] else posted_info['minute']
                
                if (current_info['score'] == posted_info['score'] and
                    abs(int(current_minute) - int(posted_minute)) <= 1 and
                    teams_match):
                    app_logger.info("-" * 40)
                    app_logger.info("[DUPLICATE] Similar minute match within 120s")
                    app_logger.info(f"Original:   {posted_title}")
                    app_logger.info(f"URL:        {data.get('url')}")
                    app_logger.info(f"Reddit URL: {data.get('reddit_url', 'Unknown')}")
                    app_logger.info(f"Duplicate:  {title}")
                    app_logger.info(f"Minutes:    {posted_minute}' ≈ {current_minute}'")
                    app_logger.info(f"Teams:      {current_info['team1']} vs {current_info['team2']}")
                    app_logger.info("-" * 40)
                    return True
                    
        return False
        
    except Exception as e:
        app_logger.error(f"Error checking for duplicate score: {str(e)}")
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
