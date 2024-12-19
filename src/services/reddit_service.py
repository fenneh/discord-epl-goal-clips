"""Reddit service for fetching goal clips."""

import asyncpraw
import re
import aiohttp
from typing import Optional, Dict
from bs4 import BeautifulSoup
from src.config import CLIENT_ID, CLIENT_SECRET, USER_AGENT
from src.utils.logger import app_logger
from src.config.teams import premier_league_teams
from src.services.video_service import video_extractor  # Fix import path

async def create_reddit_client() -> asyncpraw.Reddit:
    """Create and return a Reddit client instance.
    
    Returns:
        asyncpraw.Reddit: Authenticated Reddit client
    """
    return asyncpraw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT
    )

def clean_text(text: str) -> str:
    """Clean text to handle unicode characters."""
    return text.encode('ascii', 'ignore').decode('utf-8')

def find_team_in_title(title: str) -> Optional[Dict]:
    """Find the scoring team in a post title based on square brackets.
    
    Args:
        title (str): Post title to search
        
    Returns:
        dict: Team data if found, None otherwise
    """
    title = clean_text(title)  # Clean title before logging
    title_lower = title.lower()
    app_logger.info(f"Finding team in title: {title}")
    
    # Try different score patterns
    patterns = [
        r'(.*?)\s*\[(\d+)\]\s*-\s*(\d+)\s*(.*)',  # Team1 [1] - 0 Team2
        r'(.*?)\s*(\d+)\s*-\s*\[(\d+)\]\s*(.*)',  # Team1 0 - [1] Team2
    ]
    
    for pattern in patterns:
        match = re.search(pattern, title_lower)
        if match:
            team1, score1, score2, team2 = match.groups()
            
            # Clean up team names
            team1 = team1.strip()
            team2 = team2.strip()
            
            # Check if either team is in Premier League
            scoring_team = None
            other_team = None
            is_scoring_first = score1 > score2
            
            # Check both teams against Premier League teams
            for team_name, team_data in premier_league_teams.items():
                team_name_lower = team_name.lower()
                aliases = [alias.lower() for alias in team_data.get('aliases', [])]
                
                # Check if team1 matches
                if team_name_lower in team1 or any(alias in team1 for alias in aliases):
                    if is_scoring_first:
                        scoring_team = team_data
                    else:
                        other_team = team_data
                        
                # Check if team2 matches
                if team_name_lower in team2 or any(alias in team2 for alias in aliases):
                    if not is_scoring_first:
                        scoring_team = team_data
                    else:
                        other_team = team_data
                        
            if scoring_team:
                app_logger.info(f"Found scoring team: {scoring_team.get('name', 'Unknown')}")
                return {
                    'scoring_team': scoring_team,
                    'other_team': other_team,
                    'score': f"{score1}-{score2}" if is_scoring_first else f"{score2}-{score1}"
                }
                
    app_logger.info("No Premier League team found in title")
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
        app_logger.info(f"Submission domain: {submission.domain}")
        
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
                
        # Use video extractor for supported domains
        if any(domain in submission.url for domain in ['streamff.com', 'streamff.live']):
            app_logger.info("Using video extractor")
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
