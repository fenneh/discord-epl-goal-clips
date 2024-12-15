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

async def find_team_in_title(title: str) -> Optional[Dict]:
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
            app_logger.info(f"Found score pattern. Teams: '{team1}' vs '{team2}'")
            
            # Find the team that scored (the one with brackets)
            scoring_team = team1 if '[' in title.split('-')[0] else team2
            app_logger.info(f"Scoring team section: {scoring_team}")
            
            # Look for the scoring team first
            for team, data in premier_league_teams.items():
                for team_name in data["names"]:
                    team_name_lower = team_name.lower()
                    if team_name_lower in scoring_team.lower():
                        app_logger.info(f"Found scoring team: {team}")
                        return data
            
            # If scoring team not found, check both teams
            for team, data in premier_league_teams.items():
                for team_name in data["names"]:
                    team_name_lower = team_name.lower()
                    if team_name_lower in team1 or team_name_lower in team2:
                        app_logger.info(f"Found team: {team}")
                        return data
    
    # If no score pattern found, try simple name matching
    app_logger.info("No score pattern found, trying simple name matching")
    for team, data in premier_league_teams.items():
        for team_name in data["names"]:
            if team_name.lower() in title_lower:
                app_logger.info(f"Found team by name: {team}")
                return data
    
    app_logger.info("No team found in title")
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
