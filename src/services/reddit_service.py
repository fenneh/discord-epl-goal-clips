"""Reddit service for fetching goal clips."""

import asyncpraw
import re
import aiohttp
from typing import Optional, Dict, Any, Union
from bs4 import BeautifulSoup
from src.config import CLIENT_ID, CLIENT_SECRET, USER_AGENT
from src.utils.logger import app_logger
from src.config.teams import premier_league_teams
from src.utils.url_utils import get_base_domain
from src.services.video_service import video_extractor
from src.config.domains import base_domains

async def create_reddit_client() -> asyncpraw.Reddit:
    """Create and return a Reddit client instance.
    
    Returns:
        asyncpraw.Reddit: Authenticated Reddit client
    """
    return asyncpraw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
        requestor_kwargs={
            'timeout': 30  # Increase timeout to 30 seconds
        },
        check_for_updates=False,  # Disable update checks
        read_only=True  # Enable read-only mode since we only need to read
    )

def clean_text(text: str) -> str:
    """Clean text to handle unicode characters."""
    return text.encode('ascii', 'ignore').decode('utf-8')

def find_team_in_title(title: str, include_metadata: bool = False) -> Optional[Union[str, Dict[str, Any]]]:
    """Find Premier League team in post title.
    
    Args:
        title (str): Post title to search
        include_metadata (bool): If True, return team data dictionary, otherwise just team name
        
    Returns:
        Optional[Union[str, Dict[str, Any]]]: Team name/data if found, None otherwise
    """
    if not title:
        return None
        
    # Clean and lowercase the title
    title_lower = title.lower()
    
    def check_team_match(text: str, team_name: str, team_data: dict) -> Optional[Union[str, Dict[str, Any]]]:
        """Helper function to check if a team matches in the given text."""
        team_name_lower = team_name.lower()
        aliases = [alias.lower() for alias in team_data.get('aliases', [])]
        
        # Split text into words for exact matching
        text_words = text.split()
        text_phrases = [' '.join(text_words[i:i+4]) for i in range(len(text_words))]  # Check up to 4-word phrases
        
        # Create patterns with word boundaries
        team_patterns = [rf'\b{re.escape(name)}\b' for name in [team_name_lower] + aliases]
        
        # Try exact matches first
        for pattern in team_patterns:
            for phrase in text_phrases:
                if re.fullmatch(pattern, phrase):
                    if include_metadata:
                        return {
                            'name': team_name,
                            'data': team_data,
                            'is_scoring': None
                        }
                    return team_name
        
        # If no exact match, try word boundary matches
        for pattern in team_patterns:
            if re.search(pattern, text):
                # Additional check: make sure we don't match part of a longer word/phrase
                match = re.search(pattern, text)
                start, end = match.span()
                
                # Check character before match (if not at start)
                if start > 0 and text[start-1].isalnum():
                    continue
                    
                # Check character after match (if not at end)
                if end < len(text) and text[end].isalnum():
                    continue
                    
                if include_metadata:
                    return {
                        'name': team_name,
                        'data': team_data,
                        'is_scoring': None
                    }
                return team_name
        return None
        
    # Look for score patterns first
    score_patterns = [
        r'(.*?)\s*\[(\d+)\]\s*-\s*(\d+)\s*(.*)',  # Team1 [1] - 0 Team2
        r'(.*?)\s*(\d+)\s*-\s*\[(\d+)\]\s*(.*)',  # Team1 0 - [1] Team2
        r'(.*?)\s*\[(\d+)\s*-\s*(\d+)\]\s*(.*)',  # Team1 [1-0] Team2
    ]
    
    # Try score patterns first
    for pattern in score_patterns:
        match = re.search(pattern, title_lower)
        if match:
            team1, score1, score2, team2 = match.groups()
            team1 = team1.strip()
            team2 = team2.strip()
            
            # Determine which team scored based on bracket position
            is_team1_scoring = '[' in title.split('-')[0]
            scoring_team = team1 if is_team1_scoring else team2
            other_team = team2 if is_team1_scoring else team1
            
            # Check teams in order of scoring
            scoring_team_match = None
            other_team_match = None
            
            for team_name, team_data in premier_league_teams.items():
                # Check scoring team first
                if not scoring_team_match:
                    result = check_team_match(scoring_team, team_name, team_data)
                    if result:
                        scoring_team_match = result
                
                # Then check other team
                if not other_team_match:
                    result = check_team_match(other_team, team_name, team_data)
                    if result:
                        other_team_match = result
                
                # If we found both teams, use the scoring team's data
                if scoring_team_match:
                    if include_metadata and isinstance(scoring_team_match, dict):
                        scoring_team_match['is_scoring'] = True
                    return scoring_team_match
            
            # If we only found the non-scoring team, use that
            if other_team_match:
                if include_metadata and isinstance(other_team_match, dict):
                    other_team_match['is_scoring'] = False
                return other_team_match
    
    # If no score pattern found, try to find any team in the title
    for team_name, team_data in premier_league_teams.items():
        result = check_team_match(title_lower, team_name, team_data)
        if result:
            return result
            
    return None

async def extract_mp4_link(submission) -> Optional[str]:
    """Extract MP4 link from submission.
    
    Args:
        submission: Reddit submission object
        
    Returns:
        str: MP4 link if found, None otherwise
    """
    try:
        app_logger.info("=== Starting MP4 extraction ===")
        app_logger.info(f"Submission URL: {submission.url}")
        app_logger.info(f"Submission media: {submission.media}")
        
        # Get base domain
        base_domain = get_base_domain(submission.url)
        app_logger.info(f"Base domain: {base_domain}")
        
        # First check if submission URL is already an MP4
        if submission.url.endswith('.mp4'):
            app_logger.info("✓ Direct MP4 URL found")
            return submission.url
            
        # Check if it's a Reddit video
        if hasattr(submission, 'media') and submission.media:
            if 'reddit_video' in submission.media:
                app_logger.info("✓ Reddit video found")
                url = submission.media['reddit_video']['fallback_url']
                app_logger.info(f"Reddit video URL: {url}")
                return url
                
        # Handle streamff.live URLs
        if 'streamff.live' in submission.url:
            app_logger.info("✓ Streamff.live URL found")
            mp4_url = video_extractor.extract_from_streamff(submission.url)
            if mp4_url:
                app_logger.info(f"✓ Found MP4 URL: {mp4_url}")
                return mp4_url
                
        # Use video extractor for supported base domains
        if any(domain in base_domain for domain in base_domains):
            app_logger.info(f"Using video extractor for {base_domain}")
            mp4_url = video_extractor.extract_mp4_url(submission.url)
            if mp4_url:
                app_logger.info(f"✓ Found MP4 URL: {mp4_url}")
                return mp4_url
            else:
                app_logger.warning(f"Video extractor failed to find MP4 URL for: {submission.url}")
                
        app_logger.warning(f"No MP4 URL found for submission: {submission.url}")
        return None
            
    except Exception as e:
        app_logger.error(f"Error extracting MP4 link: {str(e)}")
        return None
