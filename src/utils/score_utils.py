"""Utilities for handling score patterns and duplicates."""

import re
import time
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

def is_duplicate_score(title: str, posted_scores: Dict[str, datetime], timestamp: datetime) -> bool:
    """Check if the same score for the same game is posted within 30 seconds.
    
    Args:
        title (str): Post title
        posted_scores (dict): Dictionary mapping titles to timestamps
        timestamp (datetime): Current timestamp
        
    Returns:
        bool: True if duplicate, False otherwise
    """
    try:
        normalized_score = normalize_score_pattern(title)
        if not normalized_score:
            return False
            
        # Extract score pattern and minute
        score_pattern = re.search(r'(\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+)', title)
        minute_pattern = re.search(r'(\d+)\'', title)
        
        if not score_pattern or not minute_pattern:
            return False
            
        current_score = score_pattern.group(1)
        current_minute = minute_pattern.group(1)
        
        # Check against recent posts
        for posted_title, posted_time in list(posted_scores.items()):
            time_diff = timestamp - posted_time.replace(tzinfo=timezone.utc)
            
            # Only check posts within last 300 seconds
            if time_diff.total_seconds() < 300:
                # Extract score and minute from posted title
                posted_score_match = re.search(r'(\d+\s*-\s*\[\d+\]|\[\d+\]\s*-\s*\d+)', posted_title)
                posted_minute_match = re.search(r'(\d+)\'', posted_title)
                
                if not posted_score_match or not posted_minute_match:
                    continue
                    
                posted_score = posted_score_match.group(1)
                posted_minute = posted_minute_match.group(1)
                
                # Calculate similarity for the full text
                similarity = get_similarity_ratio(title.lower(), posted_title.lower())
                
                # Consider it a duplicate only if:
                # 1. The score pattern is exactly the same
                # 2. The minute is exactly the same
                # 3. The overall similarity is very high
                if (current_score == posted_score and 
                    current_minute == posted_minute and 
                    similarity > 0.85):
                    app_logger.info(f"Duplicate score found: {title}")
                    return True
                    
        return False
        
    except Exception as e:
        app_logger.error(f"Error checking for duplicate score: {str(e)}")
        return False

def cleanup_old_scores(posted_scores: Dict[str, datetime]) -> None:
    """Remove scores older than 5 minutes from the posted_scores dictionary.
    
    Args:
        posted_scores (dict): Dictionary mapping titles to timestamps
    """
    current_time = datetime.now(timezone.utc)
    to_remove = []
    
    for title, timestamp in posted_scores.items():
        time_diff = current_time - timestamp.replace(tzinfo=timezone.utc)
        if time_diff.total_seconds() > 300:  # 5 minutes
            to_remove.append(title)
            
    for title in to_remove:
        del posted_scores[title]
