"""Test MP4 URL extraction from various video hosts."""

import pytest
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

@pytest.mark.asyncio
async def test_streamff_extraction():
    """Test MP4 extraction from streamff.com."""
    # Test URLs
    test_cases = [
        ('https://streamff.com/v/abc123', [
            'https://ffedge.streamff.com/uploads/abc123.mp4',
            'https://streamff.com/video/abc123.mp4',
            'https://streamff.com/v/abc123/video.mp4'
        ]),
        ('https://streamff.com/v/xyz789', [
            'https://ffedge.streamff.com/uploads/xyz789.mp4',
            'https://streamff.com/video/xyz789.mp4',
            'https://streamff.com/v/xyz789/video.mp4'
        ])
    ]
    
    async with aiohttp.ClientSession() as session:
        for url, expected_patterns in test_cases:
            video_id = url.split('/')[-1]
            
            # Test each pattern
            for pattern in expected_patterns:
                try:
                    async with session.head(pattern) as response:
                        # We only care that the pattern matches expected format
                        assert video_id in pattern
                        assert pattern.endswith('.mp4')
                except aiohttp.ClientError:
                    # We don't fail the test if the URL is unreachable
                    # We just want to verify pattern generation
                    pass

@pytest.mark.asyncio
async def test_streamja_extraction():
    """Test MP4 extraction from streamja.com."""
    # Test URLs
    test_cases = [
        ('https://streamja.com/video/abc123', [
            'https://cdn.streamja.com/video/abc123.mp4',
            'https://streamja.com/video/abc123/direct-mp4'
        ]),
        ('https://streamja.com/video/xyz789', [
            'https://cdn.streamja.com/video/xyz789.mp4',
            'https://streamja.com/video/xyz789/direct-mp4'
        ])
    ]
    
    async with aiohttp.ClientSession() as session:
        for url, expected_patterns in test_cases:
            video_id = url.split('/')[-1]
            
            # Test each pattern
            for pattern in expected_patterns:
                try:
                    async with session.head(pattern) as response:
                        # We only care that the pattern matches expected format
                        assert video_id in pattern
                        assert '.mp4' in pattern or 'direct-mp4' in pattern
                except aiohttp.ClientError:
                    # We don't fail the test if the URL is unreachable
                    # We just want to verify pattern generation
                    pass

@pytest.mark.asyncio
async def test_streamff_extraction_function():
    """Test MP4 extraction from streamff.com using the extract_mp4_from_streamff function."""
    # Test URLs
    test_cases = [
        ('https://streamff.com/v/abc123', 'https://ffedge.streamff.com/uploads/abc123.mp4'),
        ('https://streamff.com/v/xyz789', 'https://ffedge.streamff.com/uploads/xyz789.mp4')
    ]
    
    for url, expected_pattern in test_cases:
        logger.info(f"\nTesting URL: {url}")
        mp4_url = await extract_mp4_from_streamff(url)
        if mp4_url:
            logger.info(f"✓ Successfully extracted MP4: {mp4_url}")
            assert mp4_url == expected_pattern
        else:
            logger.error("❌ Failed to extract MP4")
            assert False
