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
        if not name_match:
            return None
            
        # Clean up the minute (take base minute for 90+2 -> 90)
        minute = minute_match.group(1)
        if '+' in minute:
            minute = minute.split('+')[0]
            
        return {
            'score': score_match.group(1),
            'minute': minute,
            'scorer': normalize_player_name(name_match.group(1).strip())
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
        # Extract current goal info
        current_info = extract_goal_info(title)
        if not current_info:
            return False
            
        # Track if we found a duplicate in any time window
        is_duplicate = False
            
        # Check against recent posts
        for posted_title, posted_data in list(posted_scores.items()):
            posted_time = posted_data['timestamp'].replace(tzinfo=timezone.utc)
            posted_url = posted_data.get('url')
            
            time_diff = timestamp - posted_time
            time_diff_seconds = time_diff.total_seconds()
            
            # Skip if too old
            if time_diff_seconds >= 300:  # 5 minutes
                continue
                
            # First check: Exact URL match within 30 seconds
            if url and posted_url and url == posted_url and time_diff_seconds < 30:
                app_logger.info(f"Duplicate detected - Exact URL match within 30s: {url}")
                return True
            
            # Extract posted goal info
            posted_info = extract_goal_info(posted_title)
            if not posted_info:
                continue
            
            # Log potential matches for debugging
            app_logger.debug(f"Comparing current: {current_info}")
            app_logger.debug(f"With posted: {posted_info}")
            app_logger.debug(f"Time difference: {time_diff_seconds}s")
            
            # Consider it a duplicate if ANY of these conditions are met:
            # 1. Exact same score, minute, and normalized scorer within 60 seconds
            if time_diff_seconds < 60:
                if (current_info['score'] == posted_info['score'] and 
                    current_info['minute'] == posted_info['minute'] and
                    current_info['scorer'] == posted_info['scorer']):
                    app_logger.info(f"Duplicate detected - Same score/minute/scorer within 60s")
                    app_logger.info(f"Scorer match: {current_info['scorer']} == {posted_info['scorer']}")
                    is_duplicate = True
                    break  # Stop checking other posts
                
            # 2. Same score pattern and similar minute (±1) within 120 seconds
            # BUT only if the titles are different formats (e.g., "G. Jesus" vs "Gabriel Jesus")
            elif 60 <= time_diff_seconds < 120:
                minute_diff = abs(int(current_info['minute']) - int(posted_info['minute']))
                if (current_info['score'] == posted_info['score'] and 
                    minute_diff <= 1 and 
                    current_info['scorer'] == posted_info['scorer'] and
                    title != posted_title and  # Different title formats
                    normalize_title(title) != normalize_title(posted_title)):  # Different formats
                    app_logger.info(f"Duplicate detected - Same score/scorer, similar minute")
                    is_duplicate = True
                    break  # Stop checking other posts
                
        return is_duplicate
        
    except Exception as e:
        app_logger.error(f"Error checking for duplicate score: {str(e)}")
        return False

def cleanup_old_scores(posted_scores: Dict[str, Dict[str, str]]) -> None:
    """Remove scores older than 5 minutes from the posted_scores dictionary.
    
    Args:
        posted_scores (dict): Dictionary mapping titles to timestamps and URLs
    """
    current_time = datetime.now(timezone.utc)
    to_remove = []
    
    for title, data in posted_scores.items():
        timestamp = data['timestamp'].replace(tzinfo=timezone.utc)
        time_diff = current_time - timestamp
        if time_diff.total_seconds() > 300:  # 5 minutes
            to_remove.append(title)
            
    for title in to_remove:
        del posted_scores[title]
