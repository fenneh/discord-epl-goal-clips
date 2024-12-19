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
from urllib.parse import urlparse

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
        dict: Team data if found, None otherwise. Only returns if at least one team is from Premier League.
    """
    title = clean_text(title)  # Clean title before logging
    title_lower = title.lower()
    app_logger.info(f"Finding team in title: {title}")
    
    # Look for score patterns
    score_patterns = [
        r'(.*?)\s*\[(\d+)\]\s*-\s*(\d+)\s*(.*)',  # Team1 [1] - 0 Team2
        r'(.*?)\s*(\d+)\s*-\s*\[(\d+)\]\s*(.*)',  # Team1 0 - [1] Team2
        r'(.*?)\s*\[(\d+)\s*-\s*(\d+)\]\s*(.*)',  # Team1 [1-0] Team2
    ]
    
    for pattern in score_patterns:
        match = re.search(pattern, title_lower)
        if match:
            team1, score1, score2, team2 = match.groups()
            
            # Clean up team names
            team1 = team1.strip()
            team2 = team2.strip()
            
            # Determine which team scored based on bracket position
            team1_scored = '[' in title.split('-')[0]
            scoring_team = team1 if team1_scored else team2
            other_team = team2 if team1_scored else team1
            final_score = f"{score1}-{score2}" if team1_scored else f"{score2}-{score1}"
            
            # Check if either team is in Premier League
            pl_team_found = False
            scoring_team_data = None
            other_team_data = None
            
            for team_name, team_data in premier_league_teams.items():
                team_name_lower = team_name.lower()
                aliases = [alias.lower() for alias in team_data.get('aliases', [])]
                
                # Add word boundaries to prevent partial matches
                team_pattern = rf'\b({team_name_lower}|{"|".join(aliases)})\b'
                
                # Check scoring team
                if re.search(team_pattern, scoring_team):
                    pl_team_found = True
                    scoring_team_data = {'name': team_name, 'data': team_data}
                
                # Check other team
                if re.search(team_pattern, other_team):
                    pl_team_found = True
                    other_team_data = {'name': team_name, 'data': team_data}
            
            # Only proceed if at least one Premier League team is involved
            if pl_team_found:
                app_logger.info(f"Found Premier League team in match: {scoring_team} vs {other_team}")
                
                # Use Premier League team name if available, otherwise use original name
                final_scoring_team = scoring_team_data['name'] if scoring_team_data else scoring_team.title()
                final_other_team = other_team_data['name'] if other_team_data else other_team.title()
                
                # Use scoring team's color ONLY if they are a PL team, otherwise use gray
                color = scoring_team_data['data'].get('color', 0x808080) if scoring_team_data else 0x808080
                
                return {
                    'team': final_scoring_team,
                    'other_team': final_other_team,
                    'score': final_score,
                    'color': color
                }
            else:
                app_logger.info(f"No Premier League team found in match: {scoring_team} vs {other_team}")
                
    app_logger.warning(f"No team found in title: {title}")
    return None

def get_base_domain(url: str) -> str:
    """Extract the base domain without TLD.
    
    Args:
        url (str): Full URL
        
    Returns:
        str: Base domain name (e.g., 'streamff', 'streamin', 'dubz')
    """
    try:
        # Parse the URL and get the netloc (e.g., 'streamff.com', 'streamin.one')
        domain = urlparse(url).netloc
        # Split by dots and get the main part (e.g., 'streamff' from 'streamff.com')
        base_domain = domain.split('.')[0]
        return base_domain
    except Exception as e:
        app_logger.error(f"Error extracting base domain from {url}: {str(e)}")
        return ""

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
                
        # Use video extractor for supported base domains
        supported_domains = {'streamff', 'streamin', 'dubz'}
        if base_domain in supported_domains:
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
