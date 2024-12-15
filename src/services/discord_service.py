"""Discord webhook service for posting goal clips."""

import aiohttp
import re
from datetime import datetime, timezone
from typing import Dict, Optional
from src.config import DISCORD_WEBHOOK_URL, DISCORD_USERNAME, DISCORD_AVATAR_URL
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
    """Post content to Discord webhook.
    
    Args:
        content (str): Content to post
        team_data (dict, optional): Team data for customizing webhook appearance
        username (str): Username for the webhook
        avatar_url (str): Avatar URL for the webhook
        
    Returns:
        bool: True if post was successful, False otherwise
    """
    if not DISCORD_WEBHOOK_URL:
        webhook_logger.error("Discord webhook URL not configured")
        return False

    # Split content into title and URL
    lines = content.split('\n')
    title = clean_text(lines[0].strip('*'))  # Remove markdown and clean text
    url = lines[1] if len(lines) > 1 else None

    webhook_logger.info(f"Preparing Discord message for: {title}")
    webhook_logger.info(f"Team data: {team_data}")

    # Create the embed
    embed = {
        "title": f"**{title}**",  # Use both title field and bold formatting
        "description": url if url else '',  # URL in description
        "color": team_data["color"] if team_data and "color" in team_data else 0x808080,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # Add team thumbnail if available
    if team_data and "logo" in team_data:
        embed["thumbnail"] = {"url": team_data["logo"]}
        webhook_logger.info(f"Added team logo: {team_data['logo']}")

    # Prepare webhook data
    webhook_data = {
        "embeds": [embed],
        "username": username,
        "avatar_url": avatar_url
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

async def post_mp4_link(title: str, mp4_url: str, team_data: Dict) -> None:
    """Post MP4 link to Discord."""
    webhook_logger.info(f"Posting MP4 link to Discord: {title}\n{mp4_url}")
    
    # Post just the MP4 URL without any formatting
    webhook_data = {
        "content": mp4_url,
        "username": DISCORD_USERNAME,
        "avatar_url": DISCORD_AVATAR_URL
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(DISCORD_WEBHOOK_URL, json=webhook_data) as response:
                if response.status == 204:
                    webhook_logger.info("Successfully posted to Discord")
                else:
                    webhook_logger.error(f"Failed to post to Discord. Status: {response.status}")
    except Exception as e:
        webhook_logger.error(f"Error posting to Discord: {str(e)}")