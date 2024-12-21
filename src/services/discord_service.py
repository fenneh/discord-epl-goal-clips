"""Discord webhook service for posting goal clips."""

import aiohttp
import re
from datetime import datetime, timezone
from typing import Dict, Optional
from src.config import DISCORD_WEBHOOK_URL, DISCORD_USERNAME, DISCORD_AVATAR_URL
from src.config.teams import premier_league_teams
from src.utils.logger import webhook_logger

def clean_text(text: str) -> str:
    """Clean text by removing unwanted unicode characters."""
    # Remove left-to-right mark and other invisible unicode characters
    text = re.sub(r'[\u200e\u200f\u202a-\u202e]', '', text)
    return text.strip()

async def post_to_discord(
    content: str,
    team_data: Optional[Dict] = None,
    username: str = DISCORD_USERNAME,
    avatar_url: str = DISCORD_AVATAR_URL
) -> bool:
    """Post content to Discord webhook."""
    if not DISCORD_WEBHOOK_URL:
        webhook_logger.error("Discord webhook URL not configured")
        return False

    # Split content into title and URLs, handling extra newlines
    lines = [line.strip() for line in content.split('\n') if line.strip()]
    title = clean_text(lines[0].strip('*'))  # Remove markdown and clean text
    video_url = lines[1] if len(lines) > 1 else None
    reddit_url = lines[2] if len(lines) > 2 else None

    webhook_logger.info(f"Preparing Discord message:")
    webhook_logger.info(f"Title: {title}")
    webhook_logger.info(f"Video URL: {video_url}")
    webhook_logger.info(f"Reddit URL: {reddit_url}")
    webhook_logger.info(f"Team data: {team_data}")

    # Get color from team data
    color = 0x808080  # Default gray
    if team_data and "data" in team_data:
        team_info = team_data["data"]
        if "color" in team_info:
            color = team_info["color"]
            webhook_logger.info(f"Using team color: {color}")

    # Create the embed with both URLs in description
    embed = {
        "title": title,
        "description": f"{video_url}\n\n{reddit_url}" if video_url and reddit_url else '',  # Double newline between URLs
        "color": color,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Add team logo if available
    if team_data and "data" in team_data:
        team_info = team_data["data"]
        if "logo" in team_info:
            embed["thumbnail"] = {"url": team_info["logo"]}
            webhook_logger.info(f"Added team logo: {team_info['logo']}")

    # Prepare webhook data - no content, only embed
    webhook_data = {
        "username": username,
        "avatar_url": avatar_url,
        "embeds": [embed]
    }

    webhook_logger.info(f"Final webhook data: {webhook_data}")

    success = False
    async with aiohttp.ClientSession() as session:  # Use context manager to ensure session is closed
        try:
            async with session.post(DISCORD_WEBHOOK_URL, json=webhook_data) as response:
                if response.status == 429:
                    webhook_logger.warning(
                        f"Rate limited by Discord. Retry after: {response.headers.get('Retry-After', 'unknown')} seconds"
                    )
                    return False
                    
                if response.status != 204:
                    response_text = await response.text()
                    webhook_logger.error(
                        f"Failed to post to Discord. Status code: {response.status}, Response: {response_text}"
                    )
                    return False
                    
                webhook_logger.info("Successfully posted to Discord")
                success = True
                
        except Exception as e:
            webhook_logger.error(f"Error posting to Discord: {str(e)}")
            
    return success

async def post_mp4_link(title: str, mp4_url: str, team_data: Optional[Dict] = None) -> bool:
    """Post MP4 link to Discord webhook.
    
    Args:
        title (str): Post title
        mp4_url (str): MP4 URL to post
        team_data (dict, optional): Team data for customizing webhook appearance
        
    Returns:
        bool: True if post was successful, False otherwise
    """
    webhook_logger.info(f"Posting MP4 link: {mp4_url}")
    
    # Just send the raw MP4 URL as content
    webhook_data = {
        "username": DISCORD_USERNAME,
        "avatar_url": DISCORD_AVATAR_URL,
        "content": mp4_url  # Just the raw MP4 URL
    }
    
    webhook_logger.info(f"Final webhook data: {webhook_data}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(DISCORD_WEBHOOK_URL, json=webhook_data) as response:
                if response.status == 429:
                    webhook_logger.warning(
                        f"Rate limited by Discord. Retry after: {response.headers.get('Retry-After', 'unknown')} seconds"
                    )
                    return False
                    
                if response.status != 204:
                    response_text = await response.text()
                    webhook_logger.error(
                        f"Failed to post MP4 link. Status code: {response.status}, Response: {response_text}"
                    )
                    return False
                    
                webhook_logger.info("Successfully posted MP4 link")
                return True
                
        except Exception as e:
            webhook_logger.error(f"Error posting MP4 link: {str(e)}")
            return False
