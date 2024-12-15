import asyncio
import aiohttp
import re
import logging
from typing import Optional

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def extract_mp4_from_streamff(url: str) -> Optional[str]:
    """Extract MP4 from streamff.com URL."""
    try:
        video_id = url.split('/')[-1]
        # Try different URL patterns
        patterns = [
            f"https://ffedge.streamff.com/uploads/{video_id}.mp4",
            f"https://streamff.com/video/{video_id}.mp4",
            f"https://streamff.com/v/{video_id}/video.mp4"
        ]
        
        async with aiohttp.ClientSession() as session:
            for pattern in patterns:
                try:
                    logger.info(f"Trying pattern: {pattern}")
                    async with session.head(pattern) as response:
                        if response.status == 200:
                            logger.info(f"✓ Success with pattern: {pattern}")
                            return pattern
                        logger.info(f"Failed with status {response.status}")
                except Exception as e:
                    logger.info(f"Failed to check pattern {pattern}: {str(e)}")
                    
            # If direct patterns fail, try to extract from page content
            async with session.get(url) as response:
                if response.status == 200:
                    content = await response.text()
                    logger.info("Got page content, searching for video URL")
                    patterns = [
                        r'source src="(https?://[^"]+\.mp4)"',
                        r'video src="(https?://[^"]+\.mp4)"',
                        r'https?://[^\s<>"]+?\.mp4'
                    ]
                    for pattern in patterns:
                        match = re.search(pattern, content)
                        if match:
                            url = match.group(1) if 'src' in pattern else match.group(0)
                            logger.info(f"✓ Found URL in page: {url}")
                            return url
                            
    except Exception as e:
        logger.error(f"Error extracting from streamff: {str(e)}")
    return None

async def main():
    # Test URLs
    urls = [
        "https://streamff.live/v/0533107c",  # Southampton vs Tottenham
        "https://streamff.live/v/7426f8c9",  # Chelsea vs Brentford
        "https://streamff.live/v/c2a4b7d8",  # Man City vs Man United
        "https://streamff.live/v/9c0c7f1a",  # Wolves vs Ipswich
    ]
    
    for url in urls:
        logger.info(f"\nTesting URL: {url}")
        mp4_url = await extract_mp4_from_streamff(url)
        if mp4_url:
            logger.info(f"✓ Successfully extracted MP4: {mp4_url}")
        else:
            logger.error("❌ Failed to extract MP4")

if __name__ == "__main__":
    asyncio.run(main())
